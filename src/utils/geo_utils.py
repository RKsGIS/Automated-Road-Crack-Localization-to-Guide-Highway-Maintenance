
import os
import geopandas as gpd
import requests
import numpy as np
import rasterio
from rasterio.mask import mask
from shapely.geometry import box
from tqdm import tqdm
from pathlib import Path
from PIL import Image
import pandas as pd
from src.util.config import *
import cv2
# Minimal logging
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def load_grids():
    """Load Swiss grids data, downloading if not present."""
    local_filename = GEODATA_DIR / "metadata.zip"
    
    if local_filename.exists():
        try:
            return gpd.read_file(f"zip://{local_filename}!ch.swisstopo.images-swissimage-dop10.metadata.shp")
        except Exception as e:
            logger.error(f"Failed to load {local_filename}: {e}")
            return None

    try:
        logger.info(f"Downloading metadata from {METADATA_URL}")
        with requests.get(METADATA_URL, stream=True) as r:
            r.raise_for_status()
            local_filename.write_bytes(r.content)
        return gpd.read_file(f"zip://{local_filename}!ch.swisstopo.images-swissimage-dop10.metadata.shp")
    except Exception as e:
        logger.error(f"Failed to download or read metadata: {e}")
        return None

def find_raster_file(identifier):
    for file_name in os.listdir(SWISS_IMAGE_DIR):
        if identifier in file_name and file_name.endswith('.tif'):
            return SWISS_IMAGE_DIR / file_name
    return None

def crop_raster(crop_gdf):
    for idx, row in tqdm(crop_gdf.iterrows(), total=crop_gdf.shape[0], desc="Cropping rasters"):
        unique_id = row['unique_id']
        raster_path = row['raster_path']
        raster_geometry = [row['geometry']]
        unique_identifier = row['id']

        file_path = SWISS_IMAGE_DIR / raster_path
        cropped_raster_path = ROAD_SEGMENTS_DIR / f"{unique_id}_{raster_path}"

        if cropped_raster_path.exists():
            continue

        if not file_path.exists():
            file_path = find_raster_file(unique_identifier)
            if not file_path:
                crop_gdf.at[idx, 'skip_reason'] = f"File with ID '{unique_identifier}' not found."
                continue

        try:
            with rasterio.open(file_path) as src:
                out_image, out_transform = mask(src, raster_geometry, crop=True)
                if not np.any(out_image):
                    crop_gdf.at[idx, 'skip_reason'] = "No data in cropped raster."
                    continue

                out_meta = src.meta.copy()
                out_meta.update({
                    "driver": "GTiff",
                    "height": out_image.shape[1],
                    "width": out_image.shape[2],
                    "transform": out_transform,
                    "nodata": 0,
                    "compress": "LZW"
                })
                with rasterio.open(cropped_raster_path, 'w', **out_meta) as dst:
                    dst.write(out_image)
        except Exception as e:
            crop_gdf.at[idx, 'skip_reason'] = f"Error processing {raster_path}: {e}"

    crop_gdf.to_file(GEODATA_DIR / "road_segments.gpkg")
    skip_count = crop_gdf['skip_reason'].notnull().sum()
    logger.info(f"Skipped {skip_count} rows due to issues")
    return crop_gdf[crop_gdf['skip_reason'].isnull()]

def make_tiles(polygon, unique_id, tile_size=5):
    minx, miny, maxx, maxy = polygon.bounds
    x_coords = np.arange(minx, maxx, tile_size)
    y_coords = np.arange(miny, maxy, tile_size)
    tiles = []
    tile_id = 0
    
    for x in x_coords:
        for y in y_coords:
            tile = box(x, y, x + tile_size, y + tile_size)
            if tile.intersects(polygon):
                tiles.append({
                    'tile_id': f"{unique_id}_tile_{tile_id}",
                    'x_origin': x,
                    'y_origin': y,
                    'tile_geo': tile
                })
                tile_id += 1
    return tiles

def tile_vector(cropped_gdf):
    tile_records = []
    for idx, row in tqdm(cropped_gdf.iterrows(), total=cropped_gdf.shape[0], desc="Generating tiles"):
        polygon = row.geometry
        unique_id = row['unique_id']
        tiles = make_tiles(polygon, unique_id)
        for tile in tiles:
            for column in cropped_gdf.columns:
                if column != 'geometry':
                    tile[column] = row[column]
            tile_records.append(tile)

    tiles_gdf = gpd.GeoDataFrame(tile_records, geometry='tile_geo', crs=cropped_gdf.crs)
    tiles_gdf = tiles_gdf.rename(columns={'tile_geo': 'geometry'})
    tiles_gdf = tiles_gdf.set_geometry('geometry')
    tiles_gdf['tile_id'] = tiles_gdf['tile_id'].astype(str) + '.tif'
    tiles_gdf.to_file(GEODATA_DIR / "tiles.gpkg")
    return tiles_gdf

