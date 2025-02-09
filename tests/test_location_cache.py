import pytest
from datetime import datetime, timedelta
from app.models.location_cache import LocationCache
from app.services.osm_service import OSMService
from app.services.monitoring_service import MonitoringService
import logging

# Configure logging for tests
logging.basicConfig(level=logging.INFO)

class TestLocationCache:
    @pytest.fixture
    def monitoring_service(self):
        return MonitoringService()

    @pytest.fixture
    def osm_service(self, monitoring_service):
        return OSMService(monitoring_service)

    async def clean_test_data(self, name: str, city: str = "Test City"):
        """Clean up test data after each test"""
        try:
            await LocationCache.update_or_create(
                name=name,
                city=city,
                data={
                    'translations': [],
                    'coordinates': {'lat': 0, 'lon': 0},
                    'confidence': 0,
                    'success_count': 0
                }
            )
        except Exception as e:
            print(f"Error cleaning test data: {str(e)}")

    @pytest.mark.asyncio
    async def test_location_cache_multilingual(self):
        """Test location caching with multiple languages"""
        test_location = {
            "original_name": "Royal Palace of Madrid",
            "translations": [
                "Palacio Real de Madrid",
                "Königlicher Palast von Madrid",
                "Palais royal de Madrid"
            ],
            "city": "Madrid",
            "coordinates": {"lat": 40.4167403, "lon": -3.7136222},
            "confidence": 1.0,
            "source": "test"
        }
        
        try:
            # Create initial cache entry
            cached = await LocationCache.create(test_location)
            assert cached is not None
            assert len(cached.translations) >= len(test_location["translations"])

            # Try finding with different translations
            for translation in test_location["translations"]:
                result = await LocationCache.find_by_variants(translation, "Madrid")
                assert result is not None
                assert result.coordinates == test_location["coordinates"]
                assert translation in result.translations

        finally:
            await self.clean_test_data(test_location["original_name"], "Madrid")

    @pytest.mark.asyncio
    async def test_osm_service_with_translations(self, osm_service):
        """Test OSM service with translation support"""
        location_pairs = [
            ("Royal Palace", "Palacio Real"),
            ("Cathedral", "Catedral"),
            ("City Hall", "Ayuntamiento")
        ]
        city = "Madrid"

        for english, spanish in location_pairs:
            try:
                # First request with English name
                result_en = await osm_service.validate_and_get_coordinates(english, city)
                assert result_en is not None
                assert "latitude" in result_en
                assert "longitude" in result_en

                # Should be cached now - try Spanish name
                result_es = await osm_service.validate_and_get_coordinates(spanish, city)
                assert result_es is not None
                assert result_es["latitude"] == result_en["latitude"]
                assert result_es["longitude"] == result_en["longitude"]

                # Verify translations were stored
                cached = await LocationCache.find_by_variants(english, city)
                assert cached is not None
                assert english in cached.translations
                assert spanish in cached.translations

            finally:
                await self.clean_test_data(english, city)
                await self.clean_test_data(spanish, city)

    @pytest.mark.asyncio
    async def test_cache_confidence_updates(self):
        """Test confidence score updates with usage"""
        test_data = {
            "original_name": "Test Location",
            "city": "Test City",
            "translations": ["Test 1"],
            "coordinates": {"lat": 1.0, "lon": 1.0},
            "confidence": 0.5
        }

        try:
            # Create initial entry
            cached = await LocationCache.create(test_data)
            assert cached is not None
            assert cached.confidence == 0.5

            # Increment success several times
            for _ in range(3):
                success = await cached.increment_success()
                assert success is True

            # Check confidence increased
            cached = await LocationCache.get_by_name(test_data["original_name"], test_data["city"])
            assert cached is not None
            assert cached.confidence > 0.5
            assert cached.confidence <= 1.0

        finally:
            await self.clean_test_data(test_data["original_name"])

    @pytest.mark.asyncio
    async def test_cache_cleanup(self):
        """Test cache cleanup functionality"""
        test_locations = [
            {"name": "Old Unused Place", "success": 1, "days_old": 40},
            {"name": "Old Popular Place", "success": 10, "days_old": 40},
            {"name": "New Unused Place", "success": 1, "days_old": 5},
        ]

        try:
            # Create test entries
            for loc in test_locations:
                validated_date = datetime.utcnow() - timedelta(days=loc["days_old"])
                await LocationCache.create({
                    "original_name": loc["name"],
                    "city": "Test City",
                    "translations": [loc["name"]],
                    "coordinates": {"lat": 1.0, "lon": 1.0},
                    "success_count": loc["success"],
                    "last_validated": validated_date.isoformat()
                })

            # Run cleanup
            deleted = await LocationCache.cleanup_old_entries(days=30, min_success=5)
            assert deleted == 1  # Should only delete old unused place

            # Verify correct entries remain
            old_popular = await LocationCache.get_by_name("Old Popular Place", "Test City")
            assert old_popular is not None  # High success count keeps it

            new_unused = await LocationCache.get_by_name("New Unused Place", "Test City")
            assert new_unused is not None  # Recent validation keeps it

            old_unused = await LocationCache.get_by_name("Old Unused Place", "Test City")
            assert old_unused is None  # Should be deleted

        finally:
            for loc in test_locations:
                await self.clean_test_data(loc["name"])

if __name__ == "__main__":
    pytest.main(["-v", "test_location_cache.py"])