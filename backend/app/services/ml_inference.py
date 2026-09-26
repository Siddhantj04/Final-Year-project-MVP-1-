import os
from pathlib import Path

import cv2
import numpy as np
import torch
import torch.nn as nn
from PIL import Image
from pytorch_grad_cam import GradCAM
from pytorch_grad_cam.utils.image import show_cam_on_image
from pytorch_grad_cam.utils.model_targets import ClassifierOutputTarget
from torchvision import models, transforms

from app.config import get_settings

CLASS_NAMES = ["normal_like", "pneumonia_like"]
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]

_model: nn.Module | None = None
_device: torch.device | None = None


def _get_device() -> torch.device:
    global _device
    if _device is None:
        _device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return _device


def build_model(num_classes: int = 2) -> nn.Module:
    weights = models.DenseNet121_Weights.IMAGENET1K_V1
    model = models.densenet121(weights=weights)
    in_features = model.classifier.in_features
    model.classifier = nn.Linear(in_features, num_classes)
    return model


def load_model() -> nn.Module:
    global _model
    if _model is not None:
        return _model
    settings = get_settings()
    device = _get_device()
    model = build_model()
    path = Path(settings.model_checkpoint_path)
    if path.is_file():
        state = torch.load(path, map_location=device, weights_only=True)
        if isinstance(state, dict) and "model_state_dict" in state:
            model.load_state_dict(state["model_state_dict"])
        else:
            model.load_state_dict(state)
    else:
        os.makedirs(path.parent, exist_ok=True)
    model.eval()
    model.to(device)
    _model = model
    return model


def get_preprocess_transform():
    return transforms.Compose(
        [
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
        ]
    )


def predict_and_gradcam(image_path: str, heatmap_out_path: str) -> tuple[str, float]:
    model = load_model()
    device = _get_device()
    transform = get_preprocess_transform()

    pil_rgb = Image.open(image_path).convert("RGB")
    pil_rgb = pil_rgb.resize((224, 224))
    tensor = transform(pil_rgb).unsqueeze(0).to(device)

    with torch.no_grad():
        logits = model(tensor)
        probs = torch.softmax(logits, dim=1)[0]
        conf, pred_idx = torch.max(probs, dim=0)
        predicted_class = CLASS_NAMES[int(pred_idx.item())]
        confidence = float(conf.item())

    target_layers = [model.features.denseblock4.denselayer16.conv2]
    cam = GradCAM(model=model, target_layers=target_layers)

    rgb_float = np.array(pil_rgb, dtype=np.float32) / 255.0
    targets = [ClassifierOutputTarget(int(pred_idx.item()))]
    grayscale_cam = cam(input_tensor=tensor, targets=targets)[0, :]
    visualization = show_cam_on_image(rgb_float, grayscale_cam, use_rgb=True)
    visualization_bgr = cv2.cvtColor(visualization, cv2.COLOR_RGB2BGR)
    Path(heatmap_out_path).parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(heatmap_out_path, visualization_bgr)

    return predicted_class, confidence
