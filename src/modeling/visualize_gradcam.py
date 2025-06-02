import sys
import os
import random
from pathlib import Path
import logging

import cv2
import numpy as np
import torch
from ultralytics import YOLO
from pytorch_grad_cam import GradCAM, GuidedBackpropReLUModel
from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget
from pytorch_grad_cam.utils.image import show_cam_on_image, deprocess_image

# Add root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.util.config import OUTPUT_DIR

# Minimal logging with timestamp
current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S %Z")
logging.basicConfig(level=logging.INFO, format=f'%(asctime)s - {current_time} - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class YOLOWrapper(torch.nn.Module):
    def __init__(self, yolo_model):
        super().__init__()
        self.yolo_model = yolo_model

    def forward(self, x):
        out = self.yolo_model(x)
        return out[0]

def combine_visualizations(cam_image, gb_image, cam_gb_image):
    """Combine three images side by side into a single image."""
    return np.concatenate((cam_image, gb_image, cam_gb_image), axis=1)

def generate_gradcam_visualizations(
    n_jobs=3,
    model_path=str(OUTPUT_DIR / "models/train/weights/best.pt"),
    input_dir=str(OUTPUT_DIR / "dataset/test/crack"),
    output_dir=str(OUTPUT_DIR / "visualizations/gradcam")
):
    """Generate Grad-CAM visualizations for n random images."""
    logger.info(f"Starting Grad-CAM for {model_path}")

    model = YOLO(model_path).model
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    model.to(device).eval()

    wrapped_model = YOLOWrapper(model)
    gb_model = GuidedBackpropReLUModel(model=wrapped_model, device=device)
    target_layers = [model.model[8]]  # Adjust if necessary
    classes = [0, 1]

    image_folder = Path(image_folder)
    output_folder = Path(output_folder)
    output_folder.mkdir(parents=True, exist_ok=True)

    all_images = list(image_folder.glob("*.tif"))
    if not all_images:
        logger.error(f"No images found in {image_folder}")
        return

    selected_images = random.sample(all_images, min(n, len(all_images)))

    for image_path in selected_images:
        try:
            img = cv2.imread(str(image_path))
            img = cv2.resize(img, (64, 64))
            rgb_img = img.copy()
            img = np.float32(img) / 255
            input_tensor = torch.from_numpy(img).permute(2, 0, 1).unsqueeze(0).to(device)
            input_tensor.requires_grad_(True)

            for class_id in classes:
                targets = [ClassifierOutputTarget(class_id)]
                with GradCAM(model=wrapped_model, target_layers=target_layers, use_cuda=(device == 'cuda')) as cam:
                    grayscale_cam = cam(input_tensor=input_tensor, targets=targets)[0, :]

                cam_image = show_cam_on_image(img, grayscale_cam, use_rgb=True)
                gb = gb_model(input_tensor, target_category=class_id)
                cam_mask = np.stack([grayscale_cam] * 3, axis=-1)
                cam_gb = deprocess_image(cam_mask * gb)
                gb_vis = deprocess_image(gb)

                combined = combine_visualizations(cam_image, gb_vis, cam_gb)
                output_file = output_folder / f"{image_path.stem}_class_{class_id}_cam.png"
                cv2.imwrite(str(output_file), cv2.cvtColor(combined, cv2.COLOR_RGB2BGR))
        except Exception as e:
            logger.error(f"Failed to process {image_path.name}: {e}")

    logger.info("Grad-CAM process completed")

if __name__ == "__main__":
    generate_gradcam_visualizations(n=3)
