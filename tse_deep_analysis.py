"""
TSE Deep Analysis Script
Haalt structuurinformatie op uit alle 6 endpoints van de TSE API.
Doel: begrijpen wat er nu in de database zit en wat ontbreekt.

Base URL: https://dcpeople-staging.thesourcingengine.io/api/data/v1
API Key: uit .env als TSE_API_KEY
"""

from dotenv import load_dotenv
import os
import requests
import json
from collections import Counter

load_dotenv()

API_KEY = os.getenv("TSE_API_KEY")
BASE_URL = "https://dcpeople-staging.thesourcingengine.io/api/data/v1"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}

def get_json(endpoint, params=None):
    url = BASE_URL + endpoint
    r = requests.get(url, headers=HEADERS, params=params, timeout=15)
    if r.status_code == 200:
        try:
            return r.json()
        except:
            return None
    return None

def section(title):
    print("\n" + "=" * 60)
    print(title)
    print("=" * 60)

# ─────────────────────────────────────────────
# 1. TOTALE COUNTS PER ENDPOINT
# ─────────────────────────────────────────────
section("1. TOTALE COUNTS PER ENDPOINT")

endpoints = [
    ("/candidates", "Kandidaten"),
    ("/vacancies", "Vacatures"),
    ("/clients", "Klanten"),
    ("/placements", "Plaatsingen"),
    ("/pipeline", "Pipeline entries"),
    ("/candidate-notes", "Kandidaat notities"),
]

totals = {}
for ep, label in endpoints:
    data = get_json(ep, params={"limit": 1})
    if data and "total" in data:
        totals[ep] = data["total"]
        print(f"  {label:30s} → {data['total']:,} records")
    else:
        print(f"  {label:30s} → kon niet ophalen")

# ─────────────────────────────────────────────
# 2. KANDIDATEN — STATUS VERDELING
# ─────────────────────────────────────────────
section("2. KANDIDATEN — STATUS VERDELING")

total_candidates = totals.get("/candidates", 0)
if total_candidates > 0:
    # Haal eerste 500 op voor steekproef
    sample_size = min(500, total_candidates)
    data = get_json("/candidates", params={"limit": sample_size, "page": 1})
    if data and "items" in data:
        items = data["items"]
        status_count = Counter(c.get("status") for c in items)
        source_count = Counter(c.get("source") for c in items)
        open_to_work = sum(1 for c in items if c.get("openToWork") is True)
        has_location = sum(1 for c in items if c.get("location") is not None)
        has_company = sum(1 for c in items if c.get("company") is not None)
        has_skills = sum(1 for c in items if c.get("skills") and len(c.get("skills", [])) > 0)
        has_scraped_on = sum(1 for c in items if c.get("scrapedOn") is not None)
        has_branche = sum(1 for c in items if c.get("branche") is not None)
        has_industry = sum(1 for c in items if c.get("industry") is not None)
        
        print(f"\nSteekproef: {len(items)} van {total_candidates:,} kandidaten\n")
        
        print("STATUS verdeling:")
        for status, count in status_count.most_common():
            pct = count / len(items) * 100
            print(f"  {str(status):30s} → {count:4d} ({pct:.1f}%)")
        
        print("\nSOURCE verdeling:")
        for source, count in source_count.most_common():
            pct = count / len(items) * 100
            print(f"  {str(source):30s} → {count:4d} ({pct:.1f}%)")
        
        print(f"\nVELD VULLING (in steekproef van {len(items)}):")
        print(f"  openToWork = True         → {open_to_work:4d} ({open_to_work/len(items)*100:.1f}%)")
        print(f"  location gevuld           → {has_location:4d} ({has_location/len(items)*100:.1f}%)")
        print(f"  company gevuld            → {has_company:4d} ({has_company/len(items)*100:.1f}%)")
        print(f"  skills gevuld             → {has_skills:4d} ({has_skills/len(items)*100:.1f}%)")
        print(f"  scrapedOn gevuld          → {has_scraped_on:4d} ({has_scraped_on/len(items)*100:.1f}%)")
        print(f"  branche gevuld            → {has_branche:4d} ({has_branche/len(items)*100:.1f}%)")
        print(f"  industry gevuld           → {has_industry:4d} ({has_industry/len(items)*100:.1f}%)")

