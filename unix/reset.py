import os
import shutil

OUT_DIR = "output_meshes"
if os.path.exists(OUT_DIR):
    shutil.rmtree(OUT_DIR)
    os.mkdir(OUT_DIR)
    print(f"Directory '{OUT_DIR}' exist and cleard its contents!")
else:
    os.mkdir(OUT_DIR)
    print(f"Directory '{OUT_DIR}' did not exist and we created it now.")
os.makedirs(OUT_DIR, exist_ok=True)