
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import random
from pathlib import Path
import numpy as np
from osgeo import gdal
import geopandas as gpd
from tqdm import tqdm
import shutil
import logging
from datetime import datetime
from src.utils.config import *

# Minimal logging with timestamp
current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z")
logging.basicConfig(level=logging.INFO, format=f'%(asctime)s - {current_time} - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def split_and_augment_dataset(
    input_base=str(LABELED_DATASET_DIR), 
    output_base=str(OUTPUT_DIR / "dataset"),
    gpkg_path=str(GEODATA_DIR / "tiles.gpkg"),
    classes=["crack", "no_crack"],
    split_ratio=[0.8, 0.1, 0.1]
):
    logger.info(f"Starting dataset split and augmentation")
    try:
        gdf = gpd.read_file(gpkg_path)
    except Exception as e:
        logger.error(f"Failed to read {gpkg_path}: {e}")
        raise

    gdf['split'] = None
    output_base = Path(output_base)
    for split in ["train", "val", "test"]:
        for cls in classes:
            (output_base / split / cls).mkdir(parents=True, exist_ok=True)

    input_base = Path(input_base)
    for cls in classes:
        input_class_dir = input_base / cls
        all_files = [f for f in input_class_dir.glob("*.tif")]
        random.shuffle(all_files)
        total = len(all_files)
        n_train = int(split_ratio[0] * total)
        n_val = int(split_ratio[1] * total)
        n_test = total - n_train - n_val

        split_files = {
            "train": all_files[:n_train],
            "val": all_files[n_train:n_train + n_val],
            "test": all_files[n_train + n_val:]
        }
        for split, files in split_files.items():
            for src in files:
                dst = output_base / split / cls / src.name
                shutil.copy2(src, dst)
                match_idx = gdf[gdf['filename'] == src.name].index
                if not match_idx.empty:
                    gdf.loc[match_idx, 'split'] = split

    try:
        gdf.to_file(gpkg_path, driver="GPKG")
    except Exception as e:
        logger.error(f"Failed to save {gpkg_path}: {e}")
        raise

    train_crack_dir = output_base / "train" / "crack"
    def save_tiff(image_array, output_path):
        driver = gdal.GetDriverByName('GTiff')
        out_ds = driver.Create(str(output_path), image_array.shape[1], image_array.shape[0], 3, gdal.GDT_Byte)
        for i in range(3):
            out_ds.GetRasterBand(i + 1).WriteArray(image_array[:, :, i])
        out_ds.FlushCache()

    def augment_image(image_array):
        return {
            "horizontal_flip": np.fliplr(image_array),
            "vertical_flip": np.flipud(image_array),
            "rotate_90": np.rot90(image_array, k=1),
            "rotate_270": np.rot90(image_array, k=3),
            "brightness_plus": np.clip(image_array.astype(np.int16) + 40, 0, 255).astype(np.uint8),
            "brightness_minus": np.clip(image_array.astype(np.int16) - 40, 0, 255).astype(np.uint8)
        }

    for image_path in tqdm(train_crack_dir.glob("*.tif"), desc="Augmenting images"):
        try:
            dataset = gdal.Open(str(image_path))
            image_array = dataset.ReadAsArray().transpose(1, 2, 0)
            augmentations = augment_image(image_array)
            for aug_type, aug_img in augmentations.items():
                aug_name = f"{image_path.stem}_{aug_type}.tif"
                output_path = train_crack_dir / aug_name
                save_tiff(aug_img, output_path)
        except Exception as e:
            logger.error(f"Failed to augment {image_path.name}: {e}")

    logger.info("Dataset split and augmentation completed")

if __name__ == "__main__":
    split_and_augment_dataset()