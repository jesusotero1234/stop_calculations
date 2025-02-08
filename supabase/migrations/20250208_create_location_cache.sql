-- Enable UUID generation
create extension if not exists "uuid-ossp";

-- Create location_cache table
create table if not exists public.location_cache (
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
    
    -- Add constraints
    constraint valid_coordinates check (
        coordinates ? 'lat' and 
        coordinates ? 'lon' and
        (coordinates->>'lat')::float between -90 and 90 and
        (coordinates->>'lon')::float between -180 and 180
    ),
    constraint valid_confidence check (confidence between 0 and 1)
);

-- Add indexes
create index if not exists idx_location_cache_name_city 
    on public.location_cache (original_name, city);

create index if not exists idx_location_cache_coordinates 
    on public.location_cache using gin (coordinates);

create index if not exists idx_location_cache_translations 
    on public.location_cache using gin (translations);

create index if not exists idx_location_cache_last_validated 
    on public.location_cache (last_validated);

-- Add updated_at trigger
create or replace function public.set_current_timestamp_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

create trigger set_location_cache_updated_at
    before update on public.location_cache
    for each row
    execute function public.set_current_timestamp_updated_at();

-- Add RLS policies
alter table public.location_cache enable row level security;

-- Allow read access to all authenticated users
create policy "Allow read access to all authenticated users"
    on public.location_cache for select
    to authenticated
    using (true);

-- Allow insert/update to service role
create policy "Allow service role to insert"
    on public.location_cache for insert
    to service_role
    with check (true);

create policy "Allow service role to update"
    on public.location_cache for update
    to service_role
    using (true)
    with check (true);

-- Add function to cleanup old cache entries
create or replace function public.cleanup_old_cache_entries(days integer default 30)
returns integer as $$
declare
    deleted_count integer;
begin
    delete from public.location_cache
    where last_validated < now() - (days || ' days')::interval
    and success_count < 5;
    
    get diagnostics deleted_count = row_count;
    return deleted_count;
end;
$$ language plpgsql security definer;

-- Grant permissions
grant usage on schema public to service_role;
grant all on public.location_cache to service_role;
grant execute on function public.cleanup_old_cache_entries to service_role;

-- Create cleanup job (runs daily)
select cron.schedule(
    'cleanup-location-cache',
    '0 0 * * *',  -- Run at midnight every day
    $$select public.cleanup_old_cache_entries(30)$$
);

comment on table public.location_cache is 'Cached location data with translations and validation history';