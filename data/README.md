<!-- Data readme.md -->
# Data Directory

Contains raw and processed datasets for the Swiss Crack project. See the [root README](../README.md) for the overall workflow.



## Subdirectories

- **raw/**:
  - `osm_roads.gpkg`: OSM road data from [Geofabrik](https://download.geofabrik.de/europe/switzerland.html). Contains motorway geometries (`fclass='motorway'`).
  - `osm_railways.gpkg`: OSM railway data for geometry filtering.
  - `lane_data.gpkg`: Lane data from [swissTLMRegio](https://www.swisstopo.admin.ch/en/landscape-model-swisstlmregio), filtered for `Autobahn`.

- **processed/**:
  - `swiss_highways.gpkg`: Filtered OSM motorways (`fclass='motorway'`, `tunnel='F'`) from `raw/osm_roads.gpkg`.
  - `buffered_roads.gpkg`: Highways with lane widths joined from `raw/lane_data.gpkg` and buffered (by lane width).
  - `labelled_dataset/`: CrowdMap-annotated tiles. can be found [here](https://heibox.uni-heidelberg.de/f/a6e48113d2b64a4d82e2/),
    - `crack/`: JPEG tiles annotated as cracks
    - `no_crack/`: JPEGs tiles annotated as no cracks
  - `traffic_volume.gpkg`: Traffic data (2017) from [OpenData Swiss](https://opendata.swiss), with `DTV_FZG` for vehicle volume.
  - `LTLST.gpkg`: Land Surface Temperature anomalies (2021–2023) from Google Earth Engine (see [docs/README.md](../docs/README.md#long-term-land-surface-temperature-anomalies))., with `Dif_max` for LTLST value per  30m grids.