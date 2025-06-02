
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from ultralytics import YOLO
from ultralytics.data.dataset import ClassificationDataset
import ultralytics.models.yolo.classify.train as build
import numpy as np
import logging
from datetime import datetime
from src.util.config import OUTPUT_DIR

# Minimal logging with timestamp
current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z")
logging.basicConfig(level=logging.INFO, format=f'%(asctime)s - {current_time} - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class WeightedClassificationDataset(ClassificationDataset):
    def __init__(self, *args, mode='train', **kwargs):
        super().__init__(*args, **kwargs)
        self.train_mode = "train" in self.prefix
        self.count_instances()
        self.class_weights = np.sum(self.counts) / self.counts
        self.weights = self.calculate_weights()
        self.probabilities = self.calculate_probabilities()

    def count_instances(self):
        self.counts = [0 for _ in range(len(self.base.classes))]
        for _, class_idx, _, _ in self.samples:
            self.counts[class_idx] += 1
        self.counts = np.array(self.counts)
        self.counts = np.where(self.counts == 0, 1, self.counts)

    def calculate_weights(self):
        weights = []
        for _, class_idx, _, _ in self.samples:
            weight = self.class_weights[class_idx]
            weights.append(weight)
        return weights

    def calculate_probabilities(self):
        total_weight = sum(self.weights)
        probabilities = [w / total_weight for w in self.weights]
        return probabilities

    def __getitem__(self, index):
        if self.train_mode:
            index = np.random.choice(len(self.samples), p=self.probabilities)
        return super().__getitem__(index)

build.ClassificationDataset = WeightedClassificationDataset

def train_model():
    logger.info("Starting model training")
    model = YOLO("yolo11x-cls.pt")
    try:
        model.train(
            data=str(OUTPUT_DIR / "dataset"),
            epochs=500,
            imgsz=64,
            batch=128,
            project=str(OUTPUT_DIR / "models"),
            patience=100,
            save=True,
            cache=True,
            hsv_h=0.0,
            hsv_s=0.0,
            hsv_v=0.0,
            translate=0.0,
            scale=0.0,
            shear=0.0,
            fliplr=0.0,
            mosaic=0.0,
            copy_paste_mode=None,
            auto_augment=None,
            erasing=0.0,
            crop_fraction=1.0
        )
        logger.info("Training completed")
    except Exception as e:
        logger.error(f"Training failed: {e}")
        raise

if __name__ == "__main__":
    train_model()
