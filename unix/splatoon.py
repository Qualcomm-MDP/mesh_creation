import trimesh
import json
import numpy as np
from scipy.spatial.transform import Rotation as R
import cv2
import math
import numpy as np
import matplotlib.pyplot as plt

SCALE = 5
CAMERA_LOC = (42.29228, -83.71637)
HEADING = 135
INPUT_JSON = "osm_data_buildings.json" 
INPUT_IMG = "wraps/IMG_6915.JPG"
radius = 0.5  # adjust size
interval = 100

splatter_img = cv2.imread(INPUT_IMG)
splatter_img = cv2.cvtColor(splatter_img, cv2.COLOR_BGR2RGB)
height, width, _ = splatter_img.shape
print(height, width)

# Read in the json data
with open(INPUT_JSON, "r") as f:
    data_buildings = json.load(f)

MAX_LAT = float(data_buildings["max_lat"])
MIN_LAT = float(data_buildings["min_lat"])
MAX_LON = float(data_buildings["max_lon"]) 
MIN_LON = float(data_buildings["min_lon"])

converted_max_lat = int(MAX_LAT * 10**SCALE)
converted_max_lon = int(MAX_LON * 10**SCALE)
converted_min_lon = int(MIN_LON * 10**SCALE)
converted_min_lat = int(MIN_LAT * 10**SCALE)

converted_cam_lat = int(CAMERA_LOC[0] * 10**SCALE)
converted_cam_lon = int(CAMERA_LOC[1] * 10**SCALE)

local_cam_lat = converted_cam_lat - converted_min_lat
local_cam_lon = converted_cam_lon - converted_min_lon

street_mesh = trimesh.load_mesh("combined.glb")

scene = trimesh.Scene()
scene.add_geometry(street_mesh)

# Example ray
ray_origin = np.array([[local_cam_lat, local_cam_lon, -1.83]])
ray_length = 100.0                     # how far to draw the ray

FOCAL_LENGTH = 3165
HOR_FOV = math.atan((width / 2) / FOCAL_LENGTH)
VERT_FOV = math.atan((height / 2) / FOCAL_LENGTH)

MAX_HEADING = math.radians(HEADING) + HOR_FOV
MIN_HEADING = math.radians(HEADING) - HOR_FOV

MAX_TILT = VERT_FOV
MIN_TILT = -1 * VERT_FOV

rays = []
locations_hit = []
colors = []

delta_heading = (HOR_FOV * 2) / int(width / interval)
delta_tilt = (VERT_FOV * 2) / int(height / interval)
height_center = int(height / 2)
print(height_center)

heading = MIN_HEADING
for i in range(0, width, interval):
    x = math.cos(heading)
    y = math.sin(heading)
    tilt = 0
    column_colors = []
    column_rays = []
    height_offset = 0 # Want to calculate the height offset for the pixels as we go down x number of degrees as it varies
    focal_length_adj = FOCAL_LENGTH / math.cos(heading) # Tells us how long our baseline segment is
    for j in range(0, int(height / 2), interval):
        tilt = math.sin(tilt)
        ray_direction_up = np.array([[x, y, tilt]])
        ray_direction_down = np.array([[x, y, -1 * tilt]])
        column_rays.append(ray_direction_up)
        column_rays.append(ray_direction_down)
        if height_center + height_offset < height and i < width:
            column_colors.append(splatter_img[height_center + height_offset][i])
            column_colors.append(splatter_img[height_center - height_offset][i])
        else:
            column_colors.append([0, 0, 0])
            column_colors.append([0, 0, 0])
        tilt += delta_tilt
        height_offset = abs(int((focal_length_adj * math.sin(tilt)) / (math.sin((math.pi / 2) - tilt))))
    colors.append(column_colors)
    rays.append(column_rays)
    heading += delta_heading

hit_colors = []
for i, column_ray in enumerate(rays):
    column_locations = []
    column_hit_colors = []
    for j, ray in enumerate(column_ray):
        # Compute endpoint
        ray_end = ray_origin + (ray * ray_length)

        # Create a line for the ray
        ray_line = trimesh.load_path(np.vstack([ray_origin, ray_end]))

        # Scene
        # scene.add_geometry(ray_line)

        locations, index_ray, index_tri = street_mesh.ray.intersects_location(
            ray_origins=ray_origin,
            ray_directions=ray,
            multiple_hits=False
        )
        if len(locations) != 0:
            column_locations.append(locations)
            column_hit_colors.append(colors[i][j])
    locations_hit.append(column_locations)
    hit_colors.append(column_hit_colors)

# locations_hit = np.array(locations_hit)
# colors = np.array([[255, 0, 0]]) * len(locations_hit)
# point_cloud = trimesh.points.PointCloud(locations_hit, colors=colors)
# scene.add_geometry(point_cloud)

for i, column in enumerate(locations_hit):
    for j, ray_sent_out in enumerate(column):
        for loc in ray_sent_out:
            # Create a small UV sphere
            sphere = trimesh.creation.uv_sphere(radius=radius)

            rgba = np.hstack([hit_colors[i][j], 255])
            # Optional: assign color
            sphere.visual.vertex_colors[:] = np.tile(rgba, (len(sphere.vertices),1))

            sphere.apply_translation([loc[0], loc[1], loc[2]])
            scene.add_geometry(sphere)

# Create a small UV sphere
sphere = trimesh.creation.uv_sphere(radius=radius)

# Optional: assign color
sphere.visual.vertex_colors[:] = [255, 0, 0, 255]  # Red RGBA

sphere.apply_translation([local_cam_lat, local_cam_lon, -1.83])
scene.add_geometry(sphere)

scene.show()
# scene.export("scene.glb")
# print("Scene exported successfuly!")