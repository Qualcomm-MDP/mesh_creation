import trimesh
import requests
import json
import numpy as np
from scipy.spatial.transform import Rotation as R
import cv2
import math
import numpy as np
import matplotlib.pyplot as plt
from geopy.distance import geodesic
import pyembree
from trimesh.ray.ray_pyembree import RayMeshIntersector

# A ray casting method that we could use to evaluate the quality of the mesh with images, like mapillary ones

# Define hyperparameters to be used to test an image on it
SCALE = 5
radius = 0.5  # adjust size for the balls
interval = 5 # How many pixels we wold like to skip in the original image
altitude = -2
JSON_path = "m_out.json"

MIN_LAT = 42.28705
MIN_LON = -83.71969999999999
MAX_LAT = 42.297050000000006
MAX_LON = -83.7097

def splatoon_one(CAMERA_LOC, HEADING, INPUT_IMG, scene, data_buildings, street_mesh, focal_length, scaling_factor, checkpoint=False):

    # # Use this when just testing local images
    # splatter_img = cv2.imread(INPUT_IMG)

    # VERY IMPORTANT, convert to radians as that is used for everything later on
    HEADING = math.radians(HEADING)

    # Use this when reading the image from a url, like from Mapillary
    res = requests.get(INPUT_IMG)
    img_array = np.frombuffer(res.content, np.uint8)
    splatter_img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)

    # # Optional show the original mapillary image
    # cv2.imshow("Image", splatter_img)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()

    splatter_img = cv2.cvtColor(splatter_img, cv2.COLOR_BGR2RGB) # Convert to RGB format
    height, width, _ = splatter_img.shape
    print(height, width)

    MAX_LAT = data_buildings["max_lat"]
    MAX_LON = data_buildings["max_lon"]
    MIN_LAT = data_buildings["min_lat"]
    MIN_LON = data_buildings["min_lon"]

    print(MAX_LAT, MAX_LON, MIN_LAT, MIN_LON)

    # Calculate the converted coordinates to place the camera at
    converted_max_lat = int(MAX_LAT * 10**SCALE)
    converted_max_lon = int(MAX_LON * 10**SCALE)
    converted_min_lon = int(MIN_LON * 10**SCALE)
    converted_min_lat = int(MIN_LAT * 10**SCALE)

    # Converted the coordinates for the camera
    converted_cam_lat = int(CAMERA_LOC[0] * 10**SCALE)
    converted_cam_lon = int(CAMERA_LOC[1] * 10**SCALE)

    # Get the local coordinates by offsetting it with the bounding boxes
    local_cam_lat = converted_cam_lat - converted_min_lat
    local_cam_lon = converted_cam_lon - converted_min_lon

    print(local_cam_lat, local_cam_lon)

    inside = street_mesh.contains([[local_cam_lat, local_cam_lon, altitude]])
    if(inside[0]):
        print("Returning Early -- Point inside of mesh")
        return

    # Create a small UV sphere
    sphere = trimesh.creation.uv_sphere(radius=radius)

    # Optional: assign color
    sphere.visual.vertex_colors[:] = [255, 0, 0, 255]  # Red RGBA

    # Add sphere to the scene. The red sphere marks the spot in which the image was taken from
    sphere.apply_translation([local_cam_lat, local_cam_lon, altitude])
    scene.add_geometry(sphere)
        
    # Example ray
    ray_origin = np.array([[local_cam_lat, local_cam_lon, altitude]]) # Start of the ray, where the picture was taken (ignore the negative sign, all meshes were inverted so they were extruded to a negative height to account for that)
    
    # Add a little camera anchor to see where the camera is point to
    camera_ray = np.array([[math.cos(HEADING), math.sin(HEADING), 0]])
    ray_length = 5 
    # Optional ability to visualize out the rays that are being created, but takes up a lot of space and is expensive
    # Compute endpoint
    ray_end = ray_origin + (camera_ray * ray_length)
    # Create a line for the ray
    ray_line = trimesh.load_path(np.vstack([ray_origin, ray_end]))
    scene.add_geometry(ray_line)
    
    ray_length = 100.0                     # how far to draw the ray (visualization purposes)

    FOCAL_LENGTH = focal_length * width # Focal length for apple camera, kinda estimated with chat and using the specs fond online: https://support.apple.com/en-us/111831
    FOCAL_LENGTH_UP = focal_length * width
    HOR_FOV = math.atan((width / 2) / FOCAL_LENGTH) # Calculate the horizontal FOV
    VERT_FOV = math.atan((height / 2) / FOCAL_LENGTH_UP) # Calculate the vertical FOV

    print(HOR_FOV)
    print(VERT_FOV)

    # Calculate the heading angles for the rays that we want to cast out
    MAX_HEADING = HEADING + HOR_FOV
    MIN_HEADING = HEADING - HOR_FOV

    # Calculate the tilt for the camera, since we want the rays to cover like everything, so we need to sweep and tilt
    MAX_TILT = VERT_FOV
    MIN_TILT = -1 * VERT_FOV

    # Places to store the rays, where they intersect, as well as their color
    rays = []
    locations_hit = []
    hit_colors = []
    colors = []
    raw_rays = []
    raw_colors = []

    # How much we will be incrementing our rays by to sweep and cover the area with (heading and tilt)
    height_center = int(height / 2) # Get the center of the image, will be useful later
    delta_heading = (HOR_FOV * 2) / int(width / interval)
    delta_tilt = (VERT_FOV) / int(height_center / interval)
    print(height_center)

    heading = MIN_HEADING # Set the current starting position to be the min heading, leftmost so that we sweep from left to right
    for i in range(0, width, interval):
        # Calculate the unit vector direction of the ray
        x = math.cos(heading)
        y = math.sin(heading)
        tilt = 0 # Get the tilt

        # Define some data structures since we need to store the colors in 2D ( or at least that is what I found to work as collapsing it lost valuable spatial info )
        column_colors = []
        column_rays = []

        # Crucial, angles change the difference in height for the color pixels, rays shot out with a smaller tilt angle will be closer together basically, so we need to select the colors appropriately
        height_offset = 0 # Want to calculate the height offset for the pixels as we go down x number of degrees as it varies
        focal_length_adj = abs(FOCAL_LENGTH / math.cos(abs(HEADING - heading))) # Tells us how long our baseline segment is

        # Go through the tilts, only need to calculate half and then can just mirror it
        counter = 0

        while(height_offset <= int(height_center)):
        # while(tilt <= MAX_TILT):
            counter += 1
            tilt_sin = math.sin(tilt) # Get the tilt angle
            ray_direction_up = np.array([[math.cos(tilt) * x, math.cos(tilt) * y, tilt_sin]]) # Create rays that tilt both positive and negative
            ray_direction_down = np.array([[math.cos(tilt) * x, math.cos(tilt) * y, -1 * tilt_sin]])
            column_rays.append(ray_direction_up) # Store those rays' directions so that we can create them later
            column_rays.append(ray_direction_down)
            raw_rays.append(ray_direction_up)
            raw_rays.append(ray_direction_down)
            # If ray hits a part of the image that is in scope, get that color,
            if height_center + height_offset < height and i < width:
                column_colors.append(splatter_img[height_center + height_offset][i])
                raw_colors.append(splatter_img[height_center + height_offset][i])
                column_colors.append(splatter_img[height_center - height_offset][i])
                raw_colors.append(splatter_img[height_center - height_offset][i])
            else: # Otherwise just grab black, or some other null color
                column_colors.append([1, 1, 1])
                raw_colors.append([1, 1, 1])
                column_colors.append([1, 1, 1])
                raw_colors.append([1, 1, 1])
            
            # Update the magnitude tilt angle of the rays
            tilt += delta_tilt
            height_offset = abs(int((focal_length_adj * math.sin(tilt)) / (math.sin((math.pi / 2) - tilt)))) # Calculate the height offset for the next color we want to grab, relative to the center of the image (law of sine)
        
        # After shooting out all the tilts of the rays at a given heading, add those colors and those rays and store them
        colors.append(column_colors)
        rays.append(column_rays)
        heading += delta_heading # Update the heading

    ray_origins = np.repeat(ray_origin, len(raw_rays), axis=0)
    raw_rays = np.array(raw_rays).reshape(-1, 3)
    raw_colors = np.array(raw_colors).reshape(-1, 3)
    print(ray_origins.shape)
    print(raw_rays.shape)
    print(raw_colors.shape)

    ray_intersector = street_mesh.ray
    print(type(street_mesh.ray))

    print("F")
    locations, index_ray, index_tri = ray_intersector.intersects_location(
        ray_origins=ray_origins,
        ray_directions=raw_rays,
        multiple_hits=False
    )

    # Vectorized: compute distances in XY plane if that's what you want
    hit_points_proj = locations[:, :2]  # (M, 2)
    ray_origins_proj = ray_origins[index_ray, :2]  # (M, 2)
    distances = np.linalg.norm(hit_points_proj - ray_origins_proj, axis=1)
    
    distance_mask = (distances * scaling_factor > 3) & (distances * scaling_factor <= 50)

    if distance_mask.shape[0] == 0:
        print("No valid points to splatoon here")
        return
    
    filtered_faces = index_tri[distance_mask]
    filtered_rays  = index_ray[distance_mask]

    print(filtered_faces.shape)
    print(filtered_rays.shape)

    default_color = np.array([102, 102, 102, 255])

    # print("Sample face colors:", street_mesh.visual.face_colors[filtered_faces[:10]])

    mask = np.all(
        street_mesh.visual.face_colors[filtered_faces] == default_color,
        axis=1
    )
    print(mask.shape)

    valid_triangles = filtered_faces[mask]
    valid_colors = raw_colors[filtered_rays[mask]]
    valid_colors = np.hstack([valid_colors, np.full((len(valid_colors), 1), 255)]).astype(np.uint8)
    print("G")
    print(valid_colors.shape)

    street_mesh.visual.face_colors[valid_triangles] = valid_colors

    if checkpoint:
        # Optionally can export if we want to
        scene.export("scene.glb")
        print("Scene exported successfully to scene.glb!")

