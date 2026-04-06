import urllib.request
import json

def fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req) as response:
            return json.loads(response.read())
    except:
        return None

# Step 1: Get all subregion IDs from the mapview endpoint
print("🌍 Fetching all worldwide regions...")
map_data = fetch("https://services.surfline.com/kbyg/mapview?south=-60&west=-180&north=70&east=180")

if not map_data:
    print("Failed to fetch regions")
    exit()

subregions = map_data.get("data", {}).get("subregions", [])
print(f"Found {len(subregions)} regions worldwide\n")

# Step 2: Get all spots with cams from Surfline's cam endpoint
print("📷 Fetching all spots with cameras...")
cam_data = fetch("https://services.surfline.com/kbyg/cams/spottercams")
cam_spot_ids = set()
if cam_data:
    cams = cam_data if isinstance(cam_data, list) else cam_data.get("data", [])
    for cam in cams:
        spot_id = cam.get("spot", {}).get("_id") or cam.get("spotId")
        if spot_id:
            cam_spot_ids.add(spot_id)
    print(f"Found {len(cam_spot_ids)} spots with cams\n")

# Step 3: Loop all regions and find good/epic spots
SHOW_CONDITIONS = ["FAIR TO GOOD", "GOOD", "GOOD TO EPIC", "EPIC"]
condition_order = {"EPIC": 0, "GOOD TO EPIC": 1, "GOOD": 2, "FAIR TO GOOD": 3}

results = []
print("🔍 Scanning all regions for firing spots...\n")

for sr in subregions:
    region_id = sr.get("_id")
    region_name = sr.get("subregion", {}).get("name", "Unknown")
    
    data = fetch(f"https://services.surfline.com/kbyg/regions/overview?subregionId={region_id}")
    if not data:
        continue

    spots = data.get("data", {}).get("spots", [])
    for spot in spots:
        conditions = spot.get("conditions") or {}
        rating = (conditions.get("value") or "").upper()
        if rating not in SHOW_CONDITIONS:
            continue

        spot_id = spot.get("_id", "")
        has_cam = spot_id in cam_spot_ids
        
        wave_min = spot.get("waveHeight", {}).get("min", "?")
        wave_max = spot.get("waveHeight", {}).get("max", "?")
        wind_speed = spot.get("wind", {}).get("speed", 0)
        wind_dir = spot.get("wind", {}).get("directionType", "?")
        wind_mph = round(wind_speed * 1.15078, 1)
        name = spot.get("name", "Unknown")
        url = f"https://www.surfline.com/surf-report/{name.lower().replace(' ', '-')}/{spot_id}"

        results.append({
            "region": region_name,
            "name": name,
            "rating": rating,
            "wave_min": wave_min,
            "wave_max": wave_max,
            "wind_mph": wind_mph,
            "wind_dir": wind_dir,
            "has_cam": has_cam,
            "url": url,
        })

# Sort best conditions first, cams first within same condition
results.sort(key=lambda x: (condition_order.get(x["rating"], 99), not x["has_cam"]))

print("=" * 55)
print(f"{'🔥 FIRING SPOTS WORLDWIDE':^55}")
print("=" * 55)

for r in results:
    cam_label = "📷" if r["has_cam"] else "  "
    stars = {"EPIC": "⭐⭐⭐", "GOOD TO EPIC": "⭐⭐", "GOOD": "⭐", "FAIR TO GOOD": "👍"}.get(r["rating"], "")
    print(f"\n{stars} {cam_label} {r['region']} — {r['name']}")
    print(f"   {r['rating']} | {r['wave_min']}-{r['wave_max']} ft | Wind: {r['wind_mph']} mph {r['wind_dir']}")
    print(f"   {r['url']}")

print(f"\n{'=' * 55}")
print(f"Found {len(results)} firing spots | 📷 = has live cam 🤙")