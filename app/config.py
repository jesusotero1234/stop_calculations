import os
from dotenv import load_dotenv
from typing import Dict, Any

# Load environment variables
load_dotenv()

# API Configuration
API_CONFIG: Dict[str, Any] = {
    "TITLE": os.getenv("API_TITLE", "Tour Generator"),
    "VERSION": os.getenv("API_VERSION", "2.0.0"),
    "HOST": os.getenv("API_HOST", "0.0.0.0"),
    "PORT": int(os.getenv("API_PORT", "8001")),
}

# Service Configuration
SERVICE_CONFIG: Dict[str, Any] = {
    "MIN_STOPS": int(os.getenv("MIN_STOPS", "2")),
    "MAX_STOPS": int(os.getenv("MAX_STOPS", "15")),
    "MIN_DURATION": int(os.getenv("MIN_DURATION", "30")),
    "MAX_DURATION": int(os.getenv("MAX_DURATION", "240")),
    "MAX_DESCRIPTION_LENGTH": int(os.getenv("MAX_DESCRIPTION_LENGTH", "500")),
}

# Database Configuration
DB_CONFIG: Dict[str, str] = {
    "SUPABASE_URL": os.getenv("SUPABASE_URL", ""),
    "SUPABASE_KEY": os.getenv("SUPABASE_KEY", ""),
    "SUPABASE_SERVICE_KEY": os.getenv("SUPABASE_SERVICE_KEY", ""),
}

# OpenStreetMap Configuration
OSM_CONFIG: Dict[str, Any] = {
    "USER_AGENT": os.getenv("OSM_USER_AGENT", "TourGenerator/1.0"),
    "RATE_LIMIT": float(os.getenv("OSM_RATE_LIMIT", "1.1")),
}

# Cache Configuration
CACHE_CONFIG: Dict[str, int] = {
    "TTL": int(os.getenv("CACHE_TTL", "2592000")),  # 30 days in seconds
    "MIN_SUCCESS": int(os.getenv("CACHE_MIN_SUCCESS", "5")),
}

# LLama Configuration
LLAMA_CONFIG: Dict[str, Any] = {
    "HOST": os.getenv("LLAMA_HOST", "host.docker.internal"),
    "PORT": int(os.getenv("LLAMA_PORT", "11434")),
}

# Monitoring Configuration
MONITORING_CONFIG: Dict[str, Any] = {
    "ENABLE": os.getenv("ENABLE_MONITORING", "true").lower() == "true",
    "PORT": int(os.getenv("PROMETHEUS_PORT", "9090")),
    "LOG_LEVEL": os.getenv("LOG_LEVEL", "DEBUG"),
}

# Environment
ENV: str = os.getenv("ENV", "development")

def validate_config() -> None:
    """Validate required configuration is present"""
    if not DB_CONFIG["SUPABASE_URL"]:
        raise ValueError("SUPABASE_URL must be set")
    if not DB_CONFIG["SUPABASE_KEY"]:
        raise ValueError("SUPABASE_KEY must be set")

# Validate configuration on import
validate_config()