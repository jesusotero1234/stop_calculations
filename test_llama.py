import asyncio
import aiohttp
import json
import sys
import socket
from typing import Optional, Tuple
import os

async def test_connection(url: str) -> Tuple[bool, Optional[str]]:
    """Test connection and return success status and response"""
    print(f"\nTrying {url}...")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                url,
                json={
                    "model": "phi4:latest",
                    "prompt": "Say 'connected' if you can read this.",
                    "stream": False
                },
                timeout=30
            ) as response:
                print(f"Response status: {response.status}")
                
                if response.status == 200:
                    result = await response.json()
                    response_text = result.get("response", "")
                    print("\nResponse:", response_text[:100], "..." if len(response_text) > 100 else "")
                    return True, response_text
                else:
                    error_text = await response.text()
                    print(f"Error response: {error_text}")
                    return False, None
                    
    except aiohttp.ClientError as e:
        print(f"Connection error: {str(e)}")
        return False, None
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return False, None

async def find_working_host() -> Optional[str]:
    """Test different host configurations and return the working one"""
    print("\n=== Testing Llama Connectivity ===")

    # Get local machine info
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    print(f"\nLocal machine info:")
    print(f"Hostname: {hostname}")
    print(f"IP Address: {local_ip}")

    # Test configurations
    configs = [
        ("Local Docker", "host.docker.internal"),
        ("Localhost", "localhost"),
        ("Loopback", "127.0.0.1"),
        ("Local IP", local_ip)
    ]

    print("\nTesting different host configurations...")
    for name, host in configs:
        print(f"\n➡️  Testing {name} ({host}):")
        url = f"http://{host}:11434/v1/completions"
        success, response = await test_connection(url)
        
        if success:
            print(f"✅ Success! {name} ({host}) works")
            return host
        else:
            print(f"❌ {name} ({host}) failed")

    return None

def update_env_file(host: str):
    """Update .env file with working configuration"""
    env_content = f"""# API Configuration
API_TITLE="Tour Generator"
API_VERSION="2.0.0"

# Llama Configuration
LLAMA_HOST={host}
LLAMA_PORT=11434

# Service Configuration
MIN_STOPS=2
MAX_STOPS=15
MIN_DURATION=30
MAX_DURATION=240
MAX_DESCRIPTION_LENGTH=500

# Monitoring Configuration
MONITORING_PORT=9090
LOG_LEVEL=DEBUG

# API Settings
API_PORT=8001
API_HOST=0.0.0.0"""

    with open(".env", "w") as f:
        f.write(env_content)
    print("\n✅ Updated .env file with working configuration")

def print_next_steps(host: Optional[str]):
    """Print next steps based on test results"""
    if host:
        print("\n✅ Llama connection successful!")
        print("\nNext steps:")
        print("1. Start the service:")
        print("   docker compose up --build")
        print("\n2. Test the API:")
        print("   curl http://localhost:8001")
        print("\n3. Generate a tour:")
        print("""   curl -X POST http://localhost:8001/generate-tour \\
     -H "Content-Type: application/json" \\
     -d '{
       "city": "Madrid",
       "theme": "Historical",
       "duration": 120,
       "language": "en-us"
     }'""")
    else:
        print("\n❌ Could not connect to Llama")
        print("\nTroubleshooting steps:")
        print("1. Check if Ollama is running:")
        print("   ollama list")
        print("\n2. Start Ollama if needed:")
        print("   ollama run phi4:latest")
        print("\n3. Try running this test again")

if __name__ == "__main__":
    print("\n🔍 Testing Llama Connection")
    print("==========================")
    print(f"Python version: {sys.version}")
    
    # Run tests
    working_host = asyncio.run(find_working_host())
    
    if working_host:
        # Update configuration
        update_env_file(working_host)
    
    # Print next steps
    print_next_steps(working_host)
    print("\nTest complete.")