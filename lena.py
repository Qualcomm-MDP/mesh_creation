"""
Downloads satellite imagery from USGS NAIP (National Agriculture Imagery Program)
for a rectangular area defined by four lat/lon corner points.

Usage:
    python usgs_satellite_download.py

You will be prompted to enter:
    - Four corner coordinates (lat, lon) defining the bounding box
    - Desired image width/height in pixels
    - Output filename

Or use it as a library:
    from usgs_satellite_download import download_satellite_image
    download_satellite_image(
        min_lat=42.27, min_lon=-83.75,
        max_lat=42.29, max_lon=-83.73,
        width=2048, height=2048,
        output_path="my_area.png"
    )
"""

import requests
import sys
import os
from pathlib import Path


# USGS NAIP ImageServer endpoint
USGS_NAIP_URL = (
    "https://imagery.nationalmap.gov/arcgis/rest/services/"
    "USGSNAIPPlus/ImageServer/exportImage"
)


def latlon_to_web_mercator(lat: float, lon: float) -> tuple[float, float]:
    """Convert latitude/longitude (EPSG:4326) to Web Mercator (EPSG:3857)."""
    import math
    # The number 20037508.34 is half the Earth's circumference in meters. 
    # That's the key constant that scales degrees into meters.
    x = lon * 20037508.34 / 180.0
    y = math.log(math.tan((90.0 + lat) * math.pi / 360.0)) / (math.pi / 180.0)
    y = y * 20037508.34 / 180.0
    return x, y


def download_satellite_image(
    min_lat: float,
    min_lon: float,
    max_lat: float,
    max_lon: float,
    width: int | None = None,
    height: int | None = None,
    output_path: str = "satellite_image.png",
    image_format: str = "png",
    dpi: int = 96,
) -> str:
    """
    Download a satellite image from USGS NAIP for the given bounding box.

    Parameters
    ----------
    min_lat : float        -- Southern boundary latitude
    min_lon : float        -- Western boundary longitude
    max_lat : float        -- Northern boundary latitude
    max_lon : float        -- Eastern boundary longitude
    width   : int or None  -- Output image width in pixels (None = native resolution)
    height  : int or None  -- Output image height in pixels (None = native resolution)
    output_path : str      -- File path for the saved image
    image_format: str      -- "png", "jpg", or "tiff"
    dpi     : int          -- Dots per inch

    Returns
    -------
    str : Path to the saved image file.

    Notes
    -----
    NAIP imagery is typically 0.6 m/pixel. When width and height are None,
    the script calculates the native pixel dimensions from the bounding box
    ground distance. The ArcGIS API caps a single request at ~4096 pixels
    per side; if the native size exceeds that, the script will tile multiple
    requests and stitch them together automatically.

    The ArcGIS REST endpoint itself is a free public service run by USGS. 
    There's no authentication or rate limiting beyond reasonable use.

    """

    # Validate inputs
    if min_lat >= max_lat:
        raise ValueError(f"min_lat ({min_lat}) must be less than max_lat ({max_lat})")
    if min_lon >= max_lon:
        raise ValueError(f"min_lon ({min_lon}) must be less than max_lon ({max_lon})")
    if not (-90 <= min_lat <= 90 and -90 <= max_lat <= 90):
        raise ValueError("Latitude must be between -90 and 90")
    if not (-180 <= min_lon <= 180 and -180 <= max_lon <= 180):
        raise ValueError("Longitude must be between -180 and 180")

    # Convert bounding box to Web Mercator (EPSG:3857) -- required by the API
    x_min, y_min = latlon_to_web_mercator(min_lat, min_lon)
    x_max, y_max = latlon_to_web_mercator(max_lat, max_lon)

    # NAIP native resolution: 0.6 meters per pixel
    NAIP_RESOLUTION = 0.6

    if width is None or height is None:
        ground_width  = x_max - x_min   # meters
        ground_height = y_max - y_min   # meters
        width  = int(round(ground_width  / NAIP_RESOLUTION))
        height = int(round(ground_height / NAIP_RESOLUTION))
        print(f"Native resolution: {width} x {height} px "
              f"({ground_width:.0f} x {ground_height:.0f} m at {NAIP_RESOLUTION} m/px)")

    # ArcGIS caps at ~4096 per side per request; tile if needed
    MAX_TILE = 4096

    if width <= MAX_TILE and height <= MAX_TILE:
        return _download_single(
            x_min, y_min, x_max, y_max,
            width, height,
            min_lat, min_lon, max_lat, max_lon,
            image_format, dpi, output_path,
        )
    else:
        return _download_tiled(
            x_min, y_min, x_max, y_max,
            width, height,
            min_lat, min_lon, max_lat, max_lon,
            image_format, dpi, output_path,
        )


def _get_api_format(image_format: str) -> str:
    format_map = {
        "png": "png", "jpg": "jpg", "jpeg": "jpg",
        "tiff": "tiff", "tif": "tiff",
    }
    return format_map.get(image_format.lower(), "png")


def _fetch_tile(x_min, y_min, x_max, y_max, w, h, api_format, dpi) -> bytes:
    """Fetch a single tile from the API and return raw image bytes."""
    params = {
        "bbox": f"{x_min},{y_min},{x_max},{y_max}",
        "bboxSR": 3857,
        "imageSR": 3857,
        "size": f"{w},{h}",
        "format": api_format,
        "f": "image",
        "dpi": dpi,
        "adjustAspectRatio": "true",
    }
    response = requests.get(USGS_NAIP_URL, params=params, timeout=120)
    if response.status_code != 200:
        raise RuntimeError(
            f"Server returned HTTP {response.status_code}: {response.text[:500]}"
        )
    content_type = response.headers.get("Content-Type", "")
    if "json" in content_type or "text" in content_type:
        raise RuntimeError(f"API error: {response.text[:500]}")
    return response.content


