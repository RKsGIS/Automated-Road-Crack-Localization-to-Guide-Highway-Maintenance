# script/make_zip.py

import shutil
from src.util.config import TILED_TIFF_DIR, TILED_JPEG_DIR

def make_zip():
    # Create a ZIP archive of the TILED_TIFF_DIR directory
    shutil.make_archive(TILED_TIFF_DIR, 'zip', TILED_TIFF_DIR)

    # Create a ZIP archive of the TILED_JPEG_DIR directory
    shutil.make_archive(TILED_JPEG_DIR, 'zip', TILED_JPEG_DIR)