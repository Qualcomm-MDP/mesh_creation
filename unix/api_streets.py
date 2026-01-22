import requests
import json

# These represent the region of interest, and we can change them here or control them elsewhere using like a website or smth like before
min_lat, min_lon = 40.77551, -73.98448
max_lat, max_lon = 40.77888, -73.97682

# this is good for one-off buildings / sampling. should not be used for the actual pipeline
OVERPASS_URL = "https://overpass-api.de/api/interpreter"
# directly using the OSM API is not suitable for analysis, its more primitive

# Next things would be to change query to get the roads as well as buildings
# This is the overpass query format in order to get the data (ChatGPT this cuz i dunno the format)

query_street = f"""
[out:json][timeout:25];
way["highway"]({min_lat},{min_lon},{max_lat},{max_lon});
out body geom;
"""

# Do a post request (Chat says that post request works better with larger queries)
r = requests.post(OVERPASS_URL, data=query_street)
r.raise_for_status()
data_street = r.json()
# Convert to json format

# Write to the JSON output
with open("osm_data_roads.json", "w") as f:
    json.dump(data_street, f, indent=2)