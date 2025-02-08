import os
import sys
import asyncio
from dotenv import load_dotenv

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from app.services.db_client import db

async def apply_migration():
    """Apply the location_cache migration to Supabase"""
    print("Applying location_cache migration...")
    
    try:
        # Create table
        create_table = """
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
            
            constraint valid_coordinates check (
                coordinates ? 'lat' and 
                coordinates ? 'lon' and
                (coordinates->>'lat')::float between -90 and 90 and
                (coordinates->>'lon')::float between -180 and 180
            ),
            constraint valid_confidence check (confidence between 0 and 1)
        );
        """
        
        # Create indexes
        create_indexes = [
            "create index if not exists idx_location_cache_name_city on public.location_cache (original_name, city);",
            "create index if not exists idx_location_cache_coordinates on public.location_cache using gin (coordinates);",
            "create index if not exists idx_location_cache_translations on public.location_cache using gin (translations);",
            "create index if not exists idx_location_cache_last_validated on public.location_cache (last_validated);",
            "create index if not exists idx_location_cache_success_count on public.location_cache (success_count);"
        ]
        
        # Create trigger for updated_at
        create_trigger = """
        create or replace function public.set_updated_at()
        returns trigger as $$
        begin
            new.updated_at = now();
            return new;
        end;
        $$ language plpgsql;

        drop trigger if exists set_updated_at on public.location_cache;
        create trigger set_updated_at
            before update on public.location_cache
            for each row
            execute function public.set_updated_at();
        """
        
        # Execute migrations using direct table operations
        print("\nCreating table...")
        await db.client.postgrest.schema('public').rpc('raw_sql', {'sql': create_table}).execute()
        
        print("\nCreating indexes...")
        for index in create_indexes:
            await db.client.postgrest.schema('public').rpc('raw_sql', {'sql': index}).execute()
        
        print("\nCreating trigger...")
        await db.client.postgrest.schema('public').rpc('raw_sql', {'sql': create_trigger}).execute()
        
        # Enable RLS
        rls_commands = [
            "alter table public.location_cache enable row level security;",
            """
            create policy "Allow read access to authenticated users"
                on public.location_cache for select
                to authenticated
                using (true);
            """,
            """
            create policy "Allow service role to manage data"
                on public.location_cache for all
                to service_role
                using (true)
                with check (true);
            """
        ]
        
        print("\nSetting up RLS policies...")
        for cmd in rls_commands:
            await db.client.postgrest.schema('public').rpc('raw_sql', {'sql': cmd}).execute()
        
        print("\nMigration completed successfully!")
        
    except Exception as e:
        print(f"\nError applying migration: {str(e)}")
        raise

if __name__ == "__main__":
    load_dotenv()
    asyncio.run(apply_migration())