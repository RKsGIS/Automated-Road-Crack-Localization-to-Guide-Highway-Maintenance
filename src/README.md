# Src Directory

Contains source code for the Swiss Crack project, organized into subdirectories for data retrieval, dataset preparation, modeling, visualization, and utilities. See the [root README](../README.md) for the overall workflow.


## Directory Structure

- **`data_retrieval/`**: Scripts for downloading and preprocessing satellite imagery and road data.
- **`dataset/`**: Scripts for selecting tiles for labeling and preparing the dataset for training.
- **`modeling/`**: Scripts for training, evaluating, and visualizing the YOLOv11 model.
- **`visualization/`**: Scripts for generating correlation plots between cracks and external factors.
- **`utils/`**: Utility scripts for configuration, HTTP requests, and archiving.
- **`run.py`**: Main script to execute pipeline tasks.
- **`README.md`**: This file.



## Scripts

### data_retrieval/

Handles imagery acquisition and preprocessing.

- **`mask_filter.py`**:
  - **Purpose**: Filters `buffered_roads.gpkg` for obstructions (railways, non-motorway tunnels).
  - **Arguments**: `--roads-filepath` (default: `data/processed/buffered_roads.gpkg`)
  - **Inputs**:
    - `data/processed/buffered_roads.gpkg`
    - `data/raw/{osm_railways.shp,osm_roads.shp}`
  - **Outputs**:  updats the input buffered_roads.gpkg
  - **Usage**:
    ```bash
    python src/run.py --mask-filter --roads-filepath data/processed/buffered_roads.gpkg
    ```


- **`download_images.py`**:
  - **Purpose**: Downloads 1km x 1km imagery intersecting road buffers.
  - **Arguments**: `--roads-filepath` (default: `data/processed/buffered_roads.gpkg`)
  - **Inputs**: `data/processed/buffered_roads.gpkg`
  - **Outputs**: `output/imagery/swiss_image/*.tif`
  - **Usage**:
    ```bash
    python src/run.py --download-images --roads-filepath data/processed/buffered_roads.gpkg
    ```

- **`crop_and_tile.py`**:
  - **Purpose**: Crops imagery to road buffers and tiles into 5m x 5m TIFFs.
  - **Arguments**: `--roads-filepath` (default: `data/processed/buffered_roads.gpkg`)
  - **Inputs**:
    - `data/processed/buffered_roads.gpkg`
    - `output/imagery/swiss_image/*.tif`
  - **Outputs**:
    - `output/imagery/road_segments/*.tif`
    - `output/geodata/road_segments.gpkg`
    - `output/tiles/tiff/*.tif`
    - `output/geodata/tiles.gpkg`
  - **Usage**:
    ```bash
    python src/run.py --crop-and-tile --roads-filepath data/processed/buffered_roads.gpkg
    ```



### dataset/

Prepares datasets for training.

- **`select_labeling_data.py`**:
  - **Purpose**: Selects ~30,000 tiles for labeling using KMeans, converts TIFFs to JPEGs.
  - **Arguments**: None
  - **Inputs**:
    - `output/geodata/tiles.gpkg`
    - `output/tiles/tiff/*.tif`
  - **Outputs**:
    - Updated `output/geodata/tiles.gpkg` (`label` column: `selected`/`not_selected`)
    - `output/tiles/tolabel/*.jpg`
  - **Usage**:
    ```bash
    python src/run.py --select-tiles
    ```
  !!!! /after annotation run this 

- **`split_and_augment.py`**:
  - **Purpose**: Splits labeled JPEGs (80% train, 10% val, 10% test), augments train/crack images (flips, rotations, brightness).
  - **Inputs**:
    - `data/processed/labelled_dataset/{crack,no_crack}/*.jpg`
    - `output/geodata/tiles.gpkg`
  - **Outputs**:
    - `output/dataset/{train,val,test}/{crack,no_crack}/*.jpg`
    - Updated `output/geodata/tiles.gpkg` (`split` column)
  - **Usage**:
    ```bash
    python src/run.py --split-augment
    ```

### modeling/

Trains and evaluates YOLOv11.

