"""
TSE API Explorer
Verkenningsscript voor The Sourcing Engine API
Base URL: https://dcpeople-staging.thesourcingengine.io/api/data/v1
API Key: uit .env als TSE_API_KEY
"""

from dotenv import load_dotenv
import os
import requests
import json

load_dotenv()

API_KEY = os.getenv("TSE_API_KEY")
BASE_URL = "https://dcpeople-staging.thesourcingengine.io/api/data/v1"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

def test_connection():
    """Test of de API bereikbaar is en de key geldig is."""
    print("=" * 60)
    print("1. VERBINDINGSTEST")
    print("=" * 60)
    try:
        r = requests.get(BASE_URL, headers=HEADERS, timeout=10)
        print(f"Status: {r.status_code}")
        print(f"Response: {r.text[:500]}")
    except Exception as e:
        print(f"Fout: {e}")

def try_common_endpoints():
    """Probeer veelgebruikte REST API endpoints."""
    print("\n" + "=" * 60)
    print("2. ENDPOINT VERKENNING")
    print("=" * 60)
    
    endpoints = [
        "/",
        "/candidates",
        "/profiles",
        "/people",
        "/contacts",
        "/search",
        "/stats",
        "/schema",
        "/fields",
        "/meta",
        "/health",
        "/status",
        "/candidates?limit=1",
        "/profiles?limit=1",
        "/people?limit=1",
    ]
    
    for ep in endpoints:
        url = BASE_URL + ep
        try:
            r = requests.get(url, headers=HEADERS, timeout=8)
            status = r.status_code
            if status == 200:
                print(f"✓ {ep} → {status} — {r.text[:200]}")
            elif status == 401:
                print(f"✗ {ep} → {status} (Unauthorized — key ongeldig?)")
            elif status == 403:
                print(f"✗ {ep} → {status} (Forbidden — geen toegang)")
            elif status == 404:
                print(f"  {ep} → {status} (Not found)")
            else:
                print(f"? {ep} → {status} — {r.text[:100]}")
        except Exception as e:
            print(f"  {ep} → Error: {e}")

def get_sample_profile():
    """Haal één profiel op en toon alle velden."""
    print("\n" + "=" * 60)
    print("3. SAMPLE PROFIEL — VELDSTRUCTUUR")
    print("=" * 60)
    
    sample_endpoints = [
        "/candidates?limit=1",
        "/profiles?limit=1",
        "/people?limit=1",
        "/candidates?per_page=1&page=1",
    ]
    
    for ep in sample_endpoints:
        url = BASE_URL + ep
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code == 200:
                data = r.json()
                print(f"Endpoint: {ep}")
                print(f"Type response: {type(data)}")
                if isinstance(data, list) and len(data) > 0:
                    print(f"Aantal items: {len(data)}")
                    print(f"\nVelden in eerste item:")
                    for k, v in data[0].items():
                        print(f"  {k}: {type(v).__name__} = {str(v)[:80]}")
                    break
                elif isinstance(data, dict):
                    print(f"Keys: {list(data.keys())}")
                    # Zoek naar een lijst in de response
                    for k, v in data.items():
                        if isinstance(v, list) and len(v) > 0:
                            print(f"\nLijst gevonden onder '{k}' ({len(v)} items)")
                            print(f"Velden in eerste item:")
                            for fk, fv in v[0].items():
                                print(f"  {fk}: {type(fv).__name__} = {str(fv)[:80]}")
                            break
                    break
        except Exception as e:
            print(f"  {ep} → Error: {e}")

def get_total_count():
    """Probeer het totaal aantal profielen op te halen."""
    print("\n" + "=" * 60)
    print("4. TOTAAL AANTAL PROFIELEN")
    print("=" * 60)
    
    count_endpoints = [
        "/candidates/count",
        "/profiles/count",
        "/stats",
        "/candidates?limit=1",
        "/profiles?limit=1",
    ]
    
    for ep in count_endpoints:
        url = BASE_URL + ep
        try:
            r = requests.get(url, headers=HEADERS, timeout=10)
            if r.status_code == 200:
                print(f"Endpoint: {ep}")
                data = r.json()
                print(f"Response: {json.dumps(data, indent=2)[:500]}")
                break
        except Exception as e:
            print(f"  {ep} → Error: {e}")

if __name__ == "__main__":
    print(f"TSE API Explorer")
    print(f"Base URL: {BASE_URL}")
    print(f"API Key geladen: {'Ja' if API_KEY else 'NEE — voeg TSE_API_KEY toe aan .env'}")
    print()
    
    if not API_KEY:
        print("STOP: Voeg TSE_API_KEY=<jouw_key> toe aan je .env bestand")
        exit(1)
    
    test_connection()
    try_common_endpoints()
    get_sample_profile()
    get_total_count()
    
    print("\n" + "=" * 60)
    print("KLAAR — zie bovenstaande output voor API structuur")
    print("=" * 60)
