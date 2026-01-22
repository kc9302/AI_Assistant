import requests
import json

BASE_URL = "http://192.168.0.100:11434"

def check_ollama_status():
    print(f"--- Ollama Server Status ({BASE_URL}) ---")
    
    # 1. Check version
    try:
        ver = requests.get(f"{BASE_URL}/api/version").json()
        print(f"Version: {ver.get('version')}")
    except Exception as e:
        print(f"Failed to get version: {e}")

    # 2. Check running models
    try:
        ps = requests.get(f"{BASE_URL}/api/ps").json()
        models = ps.get('models', [])
        if models:
            print("\nRunning Models:")
            for m in models:
                size_gb = m.get('size', 0) / (1024**3)
                vram_gb = m.get('size_vram', 0) / (1024**3)
                print(f"- {m['name']}: {size_gb:.2f} GB (VRAM: {vram_gb:.2f} GB)")
                print(f"  ID: {m['digest'][:12]}")
                if 'details' in m:
                    print(f"  Details: {m['details']}")
        else:
            print("\nNo models currently loaded in memory.")
    except Exception as e:
        print(f"Failed to get running models: {e}")

    # 3. List all models
    try:
        tags = requests.get(f"{BASE_URL}/api/tags").json()
        print(f"\nAvailable Models Count: {len(tags.get('models', []))}")
    except Exception as e:
        print(f"Failed to get tags: {e}")

if __name__ == "__main__":
    check_ollama_status()
