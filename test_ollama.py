import requests
import json
import sys

def test_ollama_connection():
    """Test direct connection to Ollama"""
    print("\n=== Testing Ollama Connection ===")
    
    # Test configurations
    hosts = [
        "localhost",
        "127.0.0.1",
        "host.docker.internal"
    ]
    
    request_data = {
        "model": "phi4:latest",
        "prompt": "Say 'hello'",
        "stream": False
    }
    
    for host in hosts:
        url = f"http://{host}:11434/v1/completions"
        print(f"\nTrying {url}...")
        print(f"Request data: {json.dumps(request_data, indent=2)}")
        
        try:
            response = requests.post(url, json=request_data, timeout=10)
            print(f"Status code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print("Success! Response:")
                print(json.dumps(result, indent=2))
                return True
            else:
                print(f"Error response: {response.text}")
        except requests.exceptions.RequestException as e:
            print(f"Connection error: {str(e)}")
            print(f"Error type: {type(e).__name__}")
    
    return False

def check_ollama_status():
    """Check if Ollama is running and model is available"""
    print("\n=== Checking Ollama Status ===")
    
    # Try to list models
    url = "http://localhost:11434/api/tags"
    try:
        response = requests.get(url)
        print(f"\nOllama status: {response.status_code}")
        if response.status_code == 200:
            models = response.json()
            print("\nAvailable models:")
            print(json.dumps(models, indent=2))
            
            # Check for phi4
            if any('phi4' in model.get('name', '') for model in models):
                print("\n✅ phi4 model is available")
            else:
                print("\n❌ phi4 model not found")
    except requests.exceptions.RequestException as e:
        print("\n❌ Could not connect to Ollama")
        print(f"Error: {str(e)}")

if __name__ == "__main__":
    print("\n🔍 Testing Ollama Integration")
    print("============================")
    print(f"Python version: {sys.version}")
    
    # First check Ollama status
    check_ollama_status()
    
    # Then test connection
    if test_ollama_connection():
        print("\n✅ Successfully connected to Ollama")
    else:
        print("\n❌ Could not connect to Ollama")
        print("\nTroubleshooting steps:")
        print("1. Check if Ollama is running:")
        print("   ps aux | grep ollama")
        print("\n2. Check if phi4 model is available:")
        print("   ollama list")
        print("\n3. Try starting Ollama:")
        print("   ollama run phi4:latest")