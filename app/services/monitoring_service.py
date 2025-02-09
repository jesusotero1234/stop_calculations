import time
import logging
from typing import Optional
from prometheus_client import start_http_server, Histogram, Counter, Gauge, CollectorRegistry
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
            
            # Service latency
            self.service_latency = Histogram(
                'service_request_latency_seconds',
                'Service request latency in seconds',
                ['service', 'endpoint', 'cache_status'],
                registry=self.registry
            )
            
            # Cache metrics
            self.cache_hits = Counter(
                'location_cache_hits_total',
                'Total number of cache hits',
                ['city', 'language'],
                registry=self.registry
            )
            
            self.cache_misses = Counter(
                'location_cache_misses_total',
                'Total number of cache misses',
                ['city', 'language'],
                registry=self.registry
            )
            
            self.cache_size = Gauge(
                'location_cache_entries',
                'Number of entries in location cache',
                ['city'],
                registry=self.registry
            )
            
            # Translation metrics
            self.translations_found = Counter(
                'location_translations_found_total',
                'Total number of translations found',
                ['source_language', 'target_language'],
                registry=self.registry
            )
            
            self.confidence_scores = Histogram(
                'location_match_confidence',
                'Confidence scores for location matches',
                ['match_type'],
                buckets=[0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
                registry=self.registry
            )
            
            # OSM API metrics
            self.osm_requests = Counter(
                'osm_requests_total',
                'Total OpenStreetMap API requests',
                ['status', 'endpoint'],
                registry=self.registry
            )
            
            self.osm_rate_limits = Counter(
                'osm_rate_limits_total',
                'Number of times rate limit was hit',
                registry=self.registry
            )
            
            # Try to start metrics server
            try:
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
        match_type: str = "direct",
        cache_hit: bool = False,
        city: str = "unknown",
        language: str = "en"
    ):
        """Record comprehensive OSM and cache metrics"""
        try:
            # Record latency
            self.service_latency.labels(
                service='osm',
                endpoint='validate_location',
                cache_status='hit' if cache_hit else 'miss'
            ).observe(response_time)
            
            # Record cache status
            if cache_hit:
                self.cache_hits.labels(
                    city=city,
                    language=language
                ).inc()
            else:
                self.cache_misses.labels(
                    city=city,
                    language=language
                ).inc()
            
            # Record request status
            self.osm_requests.labels(
                status='success' if success else 'failure',
                endpoint='geocode'
            ).inc()
            
            # Record confidence if available
            if match_quality is not None:
                self.confidence_scores.labels(
                    match_type=match_type
                ).observe(match_quality)

        except Exception as e:
            self.logger.error(f"Error recording OSM metrics: {str(e)}")

    def record_translation_found(
        self, 
        source_lang: str, 
        target_lang: str
    ):
        """Record successful translation"""
        try:
            self.translations_found.labels(
                source_language=source_lang,
                target_language=target_lang
            ).inc()
        except Exception as e:
            self.logger.error(f"Error recording translation metric: {str(e)}")

    def update_cache_size(self, city: str, size: int):
        """Update cache size gauge"""
        try:
            self.cache_size.labels(city=city).set(size)
        except Exception as e:
            self.logger.error(f"Error updating cache size: {str(e)}")

    def record_rate_limit_hit(self):
        """Record when rate limit is hit"""
        try:
            self.osm_rate_limits.inc()
        except Exception as e:
            self.logger.error(f"Error recording rate limit: {str(e)}")

    def get_metrics(self):
        """Get current metrics"""
        return self.registry

# Initialize singleton instance
monitoring = MonitoringService()