# ─────────────────────────────────────────────
# 3. PIPELINE — STAGES ANALYSE
# ─────────────────────────────────────────────
section("3. PIPELINE — STAGES ANALYSE")

pipeline_data = get_json("/pipeline", params={"limit": 500})
if pipeline_data and "items" in pipeline_data:
    items = pipeline_data["items"]
    print(f"\nTotaal pipeline entries: {pipeline_data.get('total', '?'):,}")
    print(f"Steekproef: {len(items)} items\n")
    
    # Toon veldstructuur van eerste item
    if items:
        print("VELDSTRUCTUUR pipeline entry:")
        for k, v in items[0].items():
            print(f"  {k}: {type(v).__name__} = {str(v)[:80]}")
        
        # Stage verdeling
        stage_count = Counter(item.get("stage") for item in items)
        print(f"\nSTAGE verdeling:")
        for stage, count in stage_count.most_common():
            pct = count / len(items) * 100
            print(f"  {str(stage):35s} → {count:4d} ({pct:.1f}%)")
        
        # Rejection reason check
        has_rejection = sum(1 for item in items if item.get("rejectionReason") or item.get("rejection_reason"))
        print(f"\nrejectionReason gevuld    → {has_rejection} van {len(items)}")

# ─────────────────────────────────────────────
# 4. VACATURES — STRUCTUUR
# ─────────────────────────────────────────────
section("4. VACATURES — STRUCTUUR EN AANTALLEN")

vac_data = get_json("/vacancies", params={"limit": 5})
if vac_data and "items" in vac_data:
    print(f"Totaal vacatures: {vac_data.get('total', '?'):,}")
    if vac_data["items"]:
        print("\nVeldstructuur vacature:")
        for k, v in vac_data["items"][0].items():
            print(f"  {k}: {type(v).__name__} = {str(v)[:80]}")

# ─────────────────────────────────────────────
# 5. KLANTEN — STRUCTUUR
# ─────────────────────────────────────────────
section("5. KLANTEN — STRUCTUUR (CTS GROUP + PARTNERS?)")

client_data = get_json("/clients", params={"limit": 50})
if client_data and "items" in client_data:
    print(f"Totaal klanten: {client_data.get('total', '?'):,}")
    if client_data["items"]:
        print("\nVeldstructuur klant:")
        for k, v in client_data["items"][0].items():
            print(f"  {k}: {type(v).__name__} = {str(v)[:80]}")
        
        print(f"\nAlle klanten ({len(client_data['items'])}):")
        for c in client_data["items"]:
            name = c.get("name") or c.get("companyName") or c.get("clientName") or str(c.get("id"))
            print(f"  - {name}")

# ─────────────────────────────────────────────
# 6. PLAATSINGEN — STRUCTUUR
# ─────────────────────────────────────────────
section("6. PLAATSINGEN — STRUCTUUR")

place_data = get_json("/placements", params={"limit": 5})
if place_data and "items" in place_data:
    print(f"Totaal plaatsingen: {place_data.get('total', '?'):,}")
    if place_data["items"]:
        print("\nVeldstructuur plaatsing:")
        for k, v in place_data["items"][0].items():
            print(f"  {k}: {type(v).__name__} = {str(v)[:80]}")

# ─────────────────────────────────────────────
# 7. CANDIDATE NOTES — STRUCTUUR
# ─────────────────────────────────────────────
section("7. CANDIDATE NOTES — STRUCTUUR")

notes_data = get_json("/candidate-notes", params={"limit": 3})
if notes_data and "items" in notes_data:
    print(f"Totaal notities: {notes_data.get('total', '?'):,}")
    if notes_data["items"]:
        print("\nVeldstructuur notitie:")
        for k, v in notes_data["items"][0].items():
            print(f"  {k}: {type(v).__name__} = {str(v)[:80]}")

print("\n" + "=" * 60)
print("ANALYSE KLAAR")
print("=" * 60)
