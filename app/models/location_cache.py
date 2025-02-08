from typing import Dict, Optional, List
from datetime import datetime
import logging
from dataclasses import dataclass, asdict
from app.services.db_client import db

logger = logging.getLogger(__name__)

@dataclass
class LocationCache:
    """Model representing a cached location"""
    original_name: str
    city: str
    translations: List[str]
    coordinates: Dict[str, float]
    success_count: int = 0
    confidence: float = 1.0
    source: str = "osm"
    id: Optional[str] = None
    country: Optional[str] = None
    metadata: Optional[Dict] = None
    last_validated: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    async def get_by_name(cls, name: str, city: str) -> Optional['LocationCache']:
        """Retrieve a location from cache by name and city"""
        try:
            result = await db.client.from_('location_cache')\
                .select('*')\
                .eq('original_name', name)\
                .eq('city', city)\
                .single()\
                .execute()
            
            if result.data:
                return cls(**result.data)
            return None

        except Exception as e:
            logger.error(f"Error retrieving from cache: {str(e)}")
            return None

    @classmethod
    async def create(cls, data: Dict) -> Optional['LocationCache']:
        """Create a new cached location"""
        try:
            result = await db.client.from_('location_cache')\
                .insert(data)\
                .execute()
            
            if result.data:
                return cls(**result.data[0])
            return None

        except Exception as e:
            logger.error(f"Error creating cache entry: {str(e)}")
            return None

    async def increment_success(self) -> bool:
        """Increment the success count for this location"""
        try:
            if not self.id:
                return False
            
            result = await db.client.from_('location_cache')\
                .update({
                    'success_count': self.success_count + 1,
                    'last_validated': datetime.utcnow().isoformat()
                })\
                .eq('id', self.id)\
                .execute()
            
            if result.data:
                self.success_count += 1
                self.last_validated = datetime.utcnow()
                return True
            return False

        except Exception as e:
            logger.error(f"Error incrementing success count: {str(e)}")
            return False

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage"""
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    async def update_or_create(cls, name: str, city: str, data: Dict) -> Optional['LocationCache']:
        """Update an existing cache entry or create a new one"""
        try:
            existing = await cls.get_by_name(name, city)
            if existing:
                result = await db.client.from_('location_cache')\
                    .update({**data, 'updated_at': datetime.utcnow().isoformat()})\
                    .eq('id', existing.id)\
                    .execute()
                return cls(**result.data[0]) if result.data else None
            else:
                return await cls.create({**data, 'original_name': name, 'city': city})

        except Exception as e:
            logger.error(f"Error updating/creating cache entry: {str(e)}")
            return None

    @classmethod
    async def cleanup_old_entries(cls, days: int = 30, min_success: int = 5) -> int:
        """Clean up old cache entries"""
        try:
            result = await db.client.from_('location_cache')\
                .delete()\
                .lt('last_validated', (datetime.utcnow() - datetime.timedelta(days=days)).isoformat())\
                .lt('success_count', min_success)\
                .execute()
            
            return len(result.data) if result.data else 0

        except Exception as e:
            logger.error(f"Error cleaning up old entries: {str(e)}")
            return 0
