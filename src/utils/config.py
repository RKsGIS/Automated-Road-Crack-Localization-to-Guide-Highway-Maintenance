from pathlib import Path

# Retry configuration for HTTP requests
MAX_RETRIES = 3
BACKOFF_FACTOR = 2
REQUEST_LIMIT = 20
REQUEST_WAIT_TIME = 60

# URLs
SWISS_IMAGE_URL = "https://data.geo.admin.ch/api/stac/v0.9/collections/ch.swisstopo.swissimage-dop10/items?bbox={bbox}"
METADATA_URL = "https://data.geo.admin.ch/ch.swisstopo.images-swissimage-dop10.metadata/shp/2056/ch.swisstopo.images-swissimage-dop10.metadata.zip"

# Directories
BASE_DIR = Path(__file__).resolve().parents[3]

DATA_DIR = BASE_DIR / "data"

RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"

ROADS_FILEPATH = RAW_DIR / "osm_roads.gpkg"
RAILWAY_FILEPATH = RAW_DIR / "osm_railways.gpkg"
DEFAULT_ROAD_FILEPATH = PROCESSED_DIR / "buffered_roads.gpkg"
LABELED_DATASET_DIR = PROCESSED_DIR / "labeling_dataset"


OUTPUT_DIR = BASE_DIR / "output"
SWISS_IMAGE_DIR = OUTPUT_DIR / "imagery/swiss_image"
ROAD_SEGMENTS_DIR = OUTPUT_DIR / "imagery/road_segments"
TIFF_DIR = OUTPUT_DIR / "tiles/tiff"
TOLABEL_DIR = OUTPUT_DIR / "tiles/tolabel"
GEODATA_DIR = OUTPUT_DIR / "geodata"

# Create directories
for directory in [RAW_DIR, PROCESSED_DIR, SWISS_IMAGE_DIR, ROAD_SEGMENTS_DIR, TIFF_DIR, TOLABEL_DIR, GEODATA_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
