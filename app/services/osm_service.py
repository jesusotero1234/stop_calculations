from typing import Dict, Optional, Tuple
import requests
from Levenshtein import ratio
import logging
import time
import asyncio
from .monitoring_service import MonitoringService
import urllib3

class OSMService:
    def __init__(self, monitoring_service: MonitoringService):
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            'User-Agent': 'TourGenerator/1.0 (https://github.com/tour_generator)',
            'Accept': 'application/json',
            'Accept-Language': 'es,en;q=0.9'  # Prefer Spanish results
        })
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        self.logger = logging.getLogger(__name__)
        self.min_similarity_ratio = 0.8
        self.monitoring = monitoring_service
        self.last_request_time = 0
        self.min_request_interval = 1.1  # seconds
        self.english_spanish_mappings = {
            "Royal Palace": ["Palacio Real"],
            "Cathedral": ["Catedral"],
            "Church": ["Iglesia", "Basílica"],
            "Monastery": ["Monasterio"],
            "Convent": ["Convento"],
            "Palace": ["Palacio"],
            "Theater": ["Teatro"],
            "Square": ["Plaza"]
        }
        self.logger.info("Initializing OSMService")

    async def _wait_for_rate_limit(self):
        """Ensure we respect Nominatim's rate limit"""
        now = time.time()
        time_since_last = now - self.last_request_time
        if time_since_last < self.min_request_interval:
            delay = self.min_request_interval - time_since_last
            self.logger.debug(f"Rate limit: waiting {delay:.2f}s")
            await asyncio.sleep(delay)
        self.last_request_time = time.time()

    async def _make_request(self, url: str) -> Optional[Dict]:
        """Make a rate-limited request to Nominatim"""
        await self._wait_for_rate_limit()
        try:
            response = self.session.get(url)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            self.logger.error(f"Request error ({url}): {str(e)}")
            return None

    def _translate_terms(self, query: str) -> list[str]:
        """Generate variations of the query using English-Spanish mappings"""
        variations = [query]
        
        # Replace English terms with Spanish equivalents
        for eng, spa_list in self.english_spanish_mappings.items():
            if eng.lower() in query.lower():
                for spa in spa_list:
                    new_query = query.lower().replace(eng.lower(), spa.lower())
                    variations.append(new_query)
        
        return list(set(variations))

    async def _geocode_location(self, query: str) -> Optional[Tuple[float, float]]:
        """Geocode a location query"""
        self.logger.debug(f"Geocoding query: {query}")
        
        # Try different variations of the query
        for variation in self._translate_terms(query):
            url = f"https://nominatim.openstreetmap.org/search?q={urllib3.util.parse_url(variation).url}&format=json&limit=1"
            
            result = await self._make_request(url)
            if result and len(result) > 0:
                self.logger.debug(f"Geocoding successful with variation '{variation}': {result[0].get('display_name')}")
                return float(result[0]["lat"]), float(result[0]["lon"])
            
            await asyncio.sleep(1.1)  # Rate limiting between variations
        
        self.logger.debug("Geocoding returned no results")
        return None

    async def validate_and_get_coordinates(self, place_name: str, city: str) -> Optional[Dict[str, float]]:
        """
        Validate location exists and get its coordinates using alternate name matching
        """
        start_time = time.time()
        self.logger.info(f"Validating location: {place_name} in {city}")

        try:
            # Try exact match first
            self.logger.debug(f"Attempting exact match for {place_name}")
            result = await self._geocode_location(f"{place_name}, {city}")
            
            if result:
                success = True
                match_quality = 1.0
                self.logger.info(f"Found exact match for {place_name}")
                self.logger.debug(f"Coordinates: {result}")
                
                self.monitoring.record_osm_metrics(
                    response_time=time.time() - start_time,
                    success=True,
                    match_quality=match_quality,
                    match_type="exact"
                )
                return {
                    "latitude": result[0],
                    "longitude": result[1],
                    "original_name": place_name
                }

            # Try alternate name matching
            self.logger.debug(f"Attempting alternate name matching for {place_name}")
            alternates = await self._get_alternate_names(place_name, city)
            if alternates:
                success = True
                match_quality = alternates[2]
                self.logger.info(f"Found alternate match for {place_name} with quality {match_quality}")
                self.logger.debug(f"Alternate coordinates: {alternates[:2]}")
                
                self.monitoring.record_osm_metrics(
                    response_time=time.time() - start_time,
                    success=True,
                    match_quality=match_quality,
                    match_type="alternate"
                )
                return {
                    "latitude": alternates[0],
                    "longitude": alternates[1],
                    "original_name": place_name
                }

            # No match found
            self.logger.warning(f"No match found for {place_name} in {city}")
            self.monitoring.record_osm_metrics(
                response_time=time.time() - start_time,
                success=False,
                match_quality=0.0,
                match_type="none"
            )
            return None

        except Exception as e:
            self.logger.error(f"Error validating location {place_name}: {str(e)}", exc_info=True)
            self.monitoring.record_osm_metrics(
                response_time=time.time() - start_time,
                success=False,
                match_type="error"
            )
            return None

    async def _get_alternate_names(self, place_name: str, city: str) -> Optional[Tuple[float, float, float]]:
        """Try to find location using alternate names and fuzzy matching"""
        self.logger.debug(f"Searching for alternate names: {place_name} in {city}")
        
        # Try all variations of the name
        for variation in self._translate_terms(place_name):
            try:
                search_query = f"{variation} {city}"
                self.logger.debug(f"Trying variation: {search_query}")
                
                url = f"https://nominatim.openstreetmap.org/search?q={urllib3.util.parse_url(search_query).url}&format=json"
                locations = await self._make_request(url)
                
                if locations:
                    # Check each result for name similarity
                    best_match = None
                    best_similarity = 0
                    
                    for location in locations:
                        name = location["display_name"].split(',')[0]
                        # Compare both original and translated names
                        similarities = [ratio(v.lower(), name.lower()) for v in self._translate_terms(place_name)]
                        similarity = max(similarities)
                        
                        if similarity >= self.min_similarity_ratio and similarity > best_similarity:
                            best_similarity = similarity
                            best_match = location
                            self.logger.debug(f"New best match: {name} ({similarity})")

                    if best_match:
                        self.logger.info(f"Found best alternate match: {best_match['display_name'].split(',')[0]} ({best_similarity})")
                        return float(best_match["lat"]), float(best_match["lon"]), best_similarity

                await asyncio.sleep(1.1)  # Rate limiting between variations
                
            except Exception as e:
                self.logger.error(f"Error with variation '{variation}': {str(e)}")
                continue

        self.logger.debug("No suitable alternate matches found")
        return None

    def set_similarity_threshold(self, threshold: float):
        """Configure the similarity threshold for name matching"""
        if 0 <= threshold <= 1:
            self.logger.info(f"Setting similarity threshold to {threshold}")
            self.min_similarity_ratio = threshold