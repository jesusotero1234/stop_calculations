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
    
    -- Add constraints
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

-- Create statistics function
create or replace function public.get_cache_statistics()
returns table (
    total_entries bigint,
    successful_entries bigint,
    average_confidence numeric,
    cache_hit_rate numeric,
    average_response_time numeric
) language plpgsql as $$
begin
    return query
    select
        count(*)::bigint as total_entries,
        count(*) filter (where success_count > 0)::bigint as successful_entries,
        avg(confidence)::numeric as average_confidence,
        (count(*) filter (where success_count > 0)::numeric / 
         nullif(count(*)::numeric, 0))::numeric as cache_hit_rate,
        avg((metadata->>'response_time')::numeric) as average_response_time
    from
        public.location_cache;
end;
$$;

-- Create cleanup function
create or replace function public.cleanup_old_cache_entries(
    days integer default 30,
    min_success integer default 5
) returns integer as $$
declare
    deleted_count integer;
begin
    delete from public.location_cache
    where last_validated < now() - (days || ' days')::interval
    and success_count < min_success;
    
    get diagnostics deleted_count = row_count;
    return deleted_count;
end;
$$ language plpgsql security definer;

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
grant execute on function public.cleanup_old_cache_entries to service_role;
grant execute on function public.get_cache_statistics to service_role;

-- Add helpful comments
comment on table public.location_cache is 'Cached location data with validation history';
comment on column public.location_cache.translations is 'Array of known translations/variations of the location name';
comment on column public.location_cache.success_count is 'Number of successful validations';
comment on column public.location_cache.confidence is 'Confidence score of the location match (0-1)';