- **`train_model.py`**:
  - **Purpose**: Trains YOLOv11 (`yolo11x-cls.pt`, imgsz=64, epochs=500, batch=128).
  - **Inputs**: `output/dataset/{train,val,test}/{crack,no_crack}/*.jpg`
  - **Outputs**: `output/models/train
  - **Usage**:
    ```bash
    python src/run.py --train-model
    ```

- **`evaluate_and_predict.py`**:
  - **Purpose**: Evaluates model on val/test sets, predicts on all tiles.
  - **Inputs**:
    - `output/models/train/weights/best.pt`
    - `output/dataset/{val,test}/{crack,no_crack}/*.jpg`
    - `output/geodata/tiles.gpkg`
    - `output/tiles/tolabel/*.jpg`
  - **Outputs**:
    - `output/geodata/tiled_gdf_with_predictions.gpkg`
    - Console: Classification reports
  - **Usage**:
    ```bash
    python src/run.py --evaluate-predict
    ```

- **`visualize_gradcam.py`**:
  - **Purpose**: Generates Grad-CAM for random 3 test/crack images.
  - **Arguments**: `--n` (default: 3, number of images)
  - **Inputs**:
    - `output/models/train/weights/best.pt`
    - `output/dataset/test/crack/*.jpg`
  - **Outputs**: `output/visualizations/gradcam/*.png`
  - **Usage**:
    ```bash
    python src/run.py --gradcam
    ```

### visualization/

Generates correlation analyses.

- **`plot_correlations.py`**:
  - **Purpose**: Correlates RHCD with traffic and LT-LST-A.
  - **Inputs**:
    - `data/processed/{traffic_volume.gpkg,LTLST.gpkg}`
    - `output/geodata/tiled_gdf_with_predictions.gpkg`
  - **Outputs**:
    - `output/geodata/{traffic_with_rhcd.gpkg,LTLST_with_rhcd.gpkg}`
    - `output/visualizations/{traffic_vs_crack.png,lst_vs_crack.png}`
  - **Usage**:
    ```bash
    python src/run.py --plot-correlations
    ```

### utils/

Utility scripts.

- **`config.py`**:
  - **Purpose**: Defines paths (e.g., `OUTPUT_DIR`, `TOLABEL_DIR`).
  - **Outputs**: Path variables.
  - **Notes**: Update if project directory changes.

- **`request_utils.py`**:
  - **Purpose**: Handles HTTP requests with retries.
  - **Inputs**: Bounding box.
  - **Outputs**: TIFFs in `output/imagery/swiss_image/`.
  - **Usage**: Called by `download_images.py`.

<!-- - **`create_zip_archives.py`**:
  - **Purpose**: Zips TIFFs and JPEGs.
  - **Inputs**:
    - `output/tiles/tiff/*.tif`
    - `output/tiles/tolabel/*.jpg`
  - **Outputs**:
    - `output/archives/{tiled_raster.zip,tiled_jpg.zip}`
  - **Usage**:
    ```bash
    python src/run.py --create-archives
    ``` -->

- **`geo_utils.py`**:
  - **Purpose**: Geospatial utilities for loading grids, cropping rasters, tiling, and TIFF-to-JPEG conversion.
  - **Functions**:
    - `load_grids()`: Loads SwissTopo metadata from `output/geodata/metadata.zip`.
    - `find_raster_file(identifier)`: Locates TIFFs in `output/imagery/swiss_image/`.
    - `crop_raster(crop_gdf)`: Crops rasters to road buffers → `output/imagery/road_segments/`, `output/geodata/road_segments.gpkg`.
    - `make_tiles(polygon, unique_id, tile_size=5)`: Generates 5m x 5m tiles.
    - `tile_vector(cropped_gdf)`: Creates vector tiles → `output/geodata/tiles.gpkg`.
    - `tile_images(tiles_gdf)`: Generates TIFF tiles → `output/tiles/tiff/`.
    - `convert_tiff_to_jpeg(tiff_path, jpeg_path)`: Converts TIFFs to JPEGs.
    - `process_grids(swiss_grids, buffered_roads)`: Clips grids to roads.
  - **Inputs**:
    - `output/geodata/metadata.zip`
    - `output/imagery/swiss_image/*.tif`
    - `data/processed/buffered_roads.gpkg`
  - **Outputs**:
    - `output/imagery/road_segments/*.tif`
    - `output/geodata/road_segments.gpkg`
    - `output/tiles/tiff/*.tif`
    - `output/geodata/tiles.gpkg`




### run.py

- **Purpose**: Executes pipeline tasks.
- **Arguments**:
  - `--mask-filter`: Run `mask_filter.py`
  - `--download-images`: Run `download_images.py`
  - `--crop-and-tile`: Run `crop_and_tile.py`
  - `--select-tiles`: Run `select_labeling_data.py`
  - `--split-augment`: Run `split_and_augment.py`
  - `--train-model`: Run `train_model.py`
  - `--evaluate-predict`: Run `evaluate_and_predict.py`
  - `--gradcam`: Run `visualize_gradcam.py`
  - `--plot-correlations`: Run `plot_correlations.py`
  <!-- - `--create-archives`: Run `create_zip_archives.py` -->
  - `--all`: Run all tasks sequentially
  - `--roads-filepath`: Path to roads GeoPackage (default: `data/processed/buffered_roads.gpkg`)
  - `--n`: Number of Grad-CAM images (default: 3)
- **Usage**:
  ```bash
  python src/run.py --all --roads-filepath data/processed/buffered_roads.gpkg
  ```


## Workflow

1. **Prepare Data**:
   - Place raw/processed data in `data/` (see [data/README.md](../data/README.md)).
   - Generate `data/processed/LTLST.gpkg` (see [docs/README.md](../docs/README.md)).

2. **Run Pipeline**:

   ```bash
   python src/run.py --mask-filter
   python src/run.py --download-images
   python src/run.py --crop-and-tile
   python src/run.py --select-tiles
   ```
   - !!! Annotate `output/tiles/tolabel/*.jpg` in [CrowdMap](https://crowdmap.heigit.org/) → `data/processed/labelled_dataset/{crack,no_crack}/`.
   ```bash
   python src/run.py --split-augment
   python src/run.py --train-model
   python src/run.py --evaluate-predict
   python src/run.py --gradcam
   python src/run.py --plot-correlations
   python src/run.py --create-archives
   ```

3. **Outputs**:
   - Model: `output/models/train/weights/best.pt`
   - Predictions: `output/geodata/tiled_gdf_with_predictions.gpkg`
   - Visualizations: `output/visualizations/{traffic_vs_crack.png,lst_vs_crack.png,gradcam/*.png}`
   - Archives: `output/archives/{tiled_raster.zip,tiled_jpg.zip}`
   - See [output/README.md](../output/README.md).

## Notes

<!-- - **TIFF-to-JPEG**: Handled by `select_labeling_data.py` via `geo_utils.py`. -->
- **Labeling**: After annotation, move JPEGs to `data/processed/labelled_dataset/`.
- **CRS**: Scripts use EPSG:2056.
- **Errors**: Check console logs for issues (e.g., missing files).

See [root README](../README.md) for project overview.
