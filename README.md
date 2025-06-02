<!-- ROOT readme.md -->
# Swiss Crack: Highway Crack Detection

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org)
[![Conda](https://img.shields.io/badge/Conda-Environment-green.svg)](environment.yml)

This repository implements a pipeline for detecting cracks in Swiss highways using 10cm-resolution aerial imagery from the Swiss Geo API, OpenStreetMap (OSM) data, and a YOLOv11 model. The workflow filters road geometries, downloads imagery, tiles it into 5m x 5m segments, creates annotation samples, trains a model, evaluates performance, and correlates predictions with traffic volume and long-term land surface temperature anomalies (LT-LST-A). 

# Abstract
Highway networks are crucial for economic prosperity. Climate change-induced temperature fluctuations are exacerbating stress on road pavements, resulting in elevated maintenance costs. This underscores the need for targeted and efficient maintenance strategies. This study investigates the potential of open-source data to guide highway infrastructure maintenance. The proposed framework integrates airborne imagery and OpenStreetMap (OSM) to fine-tune YOLOv11 for highway crack localization. To demonstrate the framework's real-world applicability, a Swiss Relative Highway Crack Density (RHCD) index was calculated to inform nationwide highway maintenance. The crack classification model achieved an F1-score of 0.84 for the positive class (crack) and 0.97 for the negative class (no crack). The Swiss RHCD index exhibited weak correlations with Long-term Land Surface Temperature Amplitudes (LT-LST-A) (Pearson’s \(r = -0.05\)) and Traffic Volume (TV) (Pearson’s \(r = 0.17\)), underlining the added value of this novel index for guiding maintenance over other data. Significantly high RHCD values were observed near urban centers and intersections, providing contextual validation for the predictions. These findings highlight the value of open-source data sharing to drive innovation, ultimately enabling more efficient solutions in the public sector.

## Prerequisites

- **Software**: Python 3.8+, QGIS, Conda, [CrowdMap](https://crowdmap.heigit.org/) .
- **Data Sources**:
  - [Geofabrik](https://download.geofabrik.de/europe/switzerland.html) (OSM roads, railways).
  - [swissTLMRegio](https://www.swisstopo.admin.ch/en/landscape-model-swisstlmregio) (lane data).
  - [Swiss Geo API](https://data.geo.admin.ch/api/stac/v0.9/collections/ch.swisstopo.swissimage-dop10) (10cm imagery).
  - [OpenData Swiss](https://opendata.swiss) (traffic volume).
  - Google Earth Engine (LT-LST-A, see [docs/README.md](docs/README.md#long-term-land-surface-temperature-anomalies)).
- **Hardware**: GPU recommended for training.
## Setup

```bash
git clone https://github.com/<your-username>/swiss-crack.git
cd swiss-crack
conda env create -f environment.yml
conda activate swiss_crack
```

## Repository Structure

- **`data/`**: Raw and processed datasets (OSM, lane data, traffic, LT-LST-A). See [data/README.md](data/README.md).
- **`output/`**: Model outputs, imagery, tiles, datasets, geodata, visualizations, and archives. See [output/README.md](output/README.md).
- **`src/`**: Source code for data retrieval, dataset preparation, modeling, and visualization. See [src/README.md](src/README.md).
- **`docs/`**: Documentation and example images. See [docs/README.md](docs/README.md).
- **`environment.yml`**: Conda environment file.
- **`LICENSE`**: MIT License.

## Workflow

1. **Road Data Preparation (External Pre-Processing)**:
   - **Overview**: Prepare highway data using external tools (e.g., QGIS) before running the codes. 
   - **Steps**:
     - Download OSM road data (`osm_roads.gpkg`) from [Geofabrik](https://download.geofabrik.de/europe/switzerland.html) and lane data (`lane_data.gpkg`) from [swissTLMRegio](https://www.swisstopo.admin.ch/en/landscape-model-swisstlmregio).
     - In QGIS, filter `osm_roads.gpkg` for motorways (`fclass='motorway'`, `tunnel='F'`) to create `data/processed/swiss_highways.gpkg`.
     - Join lane widths from `lane_data.gpkg` to `swiss_highways.gpkg` using QGIS "Join attributes by nearest."
     - Buffer roads by lane count (e.g., 3.5m per lane) to create `data/processed/buffered_roads.gpkg`.
   - **Output**: Place `osm_roads.gpkg` and `lane_data.gpkg` in `data/raw/`, and `swiss_highways.gpkg` and `buffered_roads.gpkg` in `data/processed/`.
   - **Example**: See [docs/images/road_buffering_example.png](docs/images/road_buffering_example.png) for a visualization of buffered roads.


2. **Geometry Filtering**:
   - Filter `buffered_roads.gpkg` for obstructions (e.g., railways, other roads).
   ```bash
   python src/run.py --mask-filter
   ```
   - **Example**: [docs/images/mask_filter_example.png](docs/images/mask_filter_example.png).

3. **Imagery Download**:
   - Download 1km x 1km imagery for road segments that intersect the region of interest (ROI) road buffer. Only imagery covering intersecting features will be downloaded.
   ```bash
   python src/run.py --download-images
   ```


4. **Tiling**:
   - Tile roads into 5m x 5m segments from  created road segments 
   ```bash
   python src/run.py --crop-and-tile
   ```

5. **Tile Selection**:
   - Select ~30,000 tiles for labeling, convert to JPEGs.
   ```bash
   python src/run.py --select-tiles
   ```
5. **Annotate Selection**: Annotate selected samples  JPEGs from `output/tiles/tolabel/`  in [CrowdMap](https://crowdmap.heigit.org/)  and put the images in `data/processed/labelled_dataset/{crack,no_crack}/`.


6. **Dataset Preparation**:
   - Split data (80% train, 10% val, 10% test), augment train/crack images → `output/dataset/`.
   ```bash
   python src/run.py --split-augment
   ```

7. **Model Training**:
   - Train YOLOv11 (epochs=500, imgsz=64, batch=128).
   ```bash
   python src/run.py --train-model
   ```


8. **Model Evaluation**:
   | Set        | Class     | Precision | Recall | F1   |
   |------------|-----------|-----------|--------|------|
   | Validation | Crack     | 0.82      | 0.86   | 0.84 |
   | Test       | Crack     | 0.82      | 0.86   | 0.84 |
   | Validation | No Crack  | 0.98      | 0.96   | 0.97 |
   | Test       | No Crack  | 0.98      | 0.96   | 0.97 |
   - Generate Grad-CAM visualizations → `output/visualizations/gradcam/`.
   ```bash
   python src/run.py --evaluate-predict
   python src/run.py --gradcam
   ```
   - **Example**: [docs/images/gradcam_results.png](docs/images/gradcam_results.png).

9. **Large-Scale Prediction**:
    - Predict on all tiles, update as geopacakge.
   ```bash
   python src/run.py --evaluate-predict
   ```

10. **Correlation Analysis**:
    - Correlate predictions to get RHCD with trafic volume and LT-LST-A 
    - Generate plots
    ```bash
    python src/run.py --plot-correlations
    ```
    - **Examples**: [docs/images/traffic_vs_crack_plot.png](docs/images/traffic_vs_crack_plot.png), [docs/images/lst_vs_crack_plot.png](docs/images/lst_vs_crack_plot.png).

## Data and Privacy

Uses open-source data from Geofabrik, swissTLMRegio, Swiss Geo API, traffic and Surface Temperature (ST)  data (see [data/README.md](data/README.md)).

## License

This project is licensed under the MIT License. See [LICENSE](LICENSE) for details.
