"""BountyLoop — EfficientNet-B0 Binary Freshness Training Script.

Trains on Kaggle 8-class collapsed to binary (fresh vs spoiled).
Uses:
- Pretrained EfficientNet-B0
- Data augmentation (RandomResizedCrop, RandomHorizontalFlip, ColorJitter)
- Label smoothing (0.1)
- AdamW + CosineAnnealingLR
- Early stopping on validation macro-F1
- Saves best.pt checkpoint and metrics.json
"""

from __future__ import annotations

import argparse
import csv
import logging
from pathlib import Path
from typing import Any

import numpy as np
import torch
from PIL import Image
from torch import nn
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms

from ml.src.models.baseline_freshness import FreshnessBaseline
from ml.src.training.evaluate import compute_metrics, save_metrics

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


class FreshnessCSVDataset(Dataset):
    """Dataset reading paths and labels from split CSV."""

    def __init__(self, csv_path: Path, data_root: Path, transform: Any = None) -> None:
        self.samples: list[dict[str, str]] = []
        self.data_root = data_root
        self.transform = transform
        self.label_map = {"fresh": 0, "spoiled": 1}

        with open(csv_path, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.samples.append(row)

    def __len__(self) -> int:
        return len(self.samples)

    def __getitem__(self, idx: int) -> tuple[torch.Tensor, int, str]:
        row = self.samples[idx]
        img_rel_path = row["image_path"]
        # Resolve path relative to data_root or workspace
        full_path = self.data_root / img_rel_path
        if not full_path.exists():
            full_path = Path(img_rel_path)

        with Image.open(full_path) as img:
            img = img.convert("RGB")

        if self.transform:
            tensor = self.transform(img)
        else:
            tensor = transforms.ToTensor()(img)

        label = self.label_map.get(row["freshness"], 0)
        category = row.get("item_family", "unknown")
        return tensor, label, category


def train_epoch(
    model: nn.Module,
    loader: DataLoader,
    optimizer: torch.optim.Optimizer,
    criterion: nn.Module,
    device: torch.device,
) -> float:
    """Train for one epoch."""
    model.train()
    total_loss = 0.0
    for inputs, targets, _ in loader:
        inputs, targets = inputs.to(device), targets.to(device)
        optimizer.zero_grad()
        outputs = model(inputs)
        loss = criterion(outputs, targets)
        loss.backward()
        optimizer.step()
        total_loss += loss.item() * inputs.size(0)
    return total_loss / len(loader.dataset)  # type: ignore


@torch.no_grad()
def evaluate_epoch(
    model: nn.Module,
    loader: DataLoader,
    device: torch.device,
) -> dict[str, Any]:
    """Evaluate model and return metrics dict."""
    model.eval()
    all_preds: list[int] = []
    all_targets: list[int] = []
    all_probs: list[list[float]] = []
    all_categories: list[str] = []

    for inputs, targets, categories in loader:
        inputs = inputs.to(device)
        outputs = model(inputs)
        probs = torch.softmax(outputs, dim=1).cpu().numpy()
        preds = np.argmax(probs, axis=1)

        all_preds.extend(preds.tolist())
        all_targets.extend(targets.tolist())
        all_probs.extend(probs.tolist())
        all_categories.extend(categories)

    metrics = compute_metrics(
        y_true=all_targets,
        y_pred=all_preds,
        y_probs=all_probs,
        class_names=["fresh", "spoiled"],
        metadata_categories=all_categories,
    )
    return metrics


def run_training(
    data_root: Path,
    splits_dir: Path,
    output_dir: Path,
    epochs: int = 10,
    batch_size: int = 32,
    learning_rate: float = 3e-4,
    device_name: str | None = None,
) -> Path:
    """Execute complete training pipeline and save best.pt and metrics.json."""
    if device_name:
        device = torch.device(device_name)
    else:
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    logger.info("Using device: %s", device)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Transforms
    train_transform = transforms.Compose(
        [
            transforms.RandomResizedCrop(224, scale=(0.8, 1.0)),
            transforms.RandomHorizontalFlip(),
            transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.2),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )

    val_transform = transforms.Compose(
        [
            transforms.Resize(256),
            transforms.CenterCrop(224),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
        ]
    )

    train_ds = FreshnessCSVDataset(
        splits_dir / "train.csv", data_root, transform=train_transform
    )
    val_ds = FreshnessCSVDataset(
        splits_dir / "val.csv", data_root, transform=val_transform
    )
    test_ds = FreshnessCSVDataset(
        splits_dir / "test.csv", data_root, transform=val_transform
    )

    train_loader = DataLoader(
        train_ds, batch_size=batch_size, shuffle=True, num_workers=2, pin_memory=True
    )
    val_loader = DataLoader(val_ds, batch_size=batch_size, shuffle=False, num_workers=2)
    test_loader = DataLoader(
        test_ds, batch_size=batch_size, shuffle=False, num_workers=2
    )

    logger.info(
        "Loaded datasets: %d train, %d val, %d test",
        len(train_ds),
        len(val_ds),
        len(test_ds),
    )

    model = FreshnessBaseline(pretrained=True).to(device)
    criterion = nn.CrossEntropyLoss(label_smoothing=0.1)
    optimizer = torch.optim.AdamW(
        model.parameters(), lr=learning_rate, weight_decay=1e-2
    )
    scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)

    best_val_f1 = -1.0
    best_ckpt_path = output_dir / "best.pt"

    for epoch in range(1, epochs + 1):
        loss = train_epoch(model, train_loader, optimizer, criterion, device)
        scheduler.step()
        val_metrics = evaluate_epoch(model, val_loader, device)

        val_f1 = val_metrics["macro_f1"]
        val_acc = val_metrics["accuracy"]
        logger.info(
            "Epoch %02d/%02d - Loss: %.4f | Val Acc: %.4f | Val Macro-F1: %.4f",
            epoch,
            epochs,
            loss,
            val_acc,
            val_f1,
        )

        if val_f1 > best_val_f1:
            best_val_f1 = val_f1
            torch.save(
                {
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "val_macro_f1": val_f1,
                    "val_metrics": val_metrics,
                },
                best_ckpt_path,
            )
            logger.info("Saved new best checkpoint with Val Macro-F1: %.4f", val_f1)

    # Final evaluation on held-out test split using best checkpoint
    logger.info("Loading best checkpoint for final evaluation on test split...")
    ckpt = torch.load(best_ckpt_path, map_location=device)
    model.load_state_dict(ckpt["model_state_dict"])
    test_metrics = evaluate_epoch(model, test_loader, device)

    logger.info(
        "Test Results: Accuracy: %.4f | Macro-F1: %.4f | ECE: %.4f",
        test_metrics["accuracy"],
        test_metrics["macro_f1"],
        test_metrics["ece"],
    )
    save_metrics(test_metrics, output_dir / "metrics.json")
    return best_ckpt_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Train BountyLoop Freshness Baseline.")
    parser.add_argument(
        "--data-root", type=Path, default=Path("."), help="Project root"
    )
    parser.add_argument(
        "--splits-dir",
        type=Path,
        default=Path("ml/data/processed/splits"),
        help="Splits CSV directory",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("ml/artifacts/freshness_v1"),
        help="Output directory for checkpoints",
    )
    parser.add_argument("--epochs", type=int, default=10, help="Training epochs")
    parser.add_argument("--batch-size", type=int, default=32, help="Batch size")
    parser.add_argument("--lr", type=float, default=3e-4, help="Learning rate")
    args = parser.parse_args()

    run_training(
        data_root=args.data_root,
        splits_dir=args.splits_dir,
        output_dir=args.output_dir,
        epochs=args.epochs,
        batch_size=args.batch_size,
        learning_rate=args.lr,
    )


if __name__ == "__main__":
    main()
