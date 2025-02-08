import pytest
import asyncio
from datetime import datetime
from app.models.location_cache import LocationCache
from app.services.osm_service import OSMService
from app.services.monitoring_service import MonitoringService
from app.services.db_client import db

class TestLocationCache:
    @pytest.fixture
    def monitoring_service(self):
        return MonitoringService()

    @pytest.fixture
    def osm_service(self, monitoring_service):
        return OSMService(monitoring_service)

    async def clean_test_data(self, test_name: str, city: str = "Test City"):
        """Clean up test data after each test"""
        try:
            await db.client.table('location_cache')\
                .delete()\
                .eq('original_name', test_name)\
                .eq('city', city)\
                .execute()
        except Exception as e:
            print(f"Error cleaning test data: {str(e)}")

    @pytest.mark.asyncio
    async def test_location_cache_create_and_retrieve(self):
        """Test creating and retrieving a cached location"""
        test_name = "Test Location"
        
        try:
            test_data = {
                "original_name": test_name,
                "city": "Madrid",
                "translations": ["Test 1"],
                "coordinates": {"lat": 40.4167403, "lon": -3.7136222},
                "confidence": 1.0,
                "source": "test"
            }

            # Create cache entry
            cached = await LocationCache.create(test_data)
            assert cached is not None
            assert cached.original_name == test_data["original_name"]
            assert cached.coordinates == test_data["coordinates"]

            # Retrieve cache entry
            retrieved = await LocationCache.get_by_name(
                test_data["original_name"],
                test_data["city"]
            )
            assert retrieved is not None
            assert retrieved.original_name == test_data["original_name"]
            assert retrieved.coordinates == test_data["coordinates"]

        finally:
            await self.clean_test_data(test_name, "Madrid")

    @pytest.mark.asyncio
    async def test_osm_service_with_cache(self, osm_service):
        """Test OSM service with caching"""
        location = "Royal Palace of Madrid"
        city = "Madrid"
        
        try:
            # First request - should hit OSM API
            result = await osm_service.validate_and_get_coordinates(location, city)
            assert result is not None
            assert "latitude" in result
            assert "longitude" in result

            # Second request - should hit cache
            cached_result = await osm_service.validate_and_get_coordinates(location, city)
            assert cached_result is not None
            assert cached_result["latitude"] == result["latitude"]
            assert cached_result["longitude"] == result["longitude"]

            # Verify cache was used
            cached = await LocationCache.get_by_name(location, city)
            assert cached is not None
            assert cached.success_count > 0

        finally:
            await self.clean_test_data(location, city)

    @pytest.mark.asyncio
    async def test_cache_with_multiple_translations(self, osm_service):
        """Test caching with multiple translations"""
        location = "Royal Palace"
        city = "Madrid"
        translations = ["Palacio Real", "Royal Palace", "Königlicher Palast"]

        try:
            # Create cache entry with translations
            test_data = {
                "original_name": location,
                "city": city,
                "translations": translations,
                "coordinates": {"lat": 40.4167403, "lon": -3.7136222},
                "confidence": 1.0,
                "source": "test"
            }

            cached = await LocationCache.create(test_data)
            assert cached is not None
            assert len(cached.translations) == len(translations)

            # Try retrieving with different translations
            for translation in translations:
                result = await osm_service.validate_and_get_coordinates(translation, city)
                assert result is not None
                assert result["latitude"] == test_data["coordinates"]["lat"]
                assert result["longitude"] == test_data["coordinates"]["lon"]

            # Check statistics
            stats = await LocationCache.get_statistics()
            assert stats is not None
            assert "cache_hit_rate" in stats
            assert "average_confidence" in stats

        finally:
            await self.clean_test_data(location, city)

    @pytest.mark.asyncio
    async def test_cache_cleanup(self):
        """Test cache cleanup functionality"""
        test_locations = [
            {"name": "Old Place 1", "success": 1},
            {"name": "Old Place 2", "success": 3},
            {"name": "Popular Place", "success": 10}
        ]

        try:
            # Create test entries
            for loc in test_locations:
                await LocationCache.create({
                    "original_name": loc["name"],
                    "city": "Test City",
                    "translations": [loc["name"]],
                    "coordinates": {"lat": 1.0, "lon": 1.0},
                    "success_count": loc["success"],
                    "last_validated": datetime(2024, 1, 1).isoformat()
                })

            # Run cleanup
            deleted = await LocationCache.cleanup_old_entries(days=30, min_success=5)
            assert deleted == 2  # Should delete the two less popular places

            # Verify popular place remains
            popular = await LocationCache.get_by_name("Popular Place", "Test City")
            assert popular is not None
            assert popular.success_count == 10

        finally:
            for loc in test_locations:
                await self.clean_test_data(loc["name"])

if __name__ == "__main__":
    pytest.main(["-v", "test_location_cache.py"])