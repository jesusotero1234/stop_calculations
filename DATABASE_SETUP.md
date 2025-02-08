# Database Setup Instructions

To set up the location cache database in Supabase, follow these steps:

1. Go to your Supabase project dashboard
2. Navigate to the SQL Editor
3. Copy and paste the following SQL:

```sql
-- Enable required extensions
create extension if not exists "uuid-ossp";
create extension if not exists "pg_stat_statements";

-- Create location_cache table
create table public.location_cache (
    id uuid primary key default uuid_generate_v4(),
    original_name text not null,
    city text not null,
    country text,
    translations jsonb not null default '[]'::jsonb,
    coordinates jsonb not null,
    success_count integer not null default 0,
    confidence float not null default 1.0,
    source text,
    metadata jsonb,
    last_validated timestamp with time zone default now(),
    created_at timestamp with time zone default now(),
    updated_at timestamp with time zone default now(),
    
    constraint valid_coordinates check (
        coordinates ? 'lat' and 
        coordinates ? 'lon' and
        (coordinates->>'lat')::float between -90 and 90 and
        (coordinates->>'lon')::float between -180 and 180
    ),
    constraint valid_confidence check (confidence between 0 and 1)
);

-- Add indexes for better performance
create index idx_location_cache_name_city 
    on public.location_cache (original_name, city);

create index idx_location_cache_coordinates 
    on public.location_cache using gin (coordinates);

create index idx_location_cache_translations 
    on public.location_cache using gin (translations);

create index idx_location_cache_last_validated 
    on public.location_cache (last_validated);

create index idx_location_cache_success_count
    on public.location_cache (success_count);

-- Create updated_at trigger function
create or replace function public.handle_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

-- Create trigger for updated_at
create trigger set_updated_at
    before update on public.location_cache
    for each row
    execute function public.handle_updated_at();

-- Enable RLS
alter table public.location_cache enable row level security;

-- Create RLS policies
create policy "Allow read access to all authenticated users"
    on public.location_cache for select
    to authenticated
    using (true);

create policy "Allow service role to insert/update"
    on public.location_cache for all
    to service_role
    using (true)
    with check (true);

-- Grant necessary permissions
grant usage on schema public to service_role;
grant all on public.location_cache to service_role;
grant execute on function public.handle_updated_at() to service_role;

-- Add helpful comments
comment on table public.location_cache is 'Cached location data with validation history';
comment on column public.location_cache.translations is 'Array of known translations/variations of the location name';
comment on column public.location_cache.success_count is 'Number of successful validations';
comment on column public.location_cache.confidence is 'Confidence score of the location match (0-1)';
```

4. Click "Run" to execute the SQL

## Verification

To verify the setup, run:

```sql
-- Check table exists
select * from public.location_cache limit 1;

-- Check indexes
select indexname, indexdef
from pg_indexes
where tablename = 'location_cache';

-- Check RLS policies
select * from pg_policies
where tablename = 'location_cache';
```

## Environment Variables

Make sure your `.env` file contains:

```
SUPABASE_URL=your_project_url
SUPABASE_KEY=your_anon_key
SUPABASE_SERVICE_KEY=your_service_role_key
```

## Running Tests

After setting up the database, run the tests:

```bash
python -m pytest tests/test_location_cache.py -v
```

This will verify that the location cache is working correctly with your Supabase setup.