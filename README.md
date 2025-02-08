# Stop Calculations Service

Enhanced location validation service with caching and multi-language support.

## Features

- Location validation with Supabase-backed caching
- Multi-language name support
- Automatic validation history tracking
- Performance monitoring
- Rate limiting compliance

## Setup

### Prerequisites

- Python 3.11+
- Supabase account and project
- Environment variables configured

### Installation

1. Clone the repository:
```bash
git clone https://github.com/jesusotero1234/stop_calculations.git
cd stop_calculations
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate  # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your Supabase credentials
```

5. Set up the database:
See [DATABASE_SETUP.md](DATABASE_SETUP.md) for detailed instructions on setting up the Supabase database.

## Usage

### Basic Location Validation

```python
from app.services.osm_service import OSMService
from app.services.monitoring_service import MonitoringService

# Initialize services
monitoring = MonitoringService()
osm_service = OSMService(monitoring)

# Validate a location
result = await osm_service.validate_and_get_coordinates(
    "Royal Palace of Madrid",
    "Madrid"
)

if result:
    print(f"Location found: {result['latitude']}, {result['longitude']}")
```

### Cache Management

The service automatically caches successful validations. Cached results include:
- Original name and translations
- Coordinates
- Success count
- Last validation timestamp

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_location_cache.py -v

# Run with coverage
pytest --cov=app tests/
```

### Adding New Features

1. Create a feature branch:
```bash
git checkout -b feature/your-feature-name
```

2. Make changes and add tests

3. Run tests:
```bash
pytest tests/
```

4. Create pull request

## Architecture

### Components

1. **OSMService**: Main location validation service
   - Rate limiting
   - Cache integration
   - Multi-language support

2. **LocationCache**: Supabase-backed cache model
   - Automatic validation tracking
   - Translation management
   - Performance optimization

3. **MonitoringService**: Performance tracking
   - Response times
   - Cache hit rates
   - Success rates

### Database Schema

```sql
table location_cache {
    id: uuid
    original_name: text
    city: text
    translations: jsonb
    coordinates: jsonb
    success_count: integer
    confidence: float
    last_validated: timestamp
}
```

## Performance

- Average response time: 0.2s (cached) - 2s (new location)
- Cache hit rate: >80% (after warm-up)
- Success rate: >95%

## Contributing

1. Fork the repository
2. Create your feature branch
3. Add tests for new features
4. Submit pull request

## Environment Variables

Required environment variables:
```
# API Configuration
API_TITLE=Tour Generator
API_VERSION=2.0.0
API_PORT=8001
API_HOST=0.0.0.0

# Supabase Configuration
SUPABASE_URL=your_project_url
SUPABASE_KEY=your_anon_key
SUPABASE_SERVICE_KEY=your_service_role_key

# OpenStreetMap Configuration
OSM_USER_AGENT=TourGenerator/1.0
OSM_RATE_LIMIT=1.1

# Cache Configuration
CACHE_TTL=2592000  # 30 days in seconds
CACHE_MIN_SUCCESS=5

# Monitoring
ENABLE_MONITORING=true
PROMETHEUS_PORT=9090
LOG_LEVEL=DEBUG
```

## License

MIT License

## Authors

- Jesus Otero (@jesusotero1234)