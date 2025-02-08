from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class TourRequest(BaseModel):
    city: str = Field(..., description="Name of the city")
    theme: str = Field(..., description="Theme of the tour")
    duration: int = Field(..., description="Duration in minutes", ge=30, le=240)
    language: str = Field(default="en-us", description="Language code")

class TourStop(BaseModel):
    name: str
    latitude: float
    longitude: float
    description: str
    original_name: str = Field(..., description="Original name before any matching")

class Tour(BaseModel):
    id: str
    city: str
    theme: str
    duration: int
    language: str
    stops: List[TourStop]
    created_at: datetime = Field(default_factory=datetime.utcnow)

    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "city": "Madrid",
                "theme": "Historical",
                "duration": 120,
                "language": "en-us",
                "stops": [
                    {
                        "name": "Royal Palace",
                        "latitude": 40.4177,
                        "longitude": -3.7148,
                        "description": "Former residence of Spanish kings...",
                        "original_name": "Royal Palace"
                    }
                ]
            }
        }