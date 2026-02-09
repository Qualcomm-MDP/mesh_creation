# 3D Mesh Generation
Simulate the Blosm output from scratch without Blender's Python API by using native Python and its libraries.

Pipeline is found under the unix/ folder. Utilizes Python requests to the Overpass API to obtain data about buildings, roads, and other features
for a city in a given geographic region. Once we fetch the request, we are able to extrude out the regions according to the building heights fetched 
from Overpass. 

An example output of Lower Manhattan rendered out in Blender is shown below:

<img width="1440" height="900" alt="Screenshot 2026-01-21 at 2 26 11 PM" src="https://github.com/user-attachments/assets/36a05c0c-1299-4d90-ab3e-5d31891a9fac" />