def _download_single(
    x_min, y_min, x_max, y_max,
    width, height,
    min_lat, min_lon, max_lat, max_lon,
    image_format, dpi, output_path,
) -> str:
    """Download the image in a single API request."""
    api_format = _get_api_format(image_format)

    print(f"Requesting image from USGS NAIP...")
    print(f"   Bounding box (lat/lon): [{min_lat}, {min_lon}] to [{max_lat}, {max_lon}]")
    print(f"   Image size: {width} x {height} px")
    print(f"   Format: {api_format}")

    data = _fetch_tile(x_min, y_min, x_max, y_max, width, height, api_format, dpi)

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(data)

    size_kb = len(data) / 1024
    print(f"Saved {size_kb:.1f} KB -> {output.resolve()}")
    return str(output.resolve())


def _download_tiled(
    x_min, y_min, x_max, y_max,
    width, height,
    min_lat, min_lon, max_lat, max_lon,
    image_format, dpi, output_path,
) -> str:
    """Download the image by tiling multiple API requests and stitching."""
    try:
        from PIL import Image
    except ImportError:
        raise RuntimeError(
            "Pillow is required for native-resolution downloads larger than 4096 px.\n"
            "Install it with:  pip install Pillow"
        )
    import io
    import math

    api_format = _get_api_format(image_format)
    MAX_TILE = 4096

    cols = math.ceil(width  / MAX_TILE)
    rows = math.ceil(height / MAX_TILE)

    print(f"Requesting image from USGS NAIP...")
    print(f"   Bounding box (lat/lon): [{min_lat}, {min_lon}] to [{max_lat}, {max_lon}]")
    print(f"   Full image size: {width} x {height} px")
    print(f"   Tiling: {cols} columns x {rows} rows = {cols * rows} tiles")
    print(f"   Format: {api_format}")

    full_image = Image.new("RGB", (width, height))

    tile_x_extent = (x_max - x_min) / cols
    tile_y_extent = (y_max - y_min) / rows
    tile_w = math.ceil(width  / cols)
    tile_h = math.ceil(height / rows)

    count = 0
    total = cols * rows
    for row in range(rows):
        for col in range(cols):
            count += 1
            tx_min = x_min + col * tile_x_extent
            tx_max = x_min + (col + 1) * tile_x_extent
            # y-axis: top row = highest y value
            ty_max = y_max - row * tile_y_extent
            ty_min = y_max - (row + 1) * tile_y_extent

            # last tile may be smaller
            tw = min(tile_w, width  - col * tile_w)
            th = min(tile_h, height - row * tile_h)

            print(f"   Downloading tile {count}/{total} "
                  f"({tw}x{th} px) ...", end=" ", flush=True)

            data = _fetch_tile(tx_min, ty_min, tx_max, ty_max, tw, th, api_format, dpi)
            tile_img = Image.open(io.BytesIO(data))
            full_image.paste(tile_img, (col * tile_w, row * tile_h))
            print("OK")

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    full_image.save(str(output))

    size_kb = output.stat().st_size / 1024
    print(f"Saved {size_kb:.1f} KB -> {output.resolve()}")
    return str(output.resolve())


# Interactive CLI
def _prompt_float(label: str, default: float | None = None) -> float:
    suffix = f" [{default}]" if default is not None else ""
    while True:
        raw = input(f"  {label}{suffix}: ").strip()
        if not raw and default is not None:
            return default
        try:
            return float(raw)
        except ValueError:
            print("    Please enter a valid number.")


def _prompt_int(label: str, default: int) -> int:
    while True:
        raw = input(f"  {label} [{default}]: ").strip()
        if not raw:
            return default
        try:
            return int(raw)
        except ValueError:
            print("    Please enter a valid integer.")


def main():
    print("=" * 60)
    print("  USGS NAIP Satellite Image Downloader")
    print("=" * 60)
    print()
    print("Enter the bounding box coordinates (decimal degrees):")
    print("  Coverage: Continental US only (NAIP imagery)\n")

    min_lat = _prompt_float("South latitude  (min_lat)", default=42.33241)
    max_lat = _prompt_float("North latitude  (max_lat)", default=42.33441)
    min_lon = _prompt_float("West longitude  (min_lon)", default=-83.049295)
    max_lon = _prompt_float("East longitude  (max_lon)", default=-83.04729499999999)

    print()
    customize = input("  Customize image settings? (y/n) [n]: ").strip().lower()

    if customize == "y":
        print("  (Enter 0 for native resolution)")
        width  = _prompt_int("Image width  (px, 0=native)", 0)
        height = _prompt_int("Image height (px, 0=native)", 0)
        width  = width  if width  > 0 else None
        height = height if height > 0 else None
        fmt = input("  Format [png] / jpg / tiff: ").strip() or "png"
        default_name = f"satellite_{min_lat}_{min_lon}_{max_lat}_{max_lon}.{fmt}"
        name = input(f"  Output filename [{default_name}]: ").strip() or default_name
    else:
        width = None
        height = None
        fmt = "png"
        name = f"satellite_{min_lat}_{min_lon}_{max_lat}_{max_lon}.{fmt}"

    print()
    try:
        saved = download_satellite_image(
            min_lat=min_lat,
            min_lon=min_lon,
            max_lat=max_lat,
            max_lon=max_lon,
            width=width,
            height=height,
            output_path=name,
            image_format=fmt,
        )
        print(f"\nDone! Open the image at:\n   {saved}")
    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()