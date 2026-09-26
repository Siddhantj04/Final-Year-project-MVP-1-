import json

import cv2
import numpy as np
from PIL import Image

from app.models.entities import QualityStatus


def _load_bgr(path: str) -> np.ndarray | None:
    img = cv2.imread(path, cv2.IMREAD_COLOR)
    return img


def check_image_quality(path: str) -> dict:
    img = _load_bgr(path)
    if img is None:
        return {
            "suitability": QualityStatus.unsuitable.value,
            "blur_variance": 0.0,
            "brightness_mean": 0.0,
            "contrast_std": 0.0,
            "width": 0,
            "height": 0,
            "messages": ["Unable to read image file."],
        }

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]
    blur_var = float(cv2.Laplacian(gray, cv2.CV_64F).var())
    brightness = float(np.mean(gray))
    contrast = float(np.std(gray))

    messages: list[str] = []
    issues = 0
    borderline_flags = 0

    if w < 224 or h < 224:
        messages.append("Resolution is below 224×224 pixels.")
        issues += 1
    elif w < 512 or h < 512:
        messages.append("Resolution is below recommended 512×512 pixels.")
        borderline_flags += 1

    if blur_var < 50:
        messages.append("Image appears very blurry (low Laplacian variance).")
        issues += 1
    elif blur_var < 100:
        messages.append("Image may be slightly blurry.")
        borderline_flags += 1

    if brightness < 40:
        messages.append("Image is very dark.")
        issues += 1
    elif brightness < 70:
        messages.append("Image brightness is low.")
        borderline_flags += 1
    elif brightness > 220:
        messages.append("Image is very bright or overexposed.")
        issues += 1
    elif brightness > 200:
        messages.append("Image brightness is high.")
        borderline_flags += 1

    if contrast < 25:
        messages.append("Image contrast is very low.")
        issues += 1
    elif contrast < 40:
        messages.append("Image contrast is low.")
        borderline_flags += 1

    try:
        with Image.open(path) as pil_img:
            pil_img.verify()
    except Exception:
        messages.append("Image failed integrity verification.")
        issues += 1

    if issues > 0:
        suitability = QualityStatus.unsuitable
    elif borderline_flags > 0:
        suitability = QualityStatus.borderline
    else:
        suitability = QualityStatus.suitable
        messages.append("Image passed quality checks.")

    return {
        "suitability": suitability.value,
        "blur_variance": round(blur_var, 2),
        "brightness_mean": round(brightness, 2),
        "contrast_std": round(contrast, 2),
        "width": w,
        "height": h,
        "messages": messages,
    }


def quality_details_to_json(details: dict) -> str:
    return json.dumps(details)
