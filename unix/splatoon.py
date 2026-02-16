import trimesh
import requests
import json
import numpy as np
from scipy.spatial.transform import Rotation as R
import cv2
import math
import numpy as np
import matplotlib.pyplot as plt

# A ray casting method that we could use to evaluate the quality of the mesh with images, like mapillary ones

# Define hyperparameters to be used to test an image on it
SCALE = 5
radius = 0.5  # adjust size for the balls
interval = 100 # How many pixels we wold like to skip in the original image
altitude = 1.83
JSON_path = "per_coordinate_osm_mapillary.json"

def splatoon_one(CAMERA_LOC, HEADING, INPUT_IMG, data_buildings, scene, street_mesh, checkpoint=False):

    # Use this when just testing local images
    splatter_img = cv2.imread(INPUT_IMG)

    # # Use this when reading the image from a url, like from Mapillary
    # res = requests.get(INPUT_IMG)
    # img_array = np.frombuffer(res.content, np.uint8)
    # splatter_img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    splatter_img = cv2.cvtColor(splatter_img, cv2.COLOR_BGR2RGB) # Convert to RGB format
    height, width, _ = splatter_img.shape
    print(height, width)

    # Set the bounds
    MAX_LAT = float(data_buildings[2])
    MIN_LAT = float(data_buildings[0])
    MAX_LON = float(data_buildings[3]) 
    MIN_LON = float(data_buildings[1])

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

    # Example ray
    ray_origin = np.array([[local_cam_lat, local_cam_lon, -1 * altitude]]) # Start of the ray, where the picture was taken (ignore the negative sign, all meshes were inverted so they were extruded to a negative height to account for that)
    ray_length = 100.0                     # how far to draw the ray (visualization purposes)

    FOCAL_LENGTH = 3165 # Focal length for apple camera, kinda estimated with chat and using the specs fond online: https://support.apple.com/en-us/111831
    HOR_FOV = math.atan((width / 2) / FOCAL_LENGTH) # Calculate the horizontal FOV
    VERT_FOV = math.atan((height / 2) / FOCAL_LENGTH) # Calculate the vertical FOV

    # Calculate the heading angles for the rays that we want to cast out
    MAX_HEADING = math.radians(HEADING) + HOR_FOV
    MIN_HEADING = math.radians(HEADING) - HOR_FOV

    # Calculate the tilt for the camera, since we want the rays to cover like everything, so we need to sweep and tilt
    MAX_TILT = VERT_FOV
    MIN_TILT = -1 * VERT_FOV

    # Places to store the rays, where they intersect, as well as their color
    rays = []
    locations_hit = []
    colors = []

    # How much we will be incrementing our rays by to sweep and cover the area with (heading and tilt)
    delta_heading = (HOR_FOV * 2) / int(width / interval)
    delta_tilt = (VERT_FOV * 2) / int(height / interval)
    height_center = int(height / 2) # Get the center of the image, will be useful later

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
        focal_length_adj = FOCAL_LENGTH / math.cos(heading) # Tells us how long our baseline segment is

        # Go through the tilts, only need to calculate half and then can just mirror ir
        for j in range(0, int(height / 2), interval):
            tilt = math.sin(tilt) # Get the tilt angle
            ray_direction_up = np.array([[x, y, tilt]]) # Create rays that tilt both positive and negative
            ray_direction_down = np.array([[x, y, -1 * tilt]])
            column_rays.append(ray_direction_up) # Store those rays' directions so that we can create them later
            column_rays.append(ray_direction_down)

            # If ray hits a part of the image that is in scope, get that color,
            if height_center + height_offset < height and i < width:
                column_colors.append(splatter_img[height_center + height_offset][i])
                column_colors.append(splatter_img[height_center - height_offset][i])
            else: # Otherwise just grab black, or some other null color
                column_colors.append([1, 1, 1])
                column_colors.append([1, 1, 1])
            
            # Update the magnitude tilt angle of the rays
            tilt += delta_tilt
            height_offset = abs(int((focal_length_adj * math.sin(tilt)) / (math.sin((math.pi / 2) - tilt)))) # Calculate the height offset for the next color we want to grab, relative to the center of the image (law of sine)
        # After shooting out all the tilts of the rays at a given heading, add those colors and those rays and store them
        colors.append(column_colors)
        rays.append(column_rays)
        heading += delta_heading # Update the heading
    
    # # Optional to visualize out
    # img = np.array(colors, dtype=np.uint8)

    # plt.imshow(img)
    # plt.axis('off')
    # plt.show()

    # Want a place to store the colors that actually are relevant, the ones that are touching the mesh
    hit_colors = [] # the ones that pass through the ground-truth image
    mesh_colors = [] # The mesh colors that we intersect

    # Go through the rays
    for i, column_ray in enumerate(rays):
        # Same deal as before, works best with a 2D data structure to keep track of the colors and the rays
        column_locations = []
        column_hit_colors = []
        mesh_hit_colors = []
        for j, ray in enumerate(column_ray):

            # # Optional ability to visualize out the rays that are being created, but takes up a lot of space and is expensive
            # # Compute endpoint
            # ray_end = ray_origin + (ray * ray_length)
            # # Create a line for the ray
            # ray_line = trimesh.load_path(np.vstack([ray_origin, ray_end]))
            # scene.add_geometry(ray_line)

            # Calculate the intersection with the mesh, only consider the first intersection
            locations, index_ray, index_tri = street_mesh.ray.intersects_location(
                ray_origins=ray_origin,
                ray_directions=ray,
                multiple_hits=False
            )

            # If there is an intersection, add that location as well as the color associated with that ray that intersected the mesh
            if len(locations) != 0:
                column_locations.append(locations)
                column_hit_colors.append(colors[i][j])

                # Get triangle indices
                tri_index = index_tri[0]  # example triangle
                vertex_colors = street_mesh.visual.vertex_colors
                triangle_vertex_indices = street_mesh.faces[tri_index]  # shape: (3,)
                tri_vertex_colors = vertex_colors[triangle_vertex_indices]
                avg_color = tri_vertex_colors.mean(axis=0)
                mesh_hit_colors.append(avg_color)

        # Store the locations and their colors
        locations_hit.append(column_locations)
        hit_colors.append(column_hit_colors)
        mesh_colors.append(mesh_hit_colors)

    # locations_flat = []
    # for column in locations_hit:
    #     for hit in column:
    #         locations_flat.append(hit)

    # colors_flat = []
    # for col in hit_colors:
    #     for color in col:
    #         colors_flat.append(color)

    # # Optional to use a point cloud instead of the spheres, but the point clouds can't have color, which is essential
    # locations_flat = np.array(locations_flat)
    # locations_flat = locations_flat.squeeze() # To get rid of the middle dimension cuz I dunno why, like (1841, 1, 3) → (1841, 3)
    # colors_flat = np.array(colors_flat)
    # print(locations_flat.shape)
    # print(colors_flat.shape)
    # point_cloud = trimesh.points.PointCloud(locations_flat, colors=colors_flat)
    # scene.add_geometry(point_cloud)

    # Create a list to store the cosine similarities (naive similar metric between two colors)
    cos_sims = []

    # Go thorugh the locations that were intersected
    for i, column in enumerate(locations_hit):
        for j, ray_sent_out in enumerate(column):
            for loc in ray_sent_out: # For each ray that we casted and hit the mesh

                # Alterante to point cloud, manually create a sphere with a certain color
                # Create a small UV sphere
                sphere = trimesh.creation.uv_sphere(radius=radius)
                # Convert the color into RGBA format for the colors from the image
                rgba = np.hstack([hit_colors[i][j], 255])
                # Optional , we can visualize out the colors that we intersected from the mesh
                # rgba = mesh_colors[i][j]
                # Assign the color to that sphere
                sphere.visual.vertex_colors[:] = np.tile(rgba, (len(sphere.vertices),1))
                # Place the sphere into the place that we want it
                sphere.apply_translation([loc[0], loc[1], loc[2]])
                # Add it to the scene
                scene.add_geometry(sphere)

                # Compute the cosine similarity (tf-idf style)
                img_vector = np.array(hit_colors[i][j]) 
                img_vector = img_vector / np.linalg.norm(img_vector) # Normalize the vectors

                mesh_vector = np.array(mesh_colors[i][j][:3])
                mesh_vector = mesh_vector / np.linalg.norm(mesh_vector) # Normalize the vectors

                cos_sim = np.dot(img_vector, mesh_vector)
                cos_sims.append(cos_sim)

    avg_cos_sim = sum(cos_sims) / len(cos_sims) # Calculate the average cosine similarity, extremely naive and primitive way to get similarity between mesh colors and image colors
    print(avg_cos_sim)

    # Create a small UV sphere
    sphere = trimesh.creation.uv_sphere(radius=radius)

    # Optional: assign color
    sphere.visual.vertex_colors[:] = [255, 0, 0, 255]  # Red RGBA

    # Add sphere to the scene. The red sphere marks the spot in which the image was taken from
    sphere.apply_translation([local_cam_lat, local_cam_lon, -1.83])
    scene.add_geometry(sphere)

    if checkpoint:
        # Optionally can export if we want to
        scene.export("scene.glb")
        print("Scene exported successfully to scene.glb!")

