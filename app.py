from flask import Flask, render_template, request, jsonify
import urllib.request
import json
import time
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)

CACHE_FILE = "results_cache.json"
CACHE_MAX_AGE = 60 * 60 * 6  # 6 hours

def fetch(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            return json.loads(response.read())
    except:
        return None

def get_location(lat, lon):
    try:
        url = f"https://nominatim.openstreetmap.org/reverse?lat={lat}&lon={lon}&format=json&accept-language=en"
        req = urllib.request.Request(url, headers={"User-Agent": "SurfChecker/1.0"})
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read())
        addr = data.get("address", {})
        city = addr.get("city") or addr.get("town") or addr.get("village") or addr.get("county") or ""
        country = addr.get("country", "")
        code = addr.get("country_code", "").upper()
        return {"city": city, "country": country, "code": code}
    except:
        return {"city": "", "country": "", "code": ""}

REGION_MAP = {
    "US": "North America", "CA": "North America",
    "MX": "Central America", "CR": "Central America", "SV": "Central America",
    "NI": "Central America", "PA": "Central America", "GT": "Central America",
    "BR": "South America", "CL": "South America", "PE": "South America",
    "CO": "South America", "EC": "South America", "AR": "South America",
    "FR": "Europe", "PT": "Europe", "ES": "Europe", "GB": "Europe",
    "ID": "Indonesia", "AU": "Australia", "ZA": "Africa", "MA": "Africa",
    "PF": "Pacific Islands", "FJ": "Pacific Islands",
}

def check_spot(spot):
    spot_id = spot["id"]
    data = fetch(f"https://services.surfline.com/kbyg/spots/forecasts/rating?spotId={spot_id}&days=1")
    if not data:
        return None
    ratings = data.get("data", {}).get("rating", [])
    if not ratings:
        return None
    current = ratings[0]
    rating = (current.get("rating", {}).get("key") or "").upper().replace("_", " ")
    if rating not in ["FAIR TO GOOD", "GOOD", "GOOD TO EPIC", "EPIC"]:
        return None

    wave_data = fetch(f"https://services.surfline.com/kbyg/spots/forecasts/wave?spotId={spot_id}&days=1")
    if not wave_data:
        return None
    wave_entry = wave_data["data"]["wave"][0]["surf"]
    wave_min = wave_entry.get("min", 0)
    wave_max = wave_entry.get("max", 0)

    name = spot.get("name", "Unknown")
    lat = spot.get("lat")
    lon = spot.get("lon")
    location = get_location(lat, lon) if lat and lon else {}
    time.sleep(0.3)

    region = REGION_MAP.get(location.get("code", ""), "Other")
    url = f"https://www.surfline.com/surf-report/{name.lower().replace(' ', '-')}/{spot_id}"

    return {
        "name": name,
        "city": location.get("city", ""),
        "country": location.get("country", ""),
        "region": region,
        "rating": rating,
        "wave_min": wave_min,
        "wave_max": wave_max,
        "url": url,
    }

def run_full_scan():
    with open("cam_spots.json") as f:
        cam_spots = json.load(f)

    results = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(check_spot, spot): spot for spot in cam_spots}
        for future in as_completed(futures):
            result = future.result()
            if result:
                results.append(result)

    condition_order = {"EPIC": 0, "GOOD TO EPIC": 1, "GOOD": 2, "FAIR TO GOOD": 3}
    results.sort(key=lambda x: condition_order.get(x["rating"], 99))

    with open(CACHE_FILE, "w") as f:
        json.dump({"timestamp": time.time(), "results": results}, f)

    return results

def load_cache():
    if not os.path.exists(CACHE_FILE):
        return None
    with open(CACHE_FILE) as f:
        data = json.load(f)
    age = time.time() - data.get("timestamp", 0)
    if age > CACHE_MAX_AGE:
        return None
    return data["results"]

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/search")
def search():
    min_height = int(request.args.get("min_height", 4))
    min_condition = request.args.get("condition", "FAIR TO GOOD")
    region_filter = request.args.get("region", "Worldwide")
    force_refresh = request.args.get("refresh", "false") == "true"

    cached = None

    if cached is None:
        all_results = run_full_scan()
    else:
        all_results = cached

    SHOW_CONDITIONS = ["FAIR TO GOOD", "GOOD", "GOOD TO EPIC", "EPIC"]
    start_idx = SHOW_CONDITIONS.index(min_condition) if min_condition in SHOW_CONDITIONS else 0
    SHOW_CONDITIONS = SHOW_CONDITIONS[start_idx:]

    filtered = [
        r for r in all_results
        if r["rating"] in SHOW_CONDITIONS
        and r["wave_max"] >= min_height
        and (region_filter == "Worldwide" or r["region"] == region_filter)
    ]

    return jsonify({"results": filtered, "from_cache": cached is not None})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)), debug=False)
