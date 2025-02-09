#!/usr/bin/env python3
import os
import sys
import asyncio
from datetime import datetime, timedelta
import logging
from dotenv import load_dotenv

# Add project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(project_root)

from app.models.location_cache import LocationCache
from app.services.monitoring_service import monitoring

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def analyze_cache_performance():
    """Analyze and report cache performance metrics"""
    try:
        # Get cache statistics
        stats = await LocationCache.get_stats()
        
        logger.info("Cache Performance Report")
        logger.info("=" * 50)
        logger.info(f"Total Entries: {stats.get('total_entries', 0)}")
        logger.info(f"Successful Entries: {stats.get('successful_entries', 0)}")
        
        if stats.get('total_entries', 0) > 0:
            hit_rate = (stats.get('successful_entries', 0) / stats.get('total_entries', 0)) * 100
            logger.info(f"Cache Hit Rate: {hit_rate:.2f}%")
        
        logger.info(f"Average Confidence: {stats.get('average_confidence', 0):.2f}")
        
        # Get monitoring metrics
        metrics = monitoring.get_metrics()
        
        # Analyze response times
        cache_hits_latency = metrics.get_sample_value(
            'service_request_latency_seconds_sum',
            {'cache_status': 'hit'}
        ) or 0
        cache_hits_count = metrics.get_sample_value(
            'service_request_latency_seconds_count',
            {'cache_status': 'hit'}
        ) or 1
        
        cache_misses_latency = metrics.get_sample_value(
            'service_request_latency_seconds_sum',
            {'cache_status': 'miss'}
        ) or 0
        cache_misses_count = metrics.get_sample_value(
            'service_request_latency_seconds_count',
            {'cache_status': 'miss'}
        ) or 1
        
        avg_hit_time = cache_hits_latency / cache_hits_count
        avg_miss_time = cache_misses_latency / cache_misses_count
        
        logger.info("\nResponse Times")
        logger.info("-" * 50)
        logger.info(f"Average Cache Hit Time: {avg_hit_time:.3f}s")
        logger.info(f"Average Cache Miss Time: {avg_miss_time:.3f}s")
        logger.info(f"Time Saved per Hit: {(avg_miss_time - avg_hit_time):.3f}s")
        
        # Analyze translations
        translations = {}
        for lang_pair in ['en-es', 'es-en', 'en-de', 'de-en']:
            source, target = lang_pair.split('-')
            count = metrics.get_sample_value(
                'location_translations_found_total',
                {'source_language': source, 'target_language': target}
            ) or 0
            translations[lang_pair] = count
        
        logger.info("\nTranslations")
        logger.info("-" * 50)
        for pair, count in translations.items():
            logger.info(f"{pair}: {count} translations")
        
        # Check for cleanup candidates
        cutoff_date = (datetime.utcnow() - timedelta(days=30)).isoformat()
        cleanup_candidates = await LocationCache.cleanup_old_entries(
            days=30,
            min_success=5
        )
        
        logger.info("\nMaintenance")
        logger.info("-" * 50)
        logger.info(f"Entries eligible for cleanup: {cleanup_candidates}")
        
    except Exception as e:
        logger.error(f"Error analyzing cache performance: {str(e)}")
        raise

def main():
    """Main entry point"""
    load_dotenv()
    
    try:
        asyncio.run(analyze_cache_performance())
    except KeyboardInterrupt:
        logger.info("\nMonitoring stopped by user")
    except Exception as e:
        logger.error(f"Monitoring failed: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()