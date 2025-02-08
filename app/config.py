from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Dict, Any, List
import json

class Settings(BaseSettings):
    # Llama Service Configuration
    llama_host: str = Field(default="host.docker.internal", description="Llama host address")
    llama_port: int = Field(default=11434, description="Llama port")
    
    # OpenStreetMap Configuration
    osm_timeout: int = Field(default=10, description="Timeout in seconds")
    name_match_threshold: float = Field(default=0.8, description="Minimum similarity ratio for name matching")
    
    # Tour Generation Settings
    min_stops: int = Field(default=2, description="Minimum number of stops")
    max_stops: int = Field(default=15, description="Maximum number of stops")
    min_duration: int = Field(default=30, description="Minimum duration in minutes")
    max_duration: int = Field(default=240, description="Maximum duration in minutes")
    max_description_length: int = Field(default=500, description="Maximum description length in characters")
    allowed_themes: List[str] = Field(default=["historical", "cultural"], description="Allowed tour themes")
    
    # Monitoring Configuration
    monitoring_port: int = Field(default=9090, description="Prometheus metrics port")
    log_level: str = Field(default="INFO", description="Logging level")
    
    # API Settings
    api_port: int = Field(default=8001, description="API port")
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_title: str = Field(default="Tour Generator", description="API title")
    api_version: str = Field(default="2.0.0", description="API version")

    @property
    def llama_url(self) -> str:
        """Get the full Llama URL"""
        return f"http://{self.llama_host}:{self.llama_port}"

    def dict(self, *args, **kwargs) -> Dict[str, Any]:
        """Convert settings to dict, excluding None values"""
        d = super().dict(*args, **kwargs)
        return {k: v for k, v in d.items() if v is not None}

    def json(self, *args, **kwargs) -> str:
        """Convert settings to JSON string"""
        return json.dumps(self.dict(*args, **kwargs))

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore",  # Ignore extra fields from .env file
    }