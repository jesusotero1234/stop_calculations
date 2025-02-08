# Location Validation Implementation Plan

## Phase 1: Fast Path & Caching (2 days)

### Day 1: Basic Cache Implementation
```python
# location_cache.py
class LocationCache:
    def __init__(self):
        self.cache = {}
        self.static_translations = {
            "Palace": ["Palacio", "Palais", "Palazzo"],
            "Cathedral": ["Catedral", "Cathédrale", "Dom"],
            "Church": ["Iglesia", "Église", "Chiesa"],
            "Square": ["Plaza", "Place", "Piazza"],
            # Add more common translations
        }

    async def get_or_compute(self, key: str, computer: Callable) -> Dict:
        if key in self.cache:
            return self.cache[key]
        result = await computer()
        if result:
            self.cache[key] = result
        return result
```

### Day 2: Optimized OSM Service
```python
# optimized_osm_service.py
class OptimizedOSMService:
    def __init__(self):
        self.cache = LocationCache()
        self.rate_limiter = AdaptiveRateLimiter()
        
    async def validate_location(self, name: str, city: str) -> Optional[Dict]:
        # 1. Try cache
        cache_key = f"{name}:{city}".lower()
        result = await self.cache.get(cache_key)
        if result:
            return result
            
        # 2. Try direct match
        result = await self._try_direct_match(name, city)
        if result:
            await self.cache.set(cache_key, result)
            return result
            
        # 3. Try static translations
        result = await self._try_static_translations(name, city)
        if result:
            await self.cache.set(cache_key, result)
            return result
            
        # 4. Only then try expensive operations
        return await self._deep_search(name, city)
```

## Phase 2: Smart Translation (2 days)

### Day 3: LLM Integration
```python
# llm_translation_service.py
class LLMTranslationService:
    def __init__(self, llama_service: LlamaService):
        self.llama = llama_service
        
    async def get_translations(self, place_name: str) -> List[str]:
        prompt = f"""
        Translate this place name to common European languages:
        {place_name}
        
        Return format:
        language: translation
        """
        result = await self.llama.generate(prompt)
        return self._parse_translations(result)
```

### Day 4: Parallel Processing
```python
# parallel_validator.py
class ParallelValidator:
    async def validate_location(self, name: str, city: str) -> Dict:
        async with asyncio.TaskGroup() as group:
            static_task = group.create_task(
                self._try_static_translations(name, city)
            )
            llm_task = group.create_task(
                self._try_llm_translations(name, city)
            )
            
        results = [r for r in [static_task.result(), llm_task.result()] if r]
        return max(results, key=lambda x: x['confidence'], default=None)
```

## Phase 3: Optimization & Monitoring (2 days)

### Day 5: Redis Integration
```python
# redis_cache.py
class RedisLocationCache:
    def __init__(self):
        self.redis = Redis(decode_responses=True)
        self.ttl = 30 * 24 * 60 * 60  # 30 days
        
    async def get_or_set(self, key: str, computer: Callable) -> Dict:
        data = await self.redis.get(key)
        if data:
            return json.loads(data)
            
        result = await computer()
        if result:
            await self.redis.setex(
                key,
                self.ttl,
                json.dumps(result)
            )
        return result
```

### Day 6: Performance Monitoring
```python
# monitoring.py
class ValidationMetrics:
    def __init__(self):
        self.cache_hits = Counter()
        self.response_times = Histogram()
        self.success_rates = Counter()
        
    async def record_validation(
        self,
        location: str,
        success: bool,
        response_time: float,
        source: str
    ):
        self.response_times.observe(response_time)
        self.success_rates.inc(success)
        if source == 'cache':
            self.cache_hits.inc()
```

## Key Performance Metrics to Track

1. Response Times:
```
- P50: < 200ms (cached)
- P95: < 2s (translation needed)
- P99: < 5s (deep search)
```

2. Success Rates:
```
- Cache hits: > 80%
- Translation success: > 90%
- Overall success: > 95%
```

3. Resource Usage:
```
- API calls per location: < 2
- LLM calls per location: < 0.2
- Cache memory: < 100MB
```

## Testing Strategy

1. Unit Tests:
```python
async def test_fast_path():
    validator = OptimizedOSMService()
    result = await validator.validate_location(
        "Royal Palace of Madrid",
        "Madrid"
    )
    assert result['response_time'] < 0.2
    assert result['source'] == 'cache'
```

2. Integration Tests:
```python
async def test_translation_fallback():
    validator = OptimizedOSMService()
    result = await validator.validate_location(
        "Monasterio de las Descalzas Reales",
        "Madrid"
    )
    assert result['success']
    assert result['source'] in ['static', 'llm']
```

3. Load Tests:
```python
async def test_concurrent_validation():
    validator = OptimizedOSMService()
    locations = load_test_locations(100)
    results = await asyncio.gather(*[
        validator.validate_location(loc, city)
        for loc, city in locations
    ])
    assert statistics.mean(r['response_time'] for r in results) < 1.0
```

## Rollout Strategy

1. Test Environment (Day 1-3):
   - Deploy basic caching
   - Test with historical queries
   - Measure baseline metrics

2. Staging (Day 4-5):
   - Add translation services
   - Test with production traffic copy
   - Validate metrics improvements

3. Production (Day 6-7):
   - Gradual rollout (10% -> 50% -> 100%)
   - Monitor error rates
   - Ready fallback to old system

This implementation plan provides immediate performance improvements while building toward a robust, scalable solution.