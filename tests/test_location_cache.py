import pytest
import asyncio
from datetime import datetime
from app.models.location_cache import LocationCache
from app.services.osm_service import OSMService
from app.services.monitoring_service import MonitoringService

class TestLocationCache:
    @pytest.fixture
    def monitoring_service(self):
        return MonitoringService()

    @pytest.fixture
    def osm_service(self, monitoring_service):
        return OSMService(monitoring_service)

    @pytest.mark.asyncio
    async def test_location_cache_create_and_retrieve(self):
        """Test creating and retrieving a cached location"""
        test_data = {
            "original_name": "Royal Palace of Madrid",
            "city": "Madrid",
            "translations": ["Palacio Real de Madrid"],
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

    @pytest.mark.asyncio
    async def test_osm_service_with_cache(self, osm_service):
        """Test OSM service with caching"""
        # First request - should hit OSM API
        location = "Royal Palace of Madrid"
        city = "Madrid"
        
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

    @pytest.mark.asyncio
    async def test_cache_update(self):
        """Test updating cache entries"""
        test_data = {
            "original_name": "Test Location",
            "city": "Test City",
            "translations": ["Test 1"],
            "coordinates": {"lat": 1.0, "lon": 1.0},
            "confidence": 1.0,
            "source": "test"
        }

        # Create initial entry
        cached = await LocationCache.create(test_data)
        assert cached is not None

        # Update entry
        updated_data = {
            **test_data,
            "translations": ["Test 1", "Test 2"],
            "confidence": 0.9
        }
        updated = await LocationCache.update_or_create(
            test_data["original_name"],
            test_data["city"],
            updated_data
        )

        assert updated is not None
        assert len(updated.translations) == 2
        assert updated.confidence == 0.9

    @pytest.mark.asyncio
    async def test_success_count_increment(self):
        """Test incrementing success count"""
        test_data = {
            "original_name": "Success Test",
            "city": "Test City",
            "translations": ["Test"],
            "coordinates": {"lat": 1.0, "lon": 1.0},
            "success_count": 0
        }

        # Create entry
        cached = await LocationCache.create(test_data)
        assert cached is not None
        assert cached.success_count == 0

        # Increment success count
        success = await cached.increment_success()
        assert success is True
        assert cached.success_count == 1

        # Verify in database
        retrieved = await LocationCache.get_by_name(
            test_data["original_name"],
            test_data["city"]
        )
        assert retrieved is not None
        assert retrieved.success_count == 1

    @pytest.mark.asyncio
    async def test_cache_with_multiple_translations(self, osm_service):
        """Test caching with multiple translations"""
        location = "Royal Palace"
        city = "Madrid"
        translations = ["Palacio Real", "Royal Palace", "Königlicher Palast"]

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

    @pytest.mark.asyncio
    async def test_cache_invalidation(self):
        """Test cache entry invalidation after long period"""
        old_date = datetime(2024, 1, 1).isoformat()
        test_data = {
            "original_name": "Old Location",
            "city": "Test City",
            "translations": ["Test"],
            "coordinates": {"lat": 1.0, "lon": 1.0},
            "last_validated": old_date
        }

        # Create old entry
        cached = await LocationCache.create(test_data)
        assert cached is not None
        assert cached.last_validated.isoformat() == old_date

        # Update last_validated
        success = await cached.increment_success()
        assert success is True
        assert cached.last_validated > datetime.fromisoformat(old_date)

if __name__ == "__main__":
    pytest.main(["-v", "test_location_cache.py"])