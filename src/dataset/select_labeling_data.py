import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import geopandas as gpd
import numpy as np
from sklearn.cluster import KMeans
from scipy.spatial import cKDTree
from pathlib import Path
from tqdm import tqdm
import shutil
import logging
from datetime import datetime
from src.utils.config import *
from src.utils.geo_utils import convert_tiff_to_jpeg

# Minimal logging with timestamp
current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z")
logging.basicConfig(level=logging.INFO, format=f'%(asctime)s - {current_time} - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def select_and_copy_tiles(
    gpkg_path=str(OUTPUT_DIR / "tiles.gpkg"),
    src_folder=str(TIFF_DIR),
    dest_folder=str(TOLABEL_DIR),
    file_column="filename",
    n_samples=30000
):
    logger.info(f"Starting tile selection from {gpkg_path}")
    try:
        tiles = gpd.read_file(gpkg_path)
    except Exception as e:
        logger.error(f"Failed to read {gpkg_path}: {e}")
        raise

    points = tiles.geometry.representative_point()
    coords = np.array([[p.x, p.y] for p in points])
    n_clusters = min(n_samples, len(tiles))

    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    kmeans.fit(coords)
    tree = cKDTree(coords)
    _, idx = tree.query(kmeans.cluster_centers_, k=1)

    tiles['label'] = 'not_selected'
    tiles.loc[idx, 'label'] = 'selected'
    try:
        tiles.to_file(gpkg_path, driver='GPKG')
    except Exception as e:
        logger.error(f"Failed to save {gpkg_path}: {e}")
        raise

    selected = tiles[tiles['label'] == 'selected']
    file_list = selected[file_column].tolist()

    dest_folder = Path(dest_folder)
    dest_folder.mkdir(parents=True, exist_ok=True)
    src_folder = Path(src_folder)
    for fname in tqdm(file_list, desc="Copying tiles"):
        src_path = src_folder / fname
        dest_path = dest_folder / fname
        try:
            shutil.copy2(src_path, dest_path)
            tiff_path = dest_folder / fname
            jpeg_path = dest_folder / f"{tiff_path.stem}.jpg"
            convert_tiff_to_jpeg(tiff_path, jpeg_path)
        except FileNotFoundError:
            logger.error(f"File {src_path} not found")

    logger.info(f"Selected and copied {len(file_list)} tiles to {dest_folder}")

if __name__ == "__main__":
    select_and_copy_tiles()


    