def splatoon(json, street_mesh):

    print(pyembree.__version__)
    print(trimesh.__version__)
    print(pyembree.__file__)

    street_mesh.visual = trimesh.visual.ColorVisuals(
        mesh=street_mesh,
        face_colors=np.ones((len(street_mesh.faces), 4), dtype=np.uint8) * 255
    )

    street_mesh = street_mesh.subdivide()
    street_mesh = street_mesh.subdivide()
    street_mesh = street_mesh.subdivide()
    street_mesh = street_mesh.subdivide()
    street_mesh = street_mesh.subdivide()
    street_mesh = street_mesh.subdivide()

    scene = trimesh.Scene()
    scene.add_geometry(street_mesh) # Add in the pre-existing street mesh

    data_buildings = json[0]

    MAX_LAT = data_buildings["max_lat"]
    MAX_LON = data_buildings["max_lon"]
    MIN_LAT = data_buildings["min_lat"]
    MIN_LON = data_buildings["min_lon"]

    p1 = (MAX_LAT, MAX_LON)
    p2 = (MAX_LAT, MIN_LON)
    dist = geodesic(p1, p2).meters
    print(dist, "meters")

    print(MAX_LAT, MAX_LON, MIN_LAT, MIN_LON)

    idx = int(MIN_LON * (10**SCALE))
    idx2 = int(MAX_LON * (10**SCALE))

    delta_u = idx2 - idx
    scaling_factor = delta_u / dist

    # # A sample mapillary image
    # CAMERA_LOC = (42.290091985493, -83.716450325749)
    # HEADING = float(130.16030349534)
    # INPUT_IMG = "https://scontent-det1-1.xx.fbcdn.net/m1/v/t6/An90UZlI8X-oPToKa2V1rvp1mZIodV3D-HaOvrqy_Um-CV6bWcrKgy9eQIvogP9w15sX0-zm0NSaH8d2p2H3pHPF5Dyz9KL63sCFGHraX5YdwMkUSv5s7rD_4aXNOyZlA3i7tVHhXy7eknAJHtC9YeA?edm=AOnQwmMEAAAA&_nc_gid=dXlWzuoGyAxaIEOzceppRw&_nc_oc=Adlhg0uT44MjgOQOuvJJpEdrnA4i2KBk5r5dKJHk72LS0OK-GOW4MkzX9boVO-ZqrAW7AHkM-xKFqYW3iSRGnbWt&ccb=10-5&oh=00_AfzWVLYP3in2i1hScZ6dlz_4n_q7LK5Yyu2zcsj6dZyb-g&oe=69E02B0A&_nc_sid=201bca"
    # focal = 0.66086917380243

    # splatoon_one(CAMERA_LOC, HEADING, INPUT_IMG, data_buildings, scene, street_mesh, focal, checkpoint=True)

    # # A sample image taken from my iphone
    # CAMERA_LOC = (42.292531, -83.715441)
    # HEADING = 92
    # INPUT_IMG = "wraps/IMG_6922.JPG"

    # splatoon_one(CAMERA_LOC, HEADING, INPUT_IMG, data_buildings, scene, street_mesh, checkpoint=True)

    # # Another sample mapillary image
    # CAMERA_LOC = (42.293359445169, -83.716257972562)
    # HEADING = float(182.13519237469)
    # INPUT_IMG = "https://scontent-det1-1.xx.fbcdn.net/m1/v/t6/An_vZPjId8PEFm5PxKvwnY7tDJHvcBgbi1XNwAhCRsO9PffhAhGaN6K-XU93s7zAyucZg4rShL8Emffi6Xv8Utp40u0ZQvgALrFdIYKXaDffgNrVna-DuhICIgbgULEm3ja8XO_0anetJ8xth7ws_nw?edm=AOnQwmMEAAAA&_nc_gid=dkiAhLQofvKHOw1M9UwH4w&_nc_oc=AdmWplF-T35JzUtyoSKeUw0JvHyFF5jXYcGmyaAQ8xmcTOTibdesIZMG-wifPFRqKP9kqrjGIuHwlOuup03GiKOV&ccb=10-5&oh=00_AfxElfOugTaLmfEI2h5i7h7hPNgb96b9ZrYbjbd6K6h7Dw&oe=69E06601&_nc_sid=201bca"
    # focal = 0.6821941218614

    # splatoon_one(CAMERA_LOC, HEADING, INPUT_IMG, data_buildings, scene, street_mesh, focal, scaling_factor, checkpoint=True)

    counter = 0
    mapillary = json[1]["mapillary"]["data"]
    for entry in mapillary:
        counter += 1
        if counter % 3 != 0:
            continue
        print(counter)
        # if counter >= 200:
        #     break
        CAMERA_LOC = (float(entry["computed_geometry"]["coordinates"][1]), float(entry["computed_geometry"]["coordinates"][0]))
        HEADING = float(entry["computed_compass_angle"])
        INPUT_IMG = entry["thumb_original_url"]
        focal = entry["camera_parameters"][0]

        splatoon_one(CAMERA_LOC, HEADING, INPUT_IMG, scene, data_buildings, street_mesh, focal, scaling_factor, checkpoint=True)

    return scene

def main():

    st_data = {}
    with open(JSON_path, "r") as f:
        st_data = json.load(f)
    
    street_mesh = trimesh.load_mesh("combined.glb")

    # Create a trimesh scene
    scene = trimesh.Scene()

    scene = splatoon(st_data, street_mesh)

    scene.export("scene.glb")
    print("Scene exported successfuly to scene.glb!")

if __name__ == "__main__":
    main()