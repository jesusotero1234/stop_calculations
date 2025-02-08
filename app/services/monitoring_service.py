from prometheus_client import start_http_server, Summary, Counter, Histogram, Gauge
import time
import logging
from typing import Any, Dict, Optional

# Initialize static error counter to avoid duplicates
error_counter = Counter(
    'error_total',
    'Total number of errors by type',
    ['error_type']
)

class MonitoringService:
    def __init__(self, port: int = 9090):
        self.logger = logging.getLogger(__name__)
        
        # General service metrics
        self.service_latency = Histogram(
            'service_request_latency_seconds',
            'Time spent processing tour generation requests',
            ['endpoint']
        )
        
        self.request_counter = Counter(
            'total_requests',
            'Total number of requests received',
            ['endpoint', 'status']
        )
        
        # Llama metrics
        self.llama_response_time = Histogram(
            'llama_response_time_seconds',
            'Time spent waiting for Llama responses',
            ['operation']
        )
        self.llama_quality_score = Histogram(
            'llama_response_quality',
            'Quality scores for Llama responses',
            ['type']
        )
        self.llama_success_rate = Counter(
            'llama_requests_total',
            'Number of Llama requests by status',
            ['operation', 'status']
        )
        
        # OpenStreetMap metrics
        self.osm_response_time = Histogram(
            'osm_response_time_seconds',
            'Time spent waiting for OpenStreetMap responses'
        )
        self.osm_success_rate = Counter(
            'osm_requests_total',
            'Number of OpenStreetMap requests by status',
            ['status']
        )
        self.osm_match_quality = Histogram(
            'osm_match_quality',
            'Quality of location matches from OpenStreetMap',
            ['match_type']
        )
        
        # Real-time gauges
        self.active_requests = Gauge(
            'active_requests',
            'Number of requests currently being processed'
        )
        self.last_success_timestamp = Gauge(
            'last_success_timestamp',
            'Timestamp of last successful tour generation'
        )
        
        # Start Prometheus HTTP server
        try:
            start_http_server(port)
            self.logger.info(f"Monitoring server started on port {port}")
        except Exception as e:
            self.logger.error(f"Failed to start monitoring server: {str(e)}")

    def record_llama_metrics(self, 
                           operation: str,
                           response_time: float,
                           success: bool,
                           quality_score: Optional[float] = None):
        """Record comprehensive Llama metrics"""
        try:
            self.llama_response_time.labels(operation=operation).observe(response_time)
            status = "success" if success else "error"
            self.llama_success_rate.labels(operation=operation, status=status).inc()
            
            if quality_score is not None:
                self.llama_quality_score.labels(type=operation).observe(quality_score)
                
            self.logger.debug(f"Recorded Llama metrics - Operation: {operation}, Time: {response_time}, Success: {success}")
        except Exception as e:
            self.logger.error(f"Error recording Llama metrics: {str(e)}")

    def record_osm_metrics(self,
                         response_time: float,
                         success: bool,
                         match_quality: Optional[float] = None,
                         match_type: str = "exact"):
        """Record comprehensive OpenStreetMap metrics"""
        try:
            self.osm_response_time.observe(response_time)
            status = "success" if success else "error"
            self.osm_success_rate.labels(status=status).inc()
            
            if match_quality is not None:
                self.osm_match_quality.labels(match_type=match_type).observe(match_quality)
                
            self.logger.debug(f"Recorded OSM metrics - Time: {response_time}, Success: {success}, Type: {match_type}")
        except Exception as e:
            self.logger.error(f"Error recording OSM metrics: {str(e)}")

    def record_tour_generation(self, 
                             location: str, 
                             theme: str, 
                             num_stops: int,
                             response_quality: Optional[Dict[str, Any]] = None):
        """Record metrics for a tour generation request"""
        try:
            self.last_success_timestamp.set_to_current_time()
            
            self.logger.info(
                f"Tour generation metrics - "
                f"Location: {location}, "
                f"Theme: {theme}, "
                f"Stops: {num_stops}"
            )
            
            if response_quality:
                self.logger.debug(f"Quality metrics: {response_quality}")
                
        except Exception as e:
            self.logger.error(f"Error recording tour metrics: {str(e)}")

    def record_error(self, error_type: str, details: str):
        """Record error metrics"""
        try:
            # Use global error counter to avoid duplicates
            error_counter.labels(error_type=error_type).inc()
            self.logger.error(f"Error recorded - Type: {error_type}, Details: {details}")
        except Exception as e:
            self.logger.error(f"Error recording error metrics: {str(e)}")