import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import geopandas as gpd
import logging
from src.utils.geo_utils import load_grids, process_grids, crop_raster, tile_vector, tile_images
from src.utils.config import *

# Minimal logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def crop_and_tile(road_filepath=DEFAULT_ROAD_FILEPATH):
    """Crop and tile road buffers using satellite imagery."""
    logger.info(f"Starting crop and tile process for {road_filepath}")

    try:
        road_buffer = gpd.read_file(road_filepath)
        if road_buffer.empty:
            logger.error("Input GeoPackage is empty")
            raise ValueError("Empty road buffer")
    except Exception as e:
        logger.error(f"Failed to read {road_filepath}: {e}")
        raise

    swiss_grids = load_grids()
    final_grids = process_grids(swiss_grids, road_buffer)
    cropped_gdf = crop_raster(final_grids)
    tiles_gdf = tile_vector(cropped_gdf)
    tile_images(tiles_gdf)

    logger.info("Crop and tile process completed")
    print("Processing completed successfully.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--road-filepath", type=str, default="data/processed/buffered_roads.gpkg")
    args = parser.parse_args()
    crop_and_tile(args.road_filepath)
