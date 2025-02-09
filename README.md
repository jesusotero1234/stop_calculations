# Stop Calculations Service

Enhanced location validation service with caching and multi-language support.

## Features

- Location validation with Supabase-backed caching
- Multi-language name support
- Automatic validation history tracking
- Comprehensive monitoring and alerts
- Rate limiting compliance

## Documentation

- [Database Setup](DATABASE_SETUP.md)
- [Monitoring Guide](MONITORING.md)
- [Pull Request](PULL_REQUEST.md)

## Quick Start

1. Clone and setup:
```bash
git clone https://github.com/jesusotero1234/stop_calculations.git
cd stop_calculations
python -m venv venv
source venv/bin/activate  # Linux/Mac
pip install -r requirements.txt
```

2. Configure environment:
```bash
cp .env.example .env
# Edit .env with your credentials
```

3. Setup database:
```bash
# Follow instructions in DATABASE_SETUP.md
```

4. Run tests:
```bash
pytest
```

5. Monitor performance:
```bash
./scripts/monitor_cache.py
```

## Architecture

### Components

1. **Location Validation**
   - OSM integration with rate limiting
   - Multi-language support
   - Translation tracking

2. **Cache Layer**
   - Supabase-backed storage
   - Automatic cleanup
   - Performance metrics

3. **Monitoring**
   - Prometheus metrics
   - Grafana dashboards
   - Automated alerts

## Performance

- Average response times:
  - Cache hit: 0.2s
  - Cache miss: 2.0s
- Cache hit rate: >80%
- Translation success: >95%

## Monitoring

See [MONITORING.md](MONITORING.md) for:
- Performance metrics
- Grafana dashboards
- Alert configurations
- Maintenance tasks

## Development

1. Create feature branch:
```bash
git checkout -b feature/your-feature
```

2. Implement changes

3. Run tests:
```bash
pytest
```

4. Create pull request

## Configuration

Required environment variables:
```bash
# API Configuration
API_TITLE="Tour Generator"
API_VERSION="2.0.0"
API_PORT=8001

# Supabase
SUPABASE_URL=your_project_url
SUPABASE_KEY=your_anon_key

# OpenStreetMap
OSM_USER_AGENT=TourGenerator/1.0
OSM_RATE_LIMIT=1.1

# Cache
CACHE_TTL=2592000  # 30 days
CACHE_MIN_SUCCESS=5

# Monitoring
ENABLE_MONITORING=true
PROMETHEUS_PORT=9090
```

## Contributing

1. Fork repository
2. Create feature branch
3. Add tests
4. Submit pull request

## License

MIT License

## Authors

- Jesus Otero (@jesusotero1234)