def splatoon(json):
    street_mesh = trimesh.load_mesh("combined.glb")

    # Create a trimesh scene
    scene = trimesh.Scene()
    scene.add_geometry(street_mesh) # Add in the pre-existing street mesh
    data_buildings = json["bbox_south_west_north_east"]

    # # A sample mapillary image
    # CAMERA_LOC = (42.291878, -83.715503)
    # HEADING = float(285)
    # INPUT_IMG = "https://scontent-det1-1.xx.fbcdn.net/m1/v/t6/An8zM1y78BKHD60-luu9x7zNXbdMjB18ne9OGtdX4ZTiDdb_CQFbxCrbEFbNVMPUB5SvsQzNHvci3rolq7dFeOGs6IIleHpVS8N6AIbtW_vEarGJ_3XMe6hGrUj-U8JtPu-ztfT1w7ObyyfjFKPkR-o?stp=s2048x1536&_nc_gid=f-QyVZm94rTqiPaRmrj1oA&_nc_oc=AdnxFneB5KzVHqB2HpBspvYg25-jvMYZeJKv3ZCHbuyf4kyT0SOl_EvdUZ7xl-BsjgI&ccb=10-6&oh=00_AftTKI1Sn8OIjbZfffQe2FX_FVl7lIv6DSm5ADK1PWMSlw&oe=69B99862&_nc_sid=201bca"

    # A sample mapillary image
    CAMERA_LOC = (42.29228, -83.71637)
    HEADING = 138
    INPUT_IMG = "wraps/IMG_6915.JPG"
    splatoon_one(CAMERA_LOC, HEADING, INPUT_IMG, data_buildings, scene, street_mesh, checkpoint=True)

    # mapillary = json["mapillary"]
    # for entry in mapillary:
    #     CAMERA_LOC = (float(entry["computed_geometry"]["coordinates"][1]), float(entry["computed_geometry"]["coordinates"][0]))
    #     HEADING = float(entry["computed_compass_angle"])
    #     INPUT_IMG = entry["thumb_original_url"]

    #     splatoon_one(CAMERA_LOC, HEADING, INPUT_IMG, data_buildings, scene, street_mesh, checkpoint=True)
        
    # Optionally can show if it we want to
    scene.show()

    # # Optionally can export if we want to
    # scene.export("scene.glb")
    # print("Scene exported successfuly!")

def main():

    st_data = {}
    with open(JSON_path, "r") as f:
        st_data = json.load(f)[0]

    splatoon(st_data)

if __name__ == "__main__":
    main()