import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import cv2
import numpy as np
import geopandas as gpd
import pandas as pd
from tqdm import tqdm
from ultralytics import YOLO
from sklearn.metrics import classification_report
from pathlib import Path
import logging
from src.utils.config import *

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def evaluate_folder(model, folder_path, label_map):
    true_labels = []
    pred_labels = []
    logger.info(f"Evaluating {folder_path}")
    for class_name, class_index in label_map.items():
        class_folder = folder_path / class_name
        if not class_folder.exists():
            continue
        for image_path in class_folder.glob("*.jpg"):
            try:
                results = model.predict(image_path, save=False, verbose=False)
                pred_index = int(results[0].probs.top1)
                true_labels.append(class_index)
                pred_labels.append(pred_index)
            except Exception as e:
                logger.error(f"Error processing {image_path}: {e}")
    return true_labels, pred_labels

def print_metrics(true_labels, pred_labels, label_map):
    if not true_labels:
        logger.error("No labels to compute metrics")
        return
    try:
        report = classification_report(true_labels, pred_labels, target_names=list(label_map.keys()), digits=2)
        logger.info(f"\nClassification Report:\n{report}")
    except Exception as e:
        logger.error(f"Error computing metrics: {e}")

def evaluate_split_and_update_gdf(model, split_path, split_name, gdf, filecolumn='tile_id', label_map=None):
    logger.info(f"Evaluating {split_name} split")
    try:
        results = model.predict(source=split_path, save=False, verbose=False)
    except Exception as e:
        logger.error(f"Failed to predict on {split_path}: {e}")
        return gdf

    predictions = []
    targets = []
    filenames = []
    for r in results:
        try:
            pred_class = int(r.probs.top1)
            folder_name = Path(r.path).parent.name
            true_class = label_map.get(folder_name, -1)
            if true_class == -1:
                continue
            filenames.append(Path(r.path).name)
            predictions.append(pred_class)
            targets.append(true_class)
        except Exception as e:
            logger.error(f"Error processing {r.path}: {e}")

    df = pd.DataFrame({filecolumn: filenames, 'true_label': targets, 'pred_label': predictions})
    df['result'] = df.apply(
        lambda row: 'TP' if row['true_label'] == row['pred_label'] == 0 else
                    'FP' if row['true_label'] == 1 and row['pred_label'] == 0 else
                    'FN' if row['true_label'] == 0 and row['pred_label'] == 1 else
                    'TN' if row['true_label'] == row['pred_label'] == 1 else 'Unknown',
        axis=1
    )
    gdf = gdf.merge(df[[filecolumn, 'result']], on=filecolumn, how='left')
    gdf[f'yolo_result_{split_name}'] = gdf['result']
    gdf = gdf.drop(columns=['result'], errors='ignore')
    return gdf

def predict_gdf(model, gdf_path, image_folder, label_map, output_path):
    logger.info(f"Starting prediction for {gdf_path}")
    try:
        gdf = gpd.read_file(gdf_path)
    except Exception as e:
        logger.error(f"Failed to read {gdf_path}: {e}")
        raise

    for col in ["predicted_class", "predicted_label", "top1_conf", "top5_0_index", "top5_0_conf",
                "top5_1_index", "top5_1_conf", "yolo_result_val", "yolo_result_test"]:
        if col not in gdf.columns:
            gdf[col] = None

    for idx, row in tqdm(gdf.iterrows(), total=len(gdf), desc="Predicting"):
        image_name = f"{row['tile_id']}.jpg"
        image_path = image_folder / image_name

        if not image_path.exists():
            continue

        try:
            results = model.predict(image_path, save=False, verbose=False)
            probs = results[0].probs
            gdf.at[idx, "predicted_class"] = int(probs.top1)
            gdf.at[idx, "predicted_label"] = list(label_map.keys())[int(probs.top1)]
            gdf.at[idx, "top1_conf"] = round(float(probs.top1conf), 6)
            top5_indices = probs.top5
            top5_conf = probs.top5conf
            gdf.at[idx, "top5_0_index"] = int(top5_indices[0])
            gdf.at[idx, "top5_0_conf"] = round(float(top5_conf[0]), 6)
            gdf.at[idx, "top5_1_index"] = int(top5_indices[1])
            gdf.at[idx, "top5_1_conf"] = round(float(top5_conf[1]), 6)
        except Exception as e:
            logger.error(f"Error processing {image_name}: {e}")

    try:
        gdf.to_file(output_path, driver="GPKG")
        logger.info(f"Saved to {output_path}")
    except Exception as e:
        logger.error(f"Failed to save {output_path}: {e}")
        raise
    return gdf

def main():
    model_path = OUTPUT_DIR / "models/train/weights/best.pt"
    dataset_path = OUTPUT_DIR / "dataset"
    gdf_path = GEODATA_DIR / "tiles.gpkg"
    image_folder = TOLABEL_DIR
    output_path = GEODATA_DIR / "tiled_gdf_with_predictions.gpkg"
    label_map = {"crack": 0, "no_crack": 1}

    logger.info(f"Starting evaluation and prediction with {model_path}")
    try:
        model = YOLO(model_path)
    except Exception as e:
        logger.error(f"Failed to load model: {e}")
        raise

    val_true, val_pred = evaluate_folder(model, dataset_path / "val", label_map)
    print_metrics(val_true, val_pred, label_map)

    test_true, test_pred = evaluate_folder(model, dataset_path / "test", label_map)
    print_metrics(test_true, test_pred, label_map)

    try:
        gdf = gpd.read_file(gdf_path)
    except Exception as e:
        logger.error(f"Failed to read {gdf_path}: {e}")
        raise

    gdf = evaluate_split_and_update_gdf(model, dataset_path / "val", 'val', gdf, label_map=label_map)
    gdf = evaluate_split_and_update_gdf(model, dataset_path / "test", 'test', gdf, label_map=label_map)
    predict_gdf(model, gdf_path, image_folder, label_map, output_path)

    logger.info("Evaluation and prediction completed")

if __name__ == "__main__":
    main()
