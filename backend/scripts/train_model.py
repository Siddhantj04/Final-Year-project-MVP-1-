"""
Train DenseNet121 binary classifier on RSNA Pneumonia Detection Challenge data.

Expected layout:
  RSNA_ROOT/
    stage_2_train_images/   (*.dcm or *.png)
    stage_2_train_labels.csv  (patientId, Target)

Patient-level split: 70% train, 15% val, 15% test (no patient in multiple splits).
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from PIL import Image
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.services.ml_inference import IMAGENET_MEAN, IMAGENET_STD, build_model

try:
    import pydicom
except ImportError:
    pydicom = None


def load_image(path: Path) -> Image.Image:
    if path.suffix.lower() == ".dcm":
        if pydicom is None:
            raise RuntimeError("pydicom is required for DICOM files: pip install pydicom")
        ds = pydicom.dcmread(str(path))
        arr = ds.pixel_array.astype(np.float32)
        arr = (arr - arr.min()) / (arr.max() - arr.min() + 1e-8) * 255.0
        return Image.fromarray(arr.astype(np.uint8)).convert("RGB")
    img = Image.open(path)
    return img.convert("RGB")


class RSNADataset(Dataset):
    def __init__(self, rows: pd.DataFrame, image_dir: Path, transform):
        self.rows = rows.reset_index(drop=True)
        self.image_dir = image_dir
        self.transform = transform

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, idx):
        row = self.rows.iloc[idx]
        pid = row["patientId"]
        label = int(row["Target"])
        for ext in (".dcm", ".png", ".jpg"):
            p = self.image_dir / f"{pid}{ext}"
            if p.is_file():
                img = load_image(p)
                break
        else:
            raise FileNotFoundError(f"No image for patient {pid}")
        if self.transform:
            img = self.transform(img)
        return img, label


def patient_split(df: pd.DataFrame, seed: int = 42):
    rng = np.random.default_rng(seed)
    patients = df["patientId"].unique()
    rng.shuffle(patients)
    n = len(patients)
    n_train = int(0.7 * n)
    n_val = int(0.15 * n)
    train_p = set(patients[:n_train])
    val_p = set(patients[n_train : n_train + n_val])
    test_p = set(patients[n_train + n_val :])
    return (
        df[df["patientId"].isin(train_p)],
        df[df["patientId"].isin(val_p)],
        df[df["patientId"].isin(test_p)],
    )


def get_transforms(train: bool):
    base = [
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
    ]
    if train:
        return transforms.Compose(
            [
                transforms.Resize((224, 224)),
                transforms.RandomRotation(7),
                transforms.ColorJitter(brightness=0.1, contrast=0.1),
                transforms.ToTensor(),
                transforms.Normalize(mean=IMAGENET_MEAN, std=IMAGENET_STD),
            ]
        )
    return transforms.Compose(base)


def specificity_score(y_true, y_pred):
    tn, fp, fn, tp = confusion_matrix(y_true, y_pred).ravel()
    return tn / (tn + fp + 1e-8)


def train_epoch(model, loader, criterion, optimizer, device):
    model.train()
    total_loss = 0.0
    for x, y in loader:
        x, y = x.to(device), y.to(device)
        optimizer.zero_grad()
        out = model(x)
        loss = criterion(out, y)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * x.size(0)
    return total_loss / len(loader.dataset)


@torch.no_grad()
def evaluate(model, loader, device):
    model.eval()
    ys, preds, probs = [], [], []
    for x, y in loader:
        x = x.to(device)
        logits = model(x)
        p = torch.softmax(logits, dim=1)[:, 1].cpu().numpy()
        pred = logits.argmax(dim=1).cpu().numpy()
        ys.extend(y.numpy())
        preds.extend(pred)
        probs.extend(p)
    return np.array(ys), np.array(preds), np.array(probs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--rsna-root", type=str, required=True)
    parser.add_argument("--output-dir", type=str, default="./models")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--lr", type=float, default=1e-4)
    parser.add_argument("--epochs", type=int, default=20)
    parser.add_argument("--patience", type=int, default=5)
    args = parser.parse_args()

    root = Path(args.rsna_root)
    labels_path = root / "stage_2_train_labels.csv"
    image_dir = root / "stage_2_train_images"
    if not labels_path.is_file():
        raise SystemExit(f"Missing {labels_path}")

    df = pd.read_csv(labels_path)
    train_df, val_df, test_df = patient_split(df)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    train_loader = DataLoader(
        RSNADataset(train_df, image_dir, get_transforms(True)),
        batch_size=args.batch_size,
        shuffle=True,
        num_workers=2,
    )
    val_loader = DataLoader(
        RSNADataset(val_df, image_dir, get_transforms(False)),
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=2,
    )
    test_loader = DataLoader(
        RSNADataset(test_df, image_dir, get_transforms(False)),
        batch_size=args.batch_size,
        shuffle=False,
        num_workers=2,
    )

    counts = train_df["Target"].value_counts().to_dict()
    total = sum(counts.values())
    w0 = total / (2 * counts.get(0, 1))
    w1 = total / (2 * counts.get(1, 1))
    class_weights = torch.tensor([w0, w1], dtype=torch.float32, device=device)

    model = build_model().to(device)
    criterion = nn.CrossEntropyLoss(weight=class_weights)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr)

    best_f1 = -1.0
    best_state = None
    stale = 0
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    for epoch in range(1, args.epochs + 1):
        loss = train_epoch(model, train_loader, criterion, optimizer, device)
        y_true, y_pred, _ = evaluate(model, val_loader, device)
        vf1 = f1_score(y_true, y_pred, zero_division=0)
        print(f"Epoch {epoch}: train_loss={loss:.4f} val_f1={vf1:.4f}")
        if vf1 > best_f1:
            best_f1 = vf1
            best_state = model.state_dict()
            stale = 0
        else:
            stale += 1
            if stale >= args.patience:
                print("Early stopping.")
                break

    if best_state:
        model.load_state_dict(best_state)

    ckpt_path = out_dir / "best_model.pt"
    torch.save({"model_state_dict": model.state_dict(), "best_val_f1": best_f1}, ckpt_path)

    y_true, y_pred, y_prob = evaluate(model, test_loader, device)
    cm = confusion_matrix(y_true, y_pred).tolist()
    metrics = {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "precision": float(precision_score(y_true, y_pred, zero_division=0)),
        "recall": float(recall_score(y_true, y_pred, zero_division=0)),
        "specificity": float(specificity_score(y_true, y_pred)),
        "f1_score": float(f1_score(y_true, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_true, y_prob)) if len(np.unique(y_true)) > 1 else 0.0,
        "confusion_matrix": cm,
    }
    metrics_path = out_dir / "metrics.json"
    metrics_path.write_text(json.dumps(metrics, indent=2), encoding="utf-8")
    print(json.dumps(metrics, indent=2))
    print(f"Saved checkpoint to {ckpt_path}")


if __name__ == "__main__":
    main()
