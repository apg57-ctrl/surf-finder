import urllib.request
import json
import time

def fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read())
    except:
        return None

def get_location(lat, lon):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&accept-language=en"
        req = urllib.request.Request(url, headers={"User-Agent": "SurfChecker/1.0"})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read())
        addr = data.get("address", {})
        city = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("county") or ""
        country = addr.get("country", "")
        return f"{city}, {country}" if city else country
    except:
        return ""

# Load cam spots with lat/lon
with open("cam_spots.json") as f:
    cam_spots = json.load(f)

cam_lookup = {s["id"]: s for s in cam_spots}
cam_spot_ids = list(cam_lookup.keys())

print(f"Loaded {len(cam_spot_ids)} cam spots")
print("🔍 Checking each cam spot for FAIR TO GOOD+ conditions at 6ft+...\n")

SHOW_CONDITIONS = ["FAIR TO GOOD", "GOOD", "GOOD TO EPIC", "EPIC"]
condition_order = {"EPIC": 0, "GOOD TO EPIC": 1, "GOOD": 2, "FAIR TO GOOD": 3}
results = []

for i, spot_id in enumerate(cam_spot_ids):
    if i % 50 == 0:
        print(f"  Checking spot {i}/{len(cam_spot_ids)}...")

    data = fetch(f"https://services.surfline.com/kbyg/spots/forecasts/rating?spotId={spot_id}&days=1")
    if not data:
        continue
    ratings = data.get("data", {}).get("rating", [])
    if not ratings:
        continue

    current = ratings[0]
    rating = (current.get("rating", {}).get("key") or "").upper().replace("_", " ")
    if rating not in SHOW_CONDITIONS:
        continue

    # Check wave height — must be 6ft or higher
    wave_data = fetch(f"https://services.surfline.com/kbyg/spots/forecasts/wave?spotId={spot_id}&days=1")
    if not wave_data:
        continue
    wave_entry = wave_data["data"]["wave"][0]["surf"]
    wave_min = wave_entry.get("min", 0)
    wave_max = wave_entry.get("max", 0)
    if wave_max < 6:
        continue

    spot = cam_lookup.get(spot_id, {})
    name = spot.get("name", "Unknown")
    lat = spot.get("lat")
    lon = spot.get("lon")
    location = get_location(lat, lon) if lat and lon else ""
    time.sleep(1)  # be polite to OpenStreetMap

    url = f"https://www.surfline.com/surf-report/{name.lower().replace(' ', '-')}/{spot_id}"
    results.append({"name": name, "location": location, "rating": rating, "wave_min": wave_min, "wave_max": wave_max, "url": url})
    print(f"  ✅ Found: {name} — {location} — {rating} — {wave_min}-{wave_max} ft")

results.sort(key=lambda x: condition_order.get(x["rating"], 99))

print("\n" + "=" * 55)
print(f"{'🔥 FIRING SPOTS WITH CAMS (6ft+)':^55}")
print("=" * 55)

if results:
    for r in results:
        stars = {"EPIC": "⭐⭐⭐", "GOOD TO EPIC": "⭐⭐", "GOOD": "⭐", "FAIR TO GOOD": "👍"}.get(r["rating"], "")
        print(f"\n{stars} 📷 {r['name']} — {r['location']}")
        print(f"   {r['rating']} | Waves: {r['wave_min']}-{r['wave_max']} ft")
        print(f"   {r['url']}")
else:
    print("\n  No FAIR TO GOOD+ spots with cams at 6ft+ right now.")
    print("  Check back when a swell is in the water! 🌊")

print(f"\n{'=' * 55}")
print(f"Found {len(results)} spots 🤙")
