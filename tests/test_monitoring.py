import pytest
from app.services.monitoring_service import MonitoringService
from app.services.osm_service import OSMService
from app.models.location_cache import LocationCache

class TestMonitoring:
    @pytest.fixture
    def monitoring_service(self):
        return MonitoringService()

    @pytest.fixture
    def osm_service(self, monitoring_service):
        return OSMService(monitoring_service)

    @pytest.mark.asyncio
    async def test_cache_metrics(self, monitoring_service, osm_service):
        """Test that cache metrics are recorded properly"""
        test_location = {
            "original_name": "Test Metrics Place",
            "city": "Test City",
            "translations": ["Test 1"],
            "coordinates": {"lat": 1.0, "lon": 1.0},
            "confidence": 1.0
        }

        try:
            # Create cache entry
            cached = await LocationCache.create(test_location)
            assert cached is not None

            # Record initial cache size
            initial_size = monitoring_service.registry.get_sample_value(
                'location_cache_entries_total',
                {'city': 'Test City'}
            )

            # First request - should be cache hit
            result = await osm_service.validate_and_get_coordinates(
                test_location["original_name"],
                test_location["city"]
            )
            assert result is not None

            # Check cache hit was recorded
            cache_hits = monitoring_service.registry.get_sample_value(
                'location_cache_hits_total',
                {'city': 'Test City', 'language': 'en'}
            )
            assert cache_hits == 1

            # Try with unknown location - should be cache miss
            result = await osm_service.validate_and_get_coordinates(
                "Unknown Place",
                test_location["city"]
            )

            # Check cache miss was recorded
            cache_misses = monitoring_service.registry.get_sample_value(
                'location_cache_misses_total',
                {'city': 'Test City', 'language': 'en'}
            )
            assert cache_misses == 1

        finally:
            await LocationCache.cleanup_old_entries(days=0)

    @pytest.mark.asyncio
    async def test_translation_metrics(self, monitoring_service, osm_service):
        """Test that translation metrics are recorded"""
        test_pairs = [
            ("Royal Palace", "Palacio Real", "Madrid"),
            ("Cathedral", "Catedral", "Madrid")
        ]

        try:
            for english, spanish, city in test_pairs:
                # Create cache entry with translation
                await LocationCache.create({
                    "original_name": english,
                    "city": city,
                    "translations": [english, spanish],
                    "coordinates": {"lat": 40.4167403, "lon": -3.7136222},
                    "confidence": 1.0
                })

                # Try finding with Spanish name
                result = await osm_service.validate_and_get_coordinates(spanish, city)
                assert result is not None

                # Check translation metric
                translations = monitoring_service.registry.get_sample_value(
                    'location_translations_found_total',
                    {'source_language': 'es', 'target_language': 'en'}
                )
                assert translations >= 1

        finally:
            for english, _, city in test_pairs:
                await LocationCache.cleanup_old_entries(days=0)

    @pytest.mark.asyncio
    async def test_performance_metrics(self, monitoring_service, osm_service):
        """Test that performance metrics are recorded"""
        location = "Performance Test Place"
        city = "Test City"

        try:
            # First request - should be cache miss and slower
            start_time = monitoring_service.registry.get_sample_value(
                'service_request_latency_seconds_sum',
                {'service': 'osm', 'endpoint': 'validate_location', 'cache_status': 'miss'}
            ) or 0

            result = await osm_service.validate_and_get_coordinates(location, city)
            
            end_time = monitoring_service.registry.get_sample_value(
                'service_request_latency_seconds_sum',
                {'service': 'osm', 'endpoint': 'validate_location', 'cache_status': 'miss'}
            ) or 0

            assert end_time > start_time

            # Second request - should be cache hit and faster
            start_time = monitoring_service.registry.get_sample_value(
                'service_request_latency_seconds_sum',
                {'service': 'osm', 'endpoint': 'validate_location', 'cache_status': 'hit'}
            ) or 0

            result = await osm_service.validate_and_get_coordinates(location, city)

            end_time = monitoring_service.registry.get_sample_value(
                'service_request_latency_seconds_sum',
                {'service': 'osm', 'endpoint': 'validate_location', 'cache_status': 'hit'}
            ) or 0

            assert end_time > start_time

        finally:
            await LocationCache.cleanup_old_entries(days=0)

if __name__ == "__main__":
    pytest.main(["-v", "test_monitoring.py"])