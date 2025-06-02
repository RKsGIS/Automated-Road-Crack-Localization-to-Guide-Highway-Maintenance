import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import geopandas as gpd
import pandas as pd
from shapely.ops import unary_union
from tqdm import tqdm
from pathlib import Path
import logging
from datetime import datetime
from src.utils.config import DEFAULT_ROAD_FILEPATH, RAILWAY_FILEPATH, ROADS_FILEPATH

# Minimal logging with timestamp
current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z")
logging.basicConfig(level=logging.INFO, format=f'%(asctime)s - {current_time} - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

tqdm.pandas()

def update_geometry_based_on_layer(target_layer: gpd.GeoDataFrame, ref_layer: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    """
    Update geometries in `target_layer` based on `ref_layer` and layer hierarchy.
    Higher layers override lower layers. Can work with same or different layers.

    Args:
        target_layer (GeoDataFrame): Layer to be updated.
        ref_layer (GeoDataFrame): Layer to check intersections against.

    Returns:
        GeoDataFrame: Updated layer with `final_geometry`.
    """
    target_layer = target_layer.copy()
    ref_layer = ref_layer.copy()
    ref_sindex = ref_layer.sindex

    for i, row in tqdm(target_layer.iterrows(), total=len(target_layer), desc="Processing geometries"):
        geom = row['updated_geometry'] if pd.notnull(row['updated_geometry']) else row['geometry']
        layer = row['layer']

        possible_matches_index = list(ref_sindex.intersection(geom.bounds))
        possible_matches = ref_layer.iloc[possible_matches_index]

        higher_geoms = []
        for j, ref_row in possible_matches.iterrows():
            if target_layer is ref_layer and i == j:
                continue

            ref_geom = ref_row['updated_geometry'] if pd.notnull(ref_row['updated_geometry']) else ref_row['geometry']
            ref_layer_val = ref_row['layer']

            if not geom.intersects(ref_geom):
                continue

            if ref_layer_val > layer:
                higher_geoms.append(ref_geom)
            elif ref_layer_val < layer and target_layer is not ref_layer:
                current_updated = ref_row['updated_geometry'] if pd.notnull(ref_row['updated_geometry']) else ref_row['geometry']
                new_geom = current_updated.difference(geom)
                if not new_geom.is_empty:
                    ref_layer.at[j, 'updated_geometry'] = new_geom

        if higher_geoms:
            union_high = unary_union(higher_geoms)
            new_geom = geom.difference(union_high)
            if not new_geom.is_empty:
                target_layer.at[i, 'updated_geometry'] = new_geom

    target_layer['final_geometry'] = target_layer.apply(
        lambda row: row['updated_geometry'] if pd.notnull(row['updated_geometry']) else row['geometry'],
        axis=1
    )

    target_layer = target_layer.drop(columns=['geometry'], errors='ignore')
    target_layer = target_layer.set_geometry('final_geometry')

    return target_layer

def mask_filter(
    roads_filepath=str(DEFAULT_ROAD_FILEPATH),
    railway_filepath=str(RAILWAY_FILEPATH),
    osm_roads_filepath=str(ROADS_FILEPATH),
    output_filepath=str(DEFAULT_ROAD_FILEPATH)
):
    """Update road geometries using railways and other roads."""
    logger.info(f"Starting geometry update for {roads_filepath}")

    try:
        gdf = gpd.read_file(roads_filepath)
        if gdf.crs != "EPSG:2056":
            gdf = gdf.to_crs(epsg=2056)
    except Exception as e:
        logger.error(f"Failed to read {roads_filepath}: {e}")
        raise

    try:
        railway = gpd.read_file(railway_filepath)
        roads = gpd.read_file(osm_roads_filepath)
    except Exception as e:
        logger.error(f"Failed to read external layers: {e}")
        raise

    nonmotorway_tunnels = roads[(roads['fclass'] == 'motorway') & (roads['tunnel'] == 'F')]
    external_layer = pd.concat([railway, nonmotorway_tunnels], ignore_index=True)

    if external_layer.crs != gdf.crs:
        external_layer = external_layer.to_crs(epsg=2056)

    gdf = update_geometry_based_on_layer(gdf, gdf)
    gdf = update_geometry_based_on_layer(gdf, external_layer)

    try:
        output_filepath.parent.mkdir(parents=True, exist_ok=True)
        gdf.to_file(output_filepath, driver="GPKG")
        logger.info(f"Updated roads saved to {output_filepath}")
    except Exception as e:
        logger.error(f"Failed to save {output_filepath}: {e}")
        raise

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Update road geometries for Swiss Crack pipeline.")
    parser.add_argument("--roads-filepath", type=str, default=str(DEFAULT_ROAD_FILEPATH),
                        help="Path to roads GeoPackage (default: data/processed/buffered_roads.gpkg).")
    parser.add_argument("--railway-filepath", type=str, default=str(RAILWAY_FILEPATH),
                        help="Path to railway shapefile (default: data/raw/osm_railways.shp).")
    parser.add_argument("--osm-roads-filepath", type=str, default=str(ROADS_FILEPATH),
                        help="Path to OSM roads shapefile (default: data/raw/osm_roads.shp).")
    parser.add_argument("--output-filepath", type=str, default=str(DEFAULT_ROAD_FILEPATH),
                        help="Path to save updated roads GeoPackage (default: data/processed/buffered_roads.gpkg).")
    args = parser.parse_args()
    mask_filter(
        roads_filepath=args.roads_filepath,
        railway_filepath=args.railway_filepath,
        osm_roads_filepath=args.osm_roads_filepath,
        output_filepath=args.output_filepath
    )