# Location Cache Monitoring

## Features

1. **Performance Metrics**
   - Response times (cache hits/misses)
   - Cache hit rates
   - Translation success rates
   - API latency tracking

2. **Cache Statistics**
   - Total entries
   - Success counts
   - Average confidence scores
   - Translation counts

3. **Maintenance Metrics**
   - Cleanup candidates
   - Cache size by city
   - Entry age distribution
   - Success rate distribution

## Usage

### Running the Monitor

```bash
# Basic monitoring
./scripts/monitor_cache.py

# With specific timeframe
./scripts/monitor_cache.py --days 7

# Export metrics
./scripts/monitor_cache.py --export metrics.json
```

### Example Output

```
Cache Performance Report
==================================================
Total Entries: 1,234
Successful Entries: 987
Cache Hit Rate: 79.98%
Average Confidence: 0.92

Response Times
--------------------------------------------------
Average Cache Hit Time: 0.203s
Average Cache Miss Time: 5.127s
Time Saved per Hit: 4.924s

Translations
--------------------------------------------------
en-es: 456 translations
es-en: 442 translations
en-de: 123 translations
de-en: 119 translations

Maintenance
--------------------------------------------------
Entries eligible for cleanup: 45
```

## Prometheus Metrics

### Available Metrics

1. **Latency Histograms**
   ```
   service_request_latency_seconds{service="osm",endpoint="validate_location",cache_status="hit"}
   service_request_latency_seconds{service="osm",endpoint="validate_location",cache_status="miss"}
   ```

2. **Cache Counters**
   ```
   location_cache_hits_total{city="madrid",language="es"}
   location_cache_misses_total{city="madrid",language="es"}
   ```

3. **Translation Metrics**
   ```
   location_translations_found_total{source_language="en",target_language="es"}
   ```

### Grafana Dashboard

Import the provided dashboard (ID: 12345) for visualization:

1. Cache Performance
   - Hit rates over time
   - Response time distribution
   - Success rates by city

2. Translation Analysis
   - Language pair success rates
   - Translation confidence scores
   - Cross-language matches

3. System Health
   - Cache size trends
   - Cleanup effectiveness
   - Error rates

## Alerts

### Configured Alerts

1. **High Miss Rate**
   - Condition: Cache miss rate > 30% in 5 minutes
   - Action: Notify admin, check validation logic

2. **Slow Response Time**
   - Condition: Avg response time > 2s for cache hits
   - Action: Check database performance

3. **Cache Growth**
   - Condition: Cache size increased > 50% in 24h
   - Action: Review cleanup settings

### Setting Up Alerts

1. In Grafana:
   ```yaml
   - alert: HighCacheMissRate
     expr: rate(cache_misses_total[5m]) > 0.3
     for: 5m
     labels:
       severity: warning
     annotations:
       summary: High cache miss rate
   ```

2. In Prometheus:
   ```yaml
   groups:
   - name: cache_alerts
     rules:
     - alert: SlowResponseTime
       expr: histogram_quantile(0.95, service_request_latency_seconds) > 2
       for: 5m
       labels:
         severity: critical
   ```

## Maintenance

### Automatic Cleanup

The system automatically cleans up entries that are:
- Older than 30 days
- Have less than 5 successful validations
- Have low confidence scores

### Manual Maintenance

```bash
# Force cleanup
./scripts/monitor_cache.py --cleanup

# Analyze specific city
./scripts/monitor_cache.py --city madrid

# Export statistics
./scripts/monitor_cache.py --export-stats report.json
```

## Troubleshooting

1. High Miss Rates
   - Check OSM API status
   - Verify translation service
   - Review validation thresholds

2. Slow Response Times
   - Check Supabase connection
   - Monitor database load
   - Review index usage

3. Translation Issues
   - Verify language detection
   - Check translation mappings
   - Review confidence thresholds