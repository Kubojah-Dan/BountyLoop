"""BountyLoop — Model Evaluation & Metrics Computation.

Computes:
- Macro-F1, per-class F1, Precision, Recall
- Confusion matrix
- Expected Calibration Error (ECE)
- Per-source / per-category breakdown
- Outputs metrics.json
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import numpy as np

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def compute_ece(probs: np.ndarray, targets: np.ndarray, n_bins: int = 10) -> float:
    """Compute Expected Calibration Error (ECE)."""
    confidences = np.max(probs, axis=1)
    predictions = np.argmax(probs, axis=1)
    accuracies = (predictions == targets).astype(float)

    bin_boundaries = np.linspace(0, 1, n_bins + 1)
    ece = 0.0

    for i in range(n_bins):
        in_bin = (confidences > bin_boundaries[i]) & (
            confidences <= bin_boundaries[i + 1]
        )
        prop_in_bin = np.mean(in_bin)
        if prop_in_bin > 0:
            avg_accuracy_in_bin = np.mean(accuracies[in_bin])
            avg_confidence_in_bin = np.mean(confidences[in_bin])
            ece += np.abs(avg_accuracy_in_bin - avg_confidence_in_bin) * prop_in_bin

    return float(ece)


def compute_metrics(
    y_true: list[int] | np.ndarray,
    y_pred: list[int] | np.ndarray,
    y_probs: list[list[float]] | np.ndarray,
    class_names: list[str],
    metadata_categories: list[str] | None = None,
) -> dict[str, Any]:
    """Compute comprehensive classification metrics."""
    y_true_arr = np.array(y_true)
    y_pred_arr = np.array(y_pred)
    y_probs_arr = np.array(y_probs)

    num_classes = len(class_names)
    cm = np.zeros((num_classes, num_classes), dtype=int)
    for t, p in zip(y_true_arr, y_pred_arr, strict=False):
        cm[t, p] += 1

    per_class: dict[str, dict[str, float]] = {}
    f1_list: list[float] = []

    for i, name in enumerate(class_names):
        tp = cm[i, i]
        fp = cm[:, i].sum() - tp
        fn = cm[i, :].sum() - tp

        prec = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        rec = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1 = float(2 * prec * rec / (prec + rec)) if (prec + rec) > 0 else 0.0
        f1_list.append(f1)

        per_class[name] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "support": int(cm[i, :].sum()),
        }

    macro_f1 = float(np.mean(f1_list))
    accuracy = float(np.mean(y_true_arr == y_pred_arr))
    ece = compute_ece(y_probs_arr, y_true_arr)

    # Per-category breakdown (e.g. bread, dairy, fruits, vegetables)
    category_breakdown: dict[str, dict[str, float]] = {}
    if metadata_categories and len(metadata_categories) == len(y_true_arr):
        cats = sorted(set(metadata_categories))
        for cat in cats:
            mask = np.array([c == cat for c in metadata_categories])
            cat_true = y_true_arr[mask]
            cat_pred = y_pred_arr[mask]
            cat_acc = float(np.mean(cat_true == cat_pred)) if len(cat_true) > 0 else 0.0
            category_breakdown[cat] = {
                "count": int(mask.sum()),
                "accuracy": round(cat_acc, 4),
            }

    return {
        "accuracy": round(accuracy, 4),
        "macro_f1": round(macro_f1, 4),
        "ece": round(ece, 4),
        "confusion_matrix": cm.tolist(),
        "per_class": per_class,
        "per_category_breakdown": category_breakdown,
    }


def save_metrics(metrics: dict[str, Any], output_path: Path) -> None:
    """Save metrics to JSON file."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    logger.info("Saved metrics to %s", output_path)
