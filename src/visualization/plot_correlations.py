import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import geopandas as gpd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import MinMaxScaler
from tqdm import tqdm
import logging
from datetime import datetime
from src.util.config import *

# Minimal logging with timestamp
current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z")
logging.basicConfig(level=logging.INFO, format=f'%(asctime)s - {current_time} - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def process_crack_analysis(input_path, predicted_tiles_path, output_path, id_column='tile_id'):
    logger.info(f"Processing {input_path}")
    try:
        input_gdf = gpd.read_file(input_path)
        predicted_tiles = gpd.read_file(predicted_tiles_path)
        if input_gdf.empty or predicted_tiles.empty:
            logger.error("Input or predicted tiles GeoPackage is empty")
            raise ValueError
        if predicted_tiles.crs != input_gdf.crs:
            predicted_tiles = predicted_tiles.to_crs(input_gdf.crs)
    except Exception as e:
        logger.error(f"Failed to read input files: {e}")
        raise

    for col in ["crack_count", "nocrack_count", "total_images", "rhcd", "max_overlap_feature", "max_overlap_area"]:
        input_gdf[col] = 0 if 'count' in col or col == 'total_images' else None

    assigned_tiles = set()
    for idx, feature in tqdm(input_gdf.iterrows(), total=len(input_gdf), desc="Processing"):
        unassigned = predicted_tiles[~predicted_tiles.index.isin(assigned_tiles)]
        intersecting = unassigned[unassigned.intersects(feature.geometry)]
        if intersecting.empty:
            continue
        crack_count = (intersecting["predicted_class"] == 0).sum()
        nocrack_count = (intersecting["predicted_class"] == 1).sum()
        total = len(intersecting)
        rhcd = crack_count / total if total > 0 else 0.0
        input_gdf.at[idx, "crack_count"] = crack_count
        input_gdf.at[idx, "nocrack_count"] = nocrack_count
        input_gdf.at[idx, "total_images"] = total
        input_gdf.at[idx, "rhcd"] = rhcd
        intersecting = intersecting.copy()
        intersecting["intersection_area"] = intersecting.geometry.intersection(feature.geometry).area
        max_overlap = intersecting.loc[intersecting["intersection_area"].idxmax()]
        input_gdf.at[idx, "max_overlap_feature"] = max_overlap.get(id_column)
        input_gdf.at[idx, "max_overlap_area"] = max_overlap["intersection_area"]
        assigned_tiles.update(intersecting.index)

    try:
        input_gdf.to_file(output_path, driver="GPKG")
        logger.info(f"Saved to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save {output_path}: {e}")
        raise
    return input_gdf

def plot_and_save_relationship(gdf, x_col, y_col, x_label, y_label, title_prefix, output_path):
    logger.info(f"Plotting {x_col} vs {y_col}")
    try:
        scaler = MinMaxScaler()
        gdf[[f'{x_col}_norm', f'{y_col}_norm']] = scaler.fit_transform(gdf[[x_col, y_col]])
        corr = gdf[[x_col, y_col]].corr().iloc[0, 1]
        fig, ax = plt.subplots(figsize=(8, 6))
        sns.scatterplot(x=f'{x_col}_norm', y=f'{y_col}_norm', data=gdf, color='red', alpha=0.2, s=10, ax=ax)
        sns.regplot(x=f'{x_col}_norm', y=f'{y_col}_norm', data=gdf, lowess=True, scatter=False, line_kws={'color': 'black'}, ax=ax)
        ax.set_xlabel(f'Normalized {x_label}', fontsize=16)
        ax.set_ylabel(f'Normalized {y_label}', fontsize=16)
        ax.tick_params(labelsize=14)
        ax.text(0.95, 0.95, f"Pearson's r: {corr:.2f}", transform=ax.transAxes, fontsize=14,
                ha='right', va='top', bbox=dict(facecolor='white', alpha=0.5, edgecolor='black'))
        plt.tight_layout()
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        plt.savefig(output_path, dpi=300, transparent=True)
        plt.close()
    except Exception as e:
        logger.error(f"Failed to generate plot: {e}")
        raise

def main():
    logger.info("Starting correlation analysis")
    trafficflow_gdf = process_crack_analysis(
        input_path=PROCESSED_DIR / "traffic_volume.gpkg",
        predicted_tiles_path=GEODATA_DIR / "tiled_gdf_with_predictions.gpkg",
        output_path=GEODATA_DIR / "traffic_with_rhcd.gpkg"
    )

    lst_gdf = process_crack_analysis(
        input_path=PROCESSED_DIR / "LTLST.gpkg",
        predicted_tiles_path=GEODATA_DIR / "tiled_gdf_with_predictions.gpkg",
        output_path=GEODATA_DIR / "LTLST_with_rhcd.gpkg"
    )

    plot_and_save_relationship(
        gdf=trafficflow_gdf,
        x_col='DTV_FZG',
        y_col='rhcd',
        x_label='Traffic Volume',
        y_label='Relative Highway Crack Density',
        title_prefix='Traffic_vs_Crack',
        output_path=OUTPUT_DIR / "visualizations/traffic_vs_crack.png"
    )

    plot_and_save_relationship(
        gdf=lst_gdf,
        x_col='Dif_max',
        y_col='rhcd',
        x_label=' LTLST',
        y_label='Relative Highway Crack Density',
        title_prefix='LTLST_vs_Crack',
        output_path=OUTPUT_DIR / "visualizations/LTLST_vs_crack.png"
    )

    logger.info("Correlation analysis completed")

if __name__ == "__main__":
    main()
