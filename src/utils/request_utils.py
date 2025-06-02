import os
import requests
from pathlib import Path
import re
from datetime import datetime
import time
from src.util.config import SWISS_IMAGE_DIR, MAX_RETRIES, BACKOFF_FACTOR, SWISS_IMAGE_URL

# Minimal logging
import logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

date_format = "%Y-%m-%dT%H:%M:%SZ"

def get_json(url, max_retries=MAX_RETRIES, backoff_factor=BACKOFF_FACTOR):
    """Fetch JSON data from a URL with retries on failure."""
    attempts = 0
    while attempts < max_retries:
        try:
            r = requests.get(url)
            r.raise_for_status()
            return r.json()
        except requests.RequestException as e:
            logger.error(f"Request failed: {e}")
            if attempts < max_retries - 1:
                time.sleep(backoff_factor ** attempts)
            attempts += 1
    logger.error("Max retries exceeded")
    raise RuntimeError("Max retries exceeded.")

def get_latest_feature(features):
    latest_feature = None
    latest_date = None

    for feature in features.get('features', []):
        feature_date = datetime.strptime(feature["properties"]["datetime"], date_format)
        if latest_date is None or feature_date > latest_date:
            latest_date = feature_date
            latest_feature = feature
    return latest_feature

def download_file(href, file_path):
    """Download a file from a URL."""
    try:
        with requests.get(href, stream=True) as r:
            r.raise_for_status()
            file_path.write_bytes(r.content)
    except requests.RequestException as e:
        logger.error(f"Failed to download {href}: {e}")

def find_image(bbox):
    url = SWISS_IMAGE_URL.format(bbox=",".join(map(str, bbox)))
    features = get_json(url)
    latest_feature = get_latest_feature(features)
    if not latest_feature:
        return

    identifier = latest_feature["id"]
    match = re.search(r'\d{4}_\d{4}-\d{4}', identifier)
    name = match.group(0) if match else identifier

    for asset_name, asset_info in latest_feature["assets"].items():
        if "_0.1_" in asset_name and asset_name.endswith(".tif"):
            href = asset_info["href"]
            file_path = SWISS_IMAGE_DIR / f"{name}.tif"
            if not file_path.exists():
                download_file(href, file_path)
            else:
                logger.info(f"File {file_path} already exists")
