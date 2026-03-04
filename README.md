# 3D Mesh Generation
Simulate the Blosm output from scratch without Blender's Python API by using native Python and its libraries.

Pipeline is found under the unix/ folder. Utilizes Python requests to the Overpass API to obtain data about buildings, roads, and other features
for a city in a given geographic region. Once we fetch the request, we are able to extrude out the regions according to the building heights fetched 
from Overpass. 

An example output of Lower Manhattan rendered out in Blender is shown below:

<img width="1440" height="900" alt="Screenshot 2026-01-21 at 2 26 11 PM" src="https://github.com/user-attachments/assets/36a05c0c-1299-4d90-ab3e-5d31891a9fac" />

To run the script, remember to download all of the libraries required in the requirements.txt. An example usage to run the mesh generation would be:

```bash
./bin/createmesh 42.29025 -83.71978 42.29422 -83.71205
```

The output of running the above command is shown below:

<img width="1319" height="546" alt="Screenshot 2026-03-03 at 8 08 53 PM" src="https://github.com/user-attachments/assets/66a18647-5b7a-44a5-a621-fade2f57e7ac" />

The last 4 commands represent the minimum latitude, mininmum longitude, maximum latitude, maximum longitude to specify a bounding box to generate out the extruded regions. The output
of the script will be a .glb file saved into combined.glb. Additionally, each building's .glb file will be stored in the output_meshes directory with each building mesh labeled with
its OSM building way ID. To clear the directories, run 

```bash
python3 reset.py
```

And this will clear out the output_meshes directory.


