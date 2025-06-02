<!-- Output readme.md -->
# Output Directory

Stores outputs from the Swiss Crack pipeline, including models, imagery, segments, tiles, datasets, geodata, and visualizations. All geospatial data uses crs EPSG:2056. See the [root README](../README.md) for the overall workflow.

## Subdirectories

- **models/**:
  -  YOLOv11 weights and results from `src/modeling/train_model.py`.
  
- **imagery/**:
  - `swiss_image/*.tif`: 1km x 1km TIFFs from `src/data_retrieval/download_images.py`.
  - `road_segments/*.tif`: Cropped TIFFs of road buffers from `src/data_retrieval/crop_and_tile.py`.


- **tiles/**:
  - `tiff/*.tif`: 5m x 5m TIFF tiles for prediction, from `src/data_retrieval/crop_and_tile.py`.
  - `tolabel/*.jpg`: JPEG tiles for CrowdMap annotation, from `src/dataset/select_labeling_data.py`.

- **dataset/**:
  - `train/{crack,no_crack}/*.tif`: 80% split, augmented cracks, from `src/dataset/split_and_augment.py`.
  - `val/{crack,no_crack}/*.tif`: 10% split.
  - `test/{crack,no_crack}/*.tif`: 10% split.



- **geodata/**:
  - `metadata.zip`: SwissTopo grid metadata, downloaded by `src/data_retrieval/geo_utils.py`.
  - `road_segments.gpkg`: Vector road segments from `src/data_retrieval/crop_and_tile.py`. Columns: `unique_id`.
  - `tiles.gpkg`: Vector tiles from `src/data_retrieval/crop_and_tile.py`. Columns: `tile_id`, `label`, `split`.
  - `tiled_gdf_with_predictions.gpkg`: Tiles with predictions and confidence score from `src/modeling/evaluate_and_predict.py`.
  - `traffic_with_rhcd.gpkg`: Traffic data with RHCD from `src/visualization/plot_correlations.py`. 
  - `LTLST_with_rhcd.gpkg`: LT-LST-A data with RHCD.


- **visualizations/**:
  - `gradcam/`: Guided Grad-CAM visualizations from `src/modeling/visualize_gradcam.py`.
  - `traffic_vs_crack.png`: Traffic volume vs. RHCD plot from `src/visualization/plot_correlations.py`.
  - `lst_vs_crack.png`: LT-LST-A vs. RHCD plot from `src/visualization/plot_correlations.py`.
