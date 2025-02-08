import time
import logging
from typing import Optional
from prometheus_client import start_http_server, Histogram, Counter, CollectorRegistry
import socket

class MonitoringService:
    _instance: Optional['MonitoringService'] = None
    _initialized: bool = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(MonitoringService, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize monitoring service with Prometheus metrics"""
        if not self._initialized:
            self.logger = logging.getLogger(__name__)
            self.registry = CollectorRegistry()
            
            # Initialize metrics
            self.service_latency = Histogram(
                'service_request_latency_seconds',
                'Service request latency in seconds',
                ['service', 'endpoint'],
                registry=self.registry
            )
            
            self.osm_requests = Counter(
                'osm_requests_total',
                'Total OpenStreetMap API requests',
                ['status'],
                registry=self.registry
            )
            
            self.cache_operations = Counter(
                'cache_operations_total',
                'Total cache operations',
                ['operation', 'status'],
                registry=self.registry
            )
            
            self.validation_results = Counter(
                'location_validation_results',
                'Location validation results',
                ['result', 'source'],
                registry=self.registry
            )
            
            # Try to start metrics server
            try:
                # Find available port
                port = self._find_available_port(start_port=9090)
                start_http_server(port, registry=self.registry)
                self.logger.info(f"Monitoring server started on port {port}")
            except Exception as e:
                self.logger.error(f"Failed to start monitoring server: {str(e)}")
            
            self._initialized = True

    def _find_available_port(self, start_port: int = 9090, max_tries: int = 10) -> int:
        """Find an available port starting from start_port"""
        for port in range(start_port, start_port + max_tries):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.bind(('', port))
                sock.close()
                return port
            except OSError:
                continue
        raise OSError("No available ports found")

    def record_osm_metrics(
        self,
        response_time: float,
        success: bool = True,
        match_quality: Optional[float] = None,
        match_type: str = "direct"
    ):
        """Record OSM API metrics"""
        try:
            # Record latency
            self.service_latency.labels(
                service='osm',
                endpoint='validate_location'
            ).observe(response_time)
            
            # Record request status
            self.osm_requests.labels(
                status='success' if success else 'failure'
            ).inc()
            
            # Record validation result
            if success:
                self.validation_results.labels(
                    result='valid',
                    source=match_type
                ).inc()
            else:
                self.validation_results.labels(
                    result='invalid',
                    source=match_type
                ).inc()

        except Exception as e:
            self.logger.error(f"Error recording OSM metrics: {str(e)}")

    def record_cache_operation(
        self,
        operation: str,
        success: bool,
        response_time: Optional[float] = None
    ):
        """Record cache operation metrics"""
        try:
            # Record operation status
            self.cache_operations.labels(
                operation=operation,
                status='success' if success else 'failure'
            ).inc()
            
            # Record latency if provided
            if response_time is not None:
                self.service_latency.labels(
                    service='cache',
                    endpoint=operation
                ).observe(response_time)

        except Exception as e:
            self.logger.error(f"Error recording cache metrics: {str(e)}")

    def get_metrics(self):
        """Get current metrics"""
        return self.registry

# Initialize singleton instance
monitoring = MonitoringService()