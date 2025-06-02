import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import geopandas as gpd
from tqdm import tqdm
import logging
from src.utils.request_utils import find_image
from src.utils.geo_utils import load_grids
from src.utils.config import SWISS_IMAGE_DIR, DEFAULT_ROAD_FILEPATH

# Minimal logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def download_images(road_filepath=DEFAULT_ROAD_FILEPATH, output_dir=SWISS_IMAGE_DIR):
    """Download satellite imagery for road buffers."""
    logger.info(f"Starting image download for {road_filepath}")

    try:
        road_buffer = gpd.read_file(road_filepath)
        if road_buffer.empty:
            logger.error("Input GeoPackage is empty")
            raise ValueError("Empty road buffer")
    except Exception as e:
        logger.error(f"Failed to read {road_filepath}: {e}")
        raise

    road_union = road_buffer.unary_union
    swiss_grids = load_grids()
    intersections = swiss_grids[swiss_grids.intersects(road_union)].to_crs(epsg=4326)
    
    logger.info(f"Downloading {len(intersections)} images to {output_dir}")
    for grid in tqdm(intersections.geometry, desc="Downloading images"):
        bbox = grid.centroid.buffer(0.0001).bounds
        find_image(bbox)

    logger.info("Image download completed")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Download satellite imagery for road buffers.")
    parser.add_argument("--road-filepath", type=str, default=str(DEFAULT_ROAD_FILEPATH),
                        help="Path to roads GeoPackage (default: data/processed/buffered_roads.gpkg).")
    parser.add_argument("--output-dir", type=str, default=str(SWISS_IMAGE_DIR),
                        help="Directory to save imagery (default: output/imagery/swiss_image).")
    args = parser.parse_args()
    download_images(args.road_filepath, args.output_dir) 