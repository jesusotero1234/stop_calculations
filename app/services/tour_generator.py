from typing import List, Optional, Dict
import uuid
import logging
import time
from ..models.tour import Tour, TourStop
from .llama_service import LlamaService
from .osm_service import OSMService
from .monitoring_service import MonitoringService

class TourGenerator:
    def __init__(
        self,
        llama_service: LlamaService,
        osm_service: OSMService,
        monitoring_service: MonitoringService,
        min_stops: int = 10
    ):
        self.llama_service = llama_service
        self.osm_service = osm_service
        self.monitoring = monitoring_service
        self.min_stops = min_stops
        self.logger = logging.getLogger(__name__)
        self.logger.info("Initializing TourGenerator")
        self.logger.debug(f"Configuration: min_stops={min_stops}")

    async def generate_tour(
        self,
        city: str,
        theme: str,
        duration: int,
        language: str = "en-us"
    ) -> Optional[Tour]:
        """
        Generate a tour based on parameters
        """
        start_time = time.time()
        self.logger.info(f"Starting tour generation for {city} ({theme}, {duration}min, {language})")
        
        try:
            # Calculate approximate number of stops based on duration
            # Assuming average of 15-20 minutes per stop plus walking time
            target_stops = max(2, min(duration // 20, self.min_stops))
            self.logger.debug(f"Calculated target stops: {target_stops}")

            # Record request start
            self.monitoring.request_counter.labels(endpoint="generate_tour", status="started").inc()

            # Generate initial set of stops
            self.logger.info("Requesting stops from LLM")
            raw_stops = await self._get_tour_stops(city, theme, language)
            if not raw_stops:
                self.logger.error("Failed to generate initial stops")
                self.monitoring.record_error("generation", "Failed to generate initial stops")
                return None

            self.logger.info(f"Generated {len(raw_stops)} raw stops")
            self.logger.debug(f"Raw stops: {raw_stops}")

            # Validate and get coordinates for stops
            self.logger.info("Validating locations with OpenStreetMap")
            validated_stops = await self._validate_stops(raw_stops, city)
            if not validated_stops:
                self.logger.error("No valid stops found after validation")
                self.monitoring.record_error("validation", "No valid stops found")
                return None

            self.logger.info(f"Validated {len(validated_stops)} stops")
            self.logger.debug(f"Validated stops: {validated_stops}")

            # Generate descriptions for validated stops
            self.logger.info(f"Generating descriptions for {min(len(validated_stops), target_stops)} stops")
            stops_with_descriptions = await self._add_descriptions(
                validated_stops[:target_stops],
                theme,
                language
            )
            
            if not stops_with_descriptions:
                self.logger.error("Failed to generate descriptions")
                self.monitoring.record_error("description", "Failed to generate descriptions")
                return None

            self.logger.info(f"Generated descriptions for {len(stops_with_descriptions)} stops")
            
            # Create tour
            tour = Tour(
                id=str(uuid.uuid4()),
                city=city,
                theme=theme,
                duration=duration,
                language=language,
                stops=stops_with_descriptions
            )

            # Record comprehensive metrics
            generation_time = time.time() - start_time
            self.monitoring.service_latency.labels(endpoint="generate_tour").observe(generation_time)
            
            quality_metrics = {
                "total_time": generation_time,
                "initial_stops": len(raw_stops),
                "validated_stops": len(validated_stops),
                "final_stops": len(stops_with_descriptions),
                "success_rate": len(stops_with_descriptions) / target_stops if target_stops else 0
            }
            
            self.logger.info(f"Tour generation completed successfully")
            self.logger.debug(f"Quality metrics: {quality_metrics}")
            
            self.monitoring.record_tour_generation(
                location=city,
                theme=theme,
                num_stops=len(stops_with_descriptions),
                response_quality=quality_metrics
            )

            # Record successful completion
            self.monitoring.request_counter.labels(endpoint="generate_tour", status="success").inc()

            return tour

        except Exception as e:
            self.logger.error(f"Error generating tour: {str(e)}", exc_info=True)
            self.monitoring.record_error("generation", str(e))
            self.monitoring.request_counter.labels(endpoint="generate_tour", status="error").inc()
            return None

    async def _get_tour_stops(self, city: str, theme: str, language: str) -> List[Dict[str, str]]:
        """
        Get initial set of stops from Llama
        """
        self.logger.debug(f"Getting tour stops for {city}")
        stops = []
        used_names = set()
        attempt = 0
        max_attempts = 3

        while len(stops) < self.min_stops and attempt < max_attempts:
            attempt += 1
            self.logger.debug(f"Attempt {attempt}/{max_attempts} to get stops")
            
            # Get new batch of stops
            new_stops = await self.llama_service.generate_stops(city, theme, language)
            self.logger.debug(f"Got {len(new_stops)} new stops")
            
            # Filter out duplicates
            for stop in new_stops:
                if stop["name"] not in used_names:
                    stops.append(stop)
                    used_names.add(stop["name"])
            
            if len(new_stops) == 0:
                self.logger.warning(f"No new stops generated in attempt {attempt}")
                self.monitoring.record_error(
                    "generation",
                    f"No new stops generated in attempt {attempt}"
                )
                break

        self.logger.info(f"Final stop count: {len(stops)}")
        return stops

    async def _validate_stops(
        self,
        stops: List[Dict[str, str]],
        city: str
    ) -> List[Dict[str, float]]:
        """
        Validate stops and get their coordinates
        """
        validated_stops = []
        start_time = time.time()
        self.logger.debug(f"Starting validation of {len(stops)} stops")
        
        for stop in stops:
            self.logger.debug(f"Validating stop: {stop['name']}")
            result = await self.osm_service.validate_and_get_coordinates(
                stop["name"],
                city
            )
            if result:
                validated_stops.append(result)
                self.logger.debug(f"Successfully validated: {stop['name']}")
            else:
                self.logger.warning(f"Failed to validate: {stop['name']}")

        # Record validation metrics
        validation_time = time.time() - start_time
        self.monitoring.service_latency.labels(endpoint="validate_stops").observe(validation_time)
        
        self.logger.info(f"Validated {len(validated_stops)} out of {len(stops)} stops")
        return validated_stops

    async def _add_descriptions(
        self,
        stops: List[Dict[str, float]],
        theme: str,
        language: str
    ) -> List[TourStop]:
        """
        Add themed descriptions to stops
        """
        stops_with_descriptions = []
        start_time = time.time()
        self.logger.debug(f"Generating descriptions for {len(stops)} stops")
        
        for stop in stops:
            self.logger.debug(f"Generating description for: {stop['original_name']}")
            description = await self.llama_service.generate_description(
                stop["original_name"],
                theme,
                language
            )
            
            if description:
                tour_stop = TourStop(
                    name=stop["original_name"],
                    latitude=stop["latitude"],
                    longitude=stop["longitude"],
                    description=description,
                    original_name=stop["original_name"]
                )
                stops_with_descriptions.append(tour_stop)
                self.logger.debug(f"Added description for: {stop['original_name']}")
            else:
                self.logger.warning(f"Failed to generate description for: {stop['original_name']}")

        # Record description generation metrics
        description_time = time.time() - start_time
        self.monitoring.service_latency.labels(endpoint="add_descriptions").observe(description_time)
        
        self.logger.info(f"Generated {len(stops_with_descriptions)} descriptions")
        return stops_with_descriptions
