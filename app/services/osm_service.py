from typing import Dict, Optional, Tuple, List
import requests
from Levenshtein import ratio
import logging
import time
import asyncio
from datetime import datetime
from .monitoring_service import MonitoringService
from ..models.location_cache import LocationCache
import urllib3

class OSMService:
    def __init__(self, monitoring_service: MonitoringService):
        self.session = requests.Session()
        self.session.verify = False
        self.session.headers.update({
            'User-Agent': 'TourGenerator/1.0 (https://github.com/jesusotero1234/tour_generator)',
            'Accept': 'application/json',
            'Accept-Language': 'es,en;q=0.9'
        })
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        self.logger = logging.getLogger(__name__)
        self.min_similarity_ratio = 0.8
        self.monitoring = monitoring_service
        self.last_request_time = 0
        self.min_request_interval = 1.1  # seconds

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

    async def validate_and_get_coordinates(self, place_name: str, city: str) -> Optional[Dict[str, float]]:
        """
        Validate location exists and get its coordinates using cache and alternate name matching
        """
        start_time = time.time()
        self.logger.info(f"Validating location: {place_name} in {city}")

        try:
            # Check cache first
            cached = await LocationCache.get_by_name(place_name, city)
            if cached:
                self.logger.info(f"Cache hit for {place_name}")
                await cached.increment_success()
                self.monitoring.record_osm_metrics(
                    response_time=time.time() - start_time,
                    success=True,
                    match_quality=cached.confidence,
                    match_type="cache"
                )
                return {
                    "latitude": cached.coordinates["lat"],
                    "longitude": cached.coordinates["lon"],
                    "original_name": place_name
                }

            # Try exact match
            self.logger.debug(f"Cache miss, attempting exact match for {place_name}")
            result = await self._geocode_location(f"{place_name}, {city}")
            
            if result:
                await self._cache_result(place_name, city, result, 1.0, "exact")
                self.monitoring.record_osm_metrics(
                    response_time=time.time() - start_time,
                    success=True,
                    match_quality=1.0,
                    match_type="exact"
                )
                return {
                    "latitude": result[0],
                    "longitude": result[1],
                    "original_name": place_name
                }

            # Try alternate names
            alternates = await self._get_alternate_names(place_name, city)
            if alternates:
                await self._cache_result(place_name, city, 
                                      (alternates[0], alternates[1]), 
                                      alternates[2], "alternate")
                self.monitoring.record_osm_metrics(
                    response_time=time.time() - start_time,
                    success=True,
                    match_quality=alternates[2],
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

    async def _cache_result(self, name: str, city: str, 
                          coords: Tuple[float, float], 
                          confidence: float, source: str) -> None:
        """Cache successful location lookup"""
        try:
            await LocationCache.update_or_create(
                name=name,
                city=city,
                data={
                    'coordinates': {
                        'lat': coords[0],
                        'lon': coords[1]
                    },
                    'translations': [name],  # Initial translation is original name
                    'confidence': confidence,
                    'source': source,
                    'success_count': 1,
                    'last_validated': datetime.utcnow().isoformat()
                }
            )
        except Exception as e:
            self.logger.error(f"Error caching result: {str(e)}")

    async def _geocode_location(self, query: str) -> Optional[Tuple[float, float]]:
        """Geocode a location query"""
        self.logger.debug(f"Geocoding query: {query}")
        url = f"https://nominatim.openstreetmap.org/search?q={urllib3.util.parse_url(query).url}&format=json&limit=1"
        
        result = await self._make_request(url)
        if result and len(result) > 0:
            self.logger.debug(f"Geocoding successful: {result[0].get('display_name')}")
            return float(result[0]["lat"]), float(result[0]["lon"])
        
        self.logger.debug("Geocoding returned no results")
        return None

    async def _get_alternate_names(self, place_name: str, city: str) -> Optional[Tuple[float, float, float]]:
        """Try to find location using alternate names"""
        self.logger.debug(f"Searching for alternate names: {place_name} in {city}")
        try:
            search_query = f"{place_name} {city}"
            self.logger.debug(f"Search query: {search_query}")
            
            url = f"https://nominatim.openstreetmap.org/search?q={urllib3.util.parse_url(search_query).url}&format=json"
            locations = await self._make_request(url)
            
            if not locations:
                self.logger.debug("No alternate locations found")
                return None

            # Check each result for name similarity
            best_match = None
            best_similarity = 0

            for location in locations:
                name = location["display_name"].split(',')[0]
                similarity = ratio(place_name.lower(), name.lower())
                self.logger.debug(f"Checking similarity: {name} ({similarity})")
                
                if similarity >= self.min_similarity_ratio and similarity > best_similarity:
                    best_similarity = similarity
                    best_match = location
                    self.logger.debug(f"New best match: {name} ({similarity})")

            if best_match:
                self.logger.info(f"Found best alternate match: {best_match['display_name'].split(',')[0]} ({best_similarity})")
                return float(best_match["lat"]), float(best_match["lon"]), best_similarity

            self.logger.debug("No suitable alternate matches found")
            return None

        except Exception as e:
            self.logger.error(f"Error finding alternate names for {place_name}: {str(e)}")
            return None

    def set_similarity_threshold(self, threshold: float):
        """Configure the similarity threshold for name matching"""
        if 0 <= threshold <= 1:
            self.logger.info(f"Setting similarity threshold to {threshold}")
            self.min_similarity_ratio = threshold