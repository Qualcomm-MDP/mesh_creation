# 3D Mesh Generation
Simulate the Blosm output from scratch without Blender's Python API by using native Python and its libraries.

Pipeline is found under the unix/ folder. Utilizes Python requests to the Overpass API to obtain data about buildings, roads, and other features
for a city in a given geographic region. Once we fetch the request, we are able to extrude out the regions according to the building heights fetched 
from Overpass. 

An example output of Lower Manhattan rendered out in Blender is shown below:

<img width="1440" height="900" alt="Screenshot 2026-01-21 at 2 26 11 PM" src="https://github.com/user-attachments/assets/36a05c0c-1299-4d90-ab3e-5d31891a9fac" />

## Splatoon

The splatoon feature is a raycasting mode where the goal is to paint the 3D mesh, by casting out a bunch of colored rays, and then placing the color at the intersection
between the mesh and the rays.

After cloning it, a simple way to run the script can just be:

python3 unix/splatoon.py

That will run splatoon script that is located in the folder titled "unix". That will use the pre-generated street mesh and coordinates. The script as of right now also outputs
the generated mesh as a GLB file, but due to the way that I am rendering it right now, it is rather large. I am still working on the point clouds as they are a much more
memory efficient way to place the colors, rather than generating out individual spheres wil color. However, this approach will work for now just to see what it is.

<img width="906" height="558" alt="Screenshot 2026-02-16 at 3 02 56 PM" src="https://github.com/user-attachments/assets/4ff3f34f-4308-49b9-94b2-7535a6161060" />



