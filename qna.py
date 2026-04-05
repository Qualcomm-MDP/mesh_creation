import trimesh
import numpy as np

mesh = trimesh.load("combined.glb")
scene = trimesh.Scene(mesh)

eye = np.array([691, 627, -1.83], dtype=float)      # camera location
target = np.array([700, 627, -1.83], dtype=float)    # point to look at
up = np.array([0, 0, -1], dtype=float)

forward = target - eye
forward /= np.linalg.norm(forward)

right = np.cross(forward, up)
right /= np.linalg.norm(right)

true_up = np.cross(right, forward)

transform = np.eye(4)
transform[:3,0] = right
transform[:3,1] = true_up
transform[:3,2] = -forward
transform[:3,3] = eye

scene.camera_transform = transform

png = scene.save_image(resolution=(800,600))

with open("render.png","wb") as f:
    f.write(png)