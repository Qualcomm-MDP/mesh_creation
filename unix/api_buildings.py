import requests
import json

# These represent the region of interest, and we can change them here or control them elsewhere using like a website or smth like before
min_lat, min_lon = 42.29025, -83.71978
max_lat, max_lon = 42.29422, -83.71205

# this is good for one-off buildings / sampling. should not be used for the actual pipeline
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
# directly using the OSM API is not suitable for analysis, its more primitive

# Next things would be to change query to get the roads as well as buildings
# This is the overpass query format in order to get the data (ChatGPT this cuz i dunno the format)
query_buildings = f"""
[out:json][timeout:25];
way["building"]({min_lat},{min_lon},{max_lat},{max_lon});
out body geom;
"""

# Do a post request (Chat says that post request works better with larger queries)
r = requests.post(OVERPASS_URL, data=query_buildings)
r.raise_for_status()
data_buildings = r.json()
# Convert to json format

# Encode boundaries into the JSOn as well
data_buildings["max_lat"] = max_lat
data_buildings["min_lat"] = min_lat
data_buildings["max_lon"] = max_lon
data_buildings["min_lon"] = min_lon

# Write to the JSON output
with open("osm_data_buildings.json", "w") as f:
    json.dump(data_buildings, f, indent=2)
