from fastapi import FastAPI, HTTPException
from pydantic_settings import BaseSettings
from typing import List
import asyncio
from .models.tour import Tour, TourRequest
from .services.llama_service import LlamaService
from .services.osm_service import OSMService
from .services.monitoring_service import MonitoringService
from .services.tour_generator import TourGenerator
from .config import Settings
import logging

# Initialize settings and logging
settings = Settings()
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title=settings.api_title,
    description="Generate themed tour stops using local Llama model",
    version=settings.api_version
)

# Initialize services
monitoring_service = MonitoringService(port=settings.monitoring_port)
llama_service = LlamaService(monitoring_service=monitoring_service)
osm_service = OSMService(monitoring_service=monitoring_service)
tour_generator = TourGenerator(
    llama_service=llama_service,
    osm_service=osm_service,
    monitoring_service=monitoring_service,
    min_stops=settings.min_stops
)

@app.get("/")
async def health_check():
    """Health check endpoint"""
    try:
        monitoring_service.request_counter.labels(endpoint="health", status="success").inc()
        # Test Llama connection
        llm_response = await llama_service.health_check()
        
        return {
            "status": "healthy",
            "llm_model": llama_service.model,
            "version": settings.api_version,
            "llm_url": llama_service.base_url,
            "llm_status": "connected" if llm_response else "unavailable",
            "llm_response": llm_response
        }
    except Exception as e:
        monitoring_service.request_counter.labels(endpoint="health", status="error").inc()
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/generate-tour", response_model=Tour)
async def generate_tour(request: TourRequest):
    """
    Generate a tour based on city, theme, and duration
    
    Parameters:
    - city: Name of the city
    - theme: Theme of the tour (e.g., "Historical", "Cultural")
    - duration: Duration in minutes (30-240)
    - language: Language code (optional, defaults to "en-us")
    """
    try:
        # Validate duration
        if not settings.min_duration <= request.duration <= settings.max_duration:
            monitoring_service.record_error(
                "validation",
                f"Duration must be between {settings.min_duration} and {settings.max_duration} minutes"
            )
            raise HTTPException(
                status_code=400,
                detail=f"Duration must be between {settings.min_duration} and {settings.max_duration} minutes"
            )

        # Normalize theme
        theme = request.theme.lower()
        if theme not in settings.allowed_themes:
            monitoring_service.record_error(
                "validation",
                f"Theme must be one of: {', '.join(settings.allowed_themes)}"
            )
            raise HTTPException(
                status_code=400,
                detail=f"Theme must be one of: {', '.join(settings.allowed_themes)}"
            )

        # Generate tour
        tour = await tour_generator.generate_tour(
            city=request.city,
            theme=theme,
            duration=request.duration,
            language=request.language
        )
        
        if not tour:
            raise HTTPException(
                status_code=500,
                detail="Failed to generate tour"
            )

        return tour

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in generate_tour: {str(e)}")
        monitoring_service.record_error("api", str(e))
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

# Startup event to ensure Llama model is available
@app.on_event("startup")
async def startup_event():
    logger.info(f"Initializing {settings.api_title} API v{settings.api_version}")
    try:
        # Test connection with Llama once at startup
        response = await llama_service.health_check()
        if response:
            logger.info("✅ Successfully connected to Llama service")
            logger.info(f"URL: {llama_service.base_url}")
            logger.info(f"Model: {llama_service.model}")
            logger.info(f"Response: {response}")
        else:
            logger.error("Could not establish proper connection to Llama instance")
            logger.error("Please ensure Ollama is running with the phi4 model:")
            logger.error("1. Install Ollama: brew install ollama")
            logger.error("2. Run: ollama run phi4:latest")
    except Exception as e:
        logger.error(f"Startup error: {str(e)}", exc_info=True)

# Shutdown event for cleanup
@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"Shutting down {settings.api_title} API")
