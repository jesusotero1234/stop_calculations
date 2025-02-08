import asyncio
import logging
from app.services.osm_service import OSMService
from app.services.monitoring_service import MonitoringService
from datetime import datetime

# Full set of Madrid locations
MADRID_LOCATIONS = [
    "Royal Palace of Madrid",
    "Plaza Mayor",
    "Almudena Cathedral",
    "Palacio Real de Oriente (formerly New Palace)",
    "Monastery of the Descalzas Reales",
    "Temple of Debod",
    "San Antonio de los Alemanes Church",
    "Convent of Las Descalzas Reales Church and Oratory",
    "Santa Maria la Real de la Almudena Church",
    "Plaza de Oriente",
    "Royal Palace Theater (Teatro Real)",
    "Cuartel de la Montaa, site of the Dos de Mayo Uprising Memorial",
    "Palace of Buenavista",
    "Puerta del Sol",
    "San Francisco el Grande Church"
]

class MockMonitoringService:
    """Mock monitoring service that tracks the last recorded metrics"""
    def __init__(self):
        self.last_metrics = {}
        self.all_metrics = []
        
    def record_osm_metrics(self, response_time, success, match_quality=None, match_type="exact"):
        metrics = {
            "response_time": response_time,
            "success": success,
            "match_quality": match_quality,
            "match_type": match_type,
            "timestamp": datetime.now().isoformat()
        }
        self.last_metrics = metrics
        self.all_metrics.append(metrics)
        print(f"Recorded metrics: {metrics}")

    def get_summary(self):
        if not self.all_metrics:
            return {}
            
        total = len(self.all_metrics)
        successes = sum(1 for m in self.all_metrics if m["success"])
        avg_time = sum(m["response_time"] for m in self.all_metrics) / total
        match_types = {
            "exact": sum(1 for m in self.all_metrics if m["match_type"] == "exact"),
            "alternate": sum(1 for m in self.all_metrics if m["match_type"] == "alternate"),
            "none": sum(1 for m in self.all_metrics if m["match_type"] == "none")
        }
        
        return {
            "total_requests": total,
            "success_rate": successes / total,
            "average_response_time": avg_time,
            "match_types": match_types
        }

async def test_all_locations(threshold: float = 0.8):
    """Test all Madrid locations with given similarity threshold"""
    # Configure logging
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    print(f"\nTesting all locations with similarity threshold: {threshold}")
    print("=" * 80)
    
    monitoring = MockMonitoringService()
    osm_service = OSMService(monitoring)
    osm_service.set_similarity_threshold(threshold)
    
    results = {
        "exact": [],
        "alternate": [],
        "none": [],
        "error": []
    }
    
    start_time = datetime.now()
    
    for location in MADRID_LOCATIONS:
        print(f"\nValidating: {location}")
        try:
            result = await osm_service.validate_and_get_coordinates(location, "Madrid")
            
            if result:
                match_type = monitoring.last_metrics["match_type"]
                match_quality = monitoring.last_metrics.get("match_quality", 1.0)
                print(f"✅ Valid - Type: {match_type}, Quality: {match_quality:.2f}")
                print(f"   Coordinates: {result['latitude']:.6f}, {result['longitude']:.6f}")
                
                results[match_type].append({
                    "name": location,
                    "quality": match_quality,
                    "coords": (result['latitude'], result['longitude'])
                })
            else:
                print(f"❌ Invalid - No match found")
                results["none"].append({"name": location})
                
        except Exception as e:
            print(f"Error validating {location}: {str(e)}")
            results["error"].append({"name": location, "error": str(e)})
        
        # Always wait between requests to respect rate limiting
        await asyncio.sleep(1.1)
    
    # Calculate execution time
    duration = (datetime.now() - start_time).total_seconds()
    
    # Get monitoring summary
    summary = monitoring.get_summary()
    
    # Print detailed results
    print("\nValidation Results")
    print("=" * 80)
    print(f"Total locations tested: {len(MADRID_LOCATIONS)}")
    print(f"Total time: {duration:.1f}s")
    print(f"Average response time: {summary['average_response_time']:.2f}s")
    print(f"Success rate: {summary['success_rate']*100:.1f}%")
    print("\nMatch Types:")
    print(f"  Exact: {summary['match_types']['exact']}")
    print(f"  Alternate: {summary['match_types']['alternate']}")
    print(f"  None: {summary['match_types']['none']}")
    
    if results['exact']:
        print("\nExact Matches:")
        for match in results['exact']:
            print(f"- {match['name']} (quality: 1.00)")
    
    if results['alternate']:
        print("\nAlternate Matches:")
        for match in results['alternate']:
            print(f"- {match['name']} (quality: {match['quality']:.2f})")
    
    if results['none']:
        print("\nFailed Matches:")
        for match in results['none']:
            print(f"- {match['name']}")
    
    if results['error']:
        print("\nErrors:")
        for err in results['error']:
            print(f"- {err['name']}: {err['error']}")
    
    return summary["success_rate"] >= 0.8  # Consider successful if 80%+ matches

async def main():
    """Run tests with different similarity thresholds"""
    print("Starting OSM Validation Test - Full Madrid Locations")
    print("=" * 80)
    
    thresholds = [0.8, 0.7, 0.6]  # Try progressively lower thresholds if needed
    
    for threshold in thresholds:
        success = await test_all_locations(threshold)
        if success:
            print(f"\n✅ Test successful with threshold {threshold}")
            break
        else:
            print(f"\n❌ Test failed with threshold {threshold}")
            if threshold != thresholds[-1]:
                print("Trying lower threshold...")
                await asyncio.sleep(2)  # Wait before trying next threshold

if __name__ == "__main__":
    asyncio.run(main())