def tile_images(tiles_gdf):
    for _, row in tqdm(tiles_gdf.iterrows(), total=len(tiles_gdf), desc="Processing tiles"):
        tile_id = row['tile_id']
        raster_path = ROAD_SEGMENTS_DIR / row['crop_path']
        output_tile_path = TIFF_DIR / f"{tile_id}"

        if not raster_path.exists():
            continue
        
        try:
            with rasterio.open(raster_path) as src:
                out_image, out_transform = mask(src, [row['geometry']], crop=True)
                out_meta = src.meta.copy()

                height, width = out_image.shape[1], out_image.shape[2]
                target_size = (50, 50)
                padded_image = np.zeros((out_image.shape[0], *target_size), dtype=out_image.dtype)

                y_offset = max((target_size[0] - height) // 2, 0)
                x_offset = max((target_size[1] - width) // 2, 0)
                paste_height = min(height, target_size[0])
                paste_width = min(width, target_size[1])

                padded_image[:, y_offset:y_offset+paste_height, x_offset:x_offset+paste_width] = \
                    out_image[:, :paste_height, :paste_width]

                out_meta.update({
                    "driver": "GTiff",
                    "height": target_size[0],
                    "width": target_size[1],
                    "transform": out_transform,
                    "nodata": 0,
                    "compress": "LZW"
                })

                with rasterio.open(output_tile_path, "w", **out_meta) as dest:
                    dest.write(padded_image)
        except Exception as e:
            logger.error(f"Error processing {raster_path.stem}: {e}")

# def convert_to_jpeg(tiff_dir=None, jpeg_dir=None):
#     tiff_dir = Path(tiff_dir) if tiff_dir else TIFF_DIR
#     jpeg_dir = Path(jpeg_dir) if jpeg_dir else TILED_JPEG_DIR
    
#     for tiff_path in tqdm(list(tiff_dir.glob("*.tif")), desc="Converting TIFF to JPEG"):
#         jpeg_path = jpeg_dir / f"{tiff_path.stem}.jpg"
        
#         if jpeg_path.exists():
#             continue
        
#         try:
#             with Image.open(tiff_path) as img:
#                 img.convert("RGB").save(jpeg_path, "JPEG", quality=95)
#         except Exception as e:
#             logger.error(f"Error converting {tiff_path.stem}: {e}")


def convert_tiff_to_jpeg(tiff_path, jpeg_path):
    """Convert TIFF to JPEG."""
    try:
        img = cv2.imread(str(tiff_path), cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"Failed to read {tiff_path}")
        cv2.imwrite(str(jpeg_path), img, [int(cv2.IMWRITE_JPEG_QUALITY), 95])
    except Exception as e:
        logger.error(f"Failed to convert {tiff_path} to JPEG: {e}")

def process_grids(swiss_grids, buffered_roads):
    swiss_grids['id'] = swiss_grids['id'].str.replace('_', '-')  # Match image naming convention
    buffered_roads = buffered_roads.to_crs(swiss_grids.crs)
    clipped_grids = gpd.clip(swiss_grids, buffered_roads)

    exploded_grids = clipped_grids.explode(index_parts=False).reset_index(drop=True)
    exploded_grids['unique_id'] = range(len(exploded_grids))
    exploded_grids = exploded_grids.set_index('unique_id')

    joined_grids = gpd.sjoin(exploded_grids, buffered_roads, how='left', predicate='intersects')
    joined_grids['overlap_area'] = joined_grids.apply(
        lambda row: row['geometry'].intersection(buffered_roads.loc[row['index_right'], 'geometry']).area 
        if pd.notnull(row['index_right']) else 0, axis=1
    )
    joined_grids.reset_index(drop=False, inplace=True)
    final_grids = joined_grids.loc[joined_grids.groupby('unique_id')['overlap_area'].idxmax()].reset_index(drop=True)

    final_grids['raster_path'] = final_grids['datenstand'] + '_' + final_grids['id'] + '.tif'
    final_grids['crop_path'] = final_grids['unique_id'].astype(str) + '_' + final_grids['raster_path']
    final_grids['skip_reason'] = None
    return final_grids
