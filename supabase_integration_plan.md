# Supabase Integration Plan for Location Cache

## 1. Database Schema

### Table: location_cache
```sql
create table public.location_cache (
    id uuid default uuid_generate_v4() primary key,
    original_name text not null,
    city text not null,
    country text,
    translations jsonb default '[]',
    coordinates jsonb not null,
    last_validated timestamp with time zone default now(),
    success_count integer default 0,
    confidence float default 1.0,
    source text,
    metadata jsonb default '{}'::jsonb,
    created_at timestamp with time zone default now(),
    updated_at timestamp with time zone default now()
);

-- Add indexes
create index idx_location_cache_name_city on location_cache (original_name, city);
create index idx_location_cache_coordinates on location_cache using gin (coordinates);
create index idx_location_cache_translations on location_cache using gin (translations);
```

### Function: update_location_cache
```sql
create or replace function update_location_cache_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

create trigger set_location_cache_timestamp
    before update on location_cache
    for each row
    execute procedure update_location_cache_updated_at();
```

### RLS Policies
```sql
-- Enable RLS
alter table location_cache enable row level security;

-- Allow read access to all authenticated users
create policy "Allow read access to all authenticated users"
    on location_cache for select
    to authenticated
    using (true);

-- Allow insert/update only to service role
create policy "Allow insert/update to service role"
    on location_cache for insert
    to service_role
    with check (true);
```

## 2. Integration Steps

### 2.1 Update Supabase Client
```typescript
// Location cache type definitions
interface LocationCache {
    id: string;
    original_name: string;
    city: string;
    country?: string;
    translations: string[];
    coordinates: {
        latitude: number;
        longitude: number;
    };
    last_validated: Date;
    success_count: number;
    confidence: number;
    source: string;
    metadata: Record<string, any>;
}
```

### 2.2 OSMService Integration
```python
class OSMService:
    async def get_cached_location(self, name: str, city: str) -> Optional[Dict]:
        result = await self.supabase.table('location_cache')\
            .select('*')\
            .eq('original_name', name)\
            .eq('city', city)\
            .single()\
            .execute()
            
        if result.data:
            await self._update_success_count(result.data['id'])
            return result.data
        return None

    async def cache_location(self, data: Dict) -> None:
        await self.supabase.table('location_cache')\
            .insert(data)\
            .execute()
```

## 3. GitHub Integration

### 3.1 Repository Structure
```
stop_calculations/
├── app/
│   ├── services/
│   │   ├── osm_service.py
│   │   └── ...
│   ├── models/
│   └── ...
├── supabase/
│   └── migrations/
│       ├── 20250208_create_location_cache_table.sql
│       └── ...
├── tests/
│   └── ...
├── .env.example
├── .gitignore
└── README.md
```

### 3.2 GitHub Actions Workflow
```yaml
name: Deploy Migrations

on:
  push:
    branches: [ main ]
    paths:
      - 'supabase/migrations/**'

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Deploy Migrations
        run: npx supabase db push
        env:
          SUPABASE_ACCESS_TOKEN: ${{ secrets.SUPABASE_ACCESS_TOKEN }}
          SUPABASE_DB_PASSWORD: ${{ secrets.SUPABASE_DB_PASSWORD }}
```

## 4. Implementation Timeline

### Day 1: Database Setup
1. Create migration file
2. Test locally with Supabase CLI
3. Apply migration to development environment
4. Verify RLS policies

### Day 2: Service Integration
1. Update OSMService with caching logic
2. Add cache invalidation strategy
3. Implement monitoring for cache hits/misses
4. Add logging for performance metrics

### Day 3: Testing & Deployment
1. Write integration tests
2. Set up GitHub Actions
3. Deploy to staging
4. Monitor performance improvements

## 5. Key Metrics to Track

1. Cache Performance:
   - Hit rate
   - Average response time with/without cache
   - Cache invalidation frequency

2. Storage Usage:
   - Number of cached locations
   - Average translations per location
   - Storage growth rate

3. Validation Success:
   - Success rate by city/country
   - Most common failed lookups
   - Translation effectiveness

## 6. Rollback Plan

### Quick Rollback
```sql
-- If needed, we can quickly disable the cache without dropping it
create or replace function bypass_cache() returns boolean as $$
begin
    return false;
end;
$$ language plpgsql;

-- To re-enable
create or replace function bypass_cache() returns boolean as $$
begin
    return true;
end;
$$ language plpgsql;
```

This plan provides a structured approach to implementing the location cache in Supabase while maintaining security and performance.