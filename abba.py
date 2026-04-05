# get buildings and nearby mapillary images
import json
import time
import requests

# Download from URL:
"""
curl "[url]" -o ./tmp/sfm_cluster
"""

# Decode sfm cluster:
""" python3 -c '
import sys, zlib, json

data = zlib.decompress(sys.stdin.buffer.read())
obj = json.loads(data.decode("utf-8"))

print(json.dumps(obj, indent=2))
' < ./temp/sfm_cluster > output.json
"""

MAPILLARY_URL = "https://graph.mapillary.com/images"


COORDS = [
    # (42.278594, -83.740779) # University St
    #(42.2754250, -83.7432138), # central
    (42.292091, -83.716011), # north
    # (42.274933, -83.743182), # munger
    
]



min_lon = -83.71996
max_lon = -83.71167
min_lat = 42.29006
max_lat = 42.29454

OUT_FILE = "m_out.json"   # set to None to print instead of save

MAPILLARY_ACCESS_TOKEN = "MLY|25949894238000038|6ce5d01e1362c9315805c6b85aea7eec" 

# ============================================================


def fetch_mapillary(token):

    url = f"https://graph.mapillary.com/images/"  # endpoint for single image
    bbox_str = f"{min_lon},{min_lat},{max_lon},{max_lat}"
    params = {
        "fields": "id,thumb_original_url,camera_type,computed_geometry,computed_compass_angle,captured_at,camera_parameters",
        "access_token": token,
        "camera_type": "equirectangular",
        "bbox": bbox_str
    }

    r = requests.get(url, params=params, timeout=60)
    r.raise_for_status()
    return r.json()


def main():
    results = []

    bound_rec = {
        "min_lat": min_lat,
        "min_lon": min_lon,
        "max_lat": max_lat,
        "max_lon": max_lon
    }

    results.append(bound_rec)

    record = {
        "mapillary": fetch_mapillary(MAPILLARY_ACCESS_TOKEN),
    }

    results.append(record)

    output_json = json.dumps(results, indent=2)

    if OUT_FILE:
        with open(OUT_FILE, "w") as f:
            f.write(output_json)
        print(f"Saved {OUT_FILE}")
    else:
        print(output_json)


if __name__ == "__main__":
    main()