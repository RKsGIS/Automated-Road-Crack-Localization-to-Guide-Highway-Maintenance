
import argparse
import os
from data_retrieval.mask_filter import filter_roads
from data_retrieval.download_images import download_images
from data_retrieval.crop_and_tile import crop_and_tile
from dataset.select_labeling_data import select_labeling_data
from dataset.split_and_augment import split_and_augment
from modeling.train_model import train_model
from modeling.evaluate_and_predict import evaluate_and_predict
from modeling.visualize_gradcam import visualize_gradcam
from visualization.plot_correlations import plot_correlations
from utils.create_zip_archives import create_zip_archives
from utils.config import DEFAULT_ROAD_FILEPATH

def main():
    parser = argparse.ArgumentParser(description="Swiss Crack Pipeline")
    parser.add_argument("--mask-filter", action="store_true", help="Filter road geometries")
    parser.add_argument("--download-images", action="store_true", help="Download imagery")
    parser.add_argument("--crop-and-tile", action="store_true", help="Crop and tile imagery")
    parser.add_argument("--select-tiles", action="store_true", help="Select tiles for labeling")
    parser.add_argument("--split-augment", action="store_true", help="Split and augment dataset")
    parser.add_argument("--train-model", action="store_true", help="Train YOLOv11 model")
    parser.add_argument("--evaluate-predict", action="store_true", help="Evaluate and predict")
    parser.add_argument("--gradcam", action="store_true", help="Generate Grad-CAM visualizations")
    parser.add_argument("--plot-correlations", action="store_true", help="Plot correlations")
    parser.add_argument("--create-archives", action="store_true", help="Create ZIP archives")
    parser.add_argument("--all", action="store_true", help="Run all tasks")
    parser.add_argument("--roads-filepath", default=DEFAULT_ROAD_FILEPATH, help="Path to roads GeoPackage")
    parser.add_argument("--n", type=int, default=3, help="Number of Grad-CAM images")

    args = parser.parse_args()

    if not any([args.mask_filter, args.download_images, args.crop_and_tile, args.select_tiles,
                args.split_augment, args.train_model, args.evaluate_predict, args.gradcam,
                args.plot_correlations, args.create_archives, args.all]):
        parser.print_help()
        return

    if args.all or args.mask_filter:
        print("Running mask_filter...")
        filter_roads(args.roads_filepath)

    if args.all or args.download_images:
        print("Running download_images...")
        download_images(args.roads_filepath)

    if args.all or args.crop_and_tile:
        print("Running crop_and_tile...")
        crop_and_tile(args.roads_filepath)

    if args.all or args.select_tiles:
        print("Running select_labeling_data...")
        select_labeling_data()

    if args.all or args.split_augment:
        print("Running split_and_augment...")
        split_and_augment()

    if args.all or args.train_model:
        print("Running train_model...")
        train_model()

    if args.all or args.evaluate_predict:
        print("Running evaluate_and_predict...")
        evaluate_and_predict()

    if args.all or args.gradcam:
        print("Running visualize_gradcam...")
        visualize_gradcam(n=args.n)

    if args.all or args.plot_correlations:
        print("Running plot_correlations...")
        plot_correlations()

    if args.all or args.create_archives:
        print("Running create_zip_archives...")
        create_zip_archives()

if __name__ == "__main__":
    main()
