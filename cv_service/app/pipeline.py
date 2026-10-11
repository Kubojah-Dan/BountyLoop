"""BountyLoop — Inference Pipeline & Model Serving.

Manages ONNX Runtime sessions, runs inference with TTA, and evaluates
confidence gates against defined safety thresholds:
- AUTO_CONF: >= 0.90
- CONFIRM_CONF: >= 0.60
- HAZARD_FORCES_REVIEW: True
"""

from __future__ import annotations

import logging
import os
import time
from pathlib import Path
from typing import Any

import numpy as np
import onnxruntime as ort

from app.preprocess import preprocess_image

logger = logging.getLogger(__name__)


def softmax(x: np.ndarray) -> np.ndarray:
    """Compute softmax probabilities along last axis."""
    e_x = np.exp(x - np.max(x, axis=-1, keepdims=True))
    return e_x / np.sum(e_x, axis=-1, keepdims=True)


class InferencePipeline:
    """Manages ONNX sessions and executes prediction pipeline."""

    def __init__(self, models_dir: Path | None = None) -> None:
        if models_dir is None:
            models_dir = Path(os.environ.get("MODELS_DIR", "/app/models"))

        self.models_dir = models_dir
        self.auto_conf = float(os.environ.get("AUTO_CONF", "0.90"))
        self.confirm_conf = float(os.environ.get("CONFIRM_CONF", "0.60"))
        self.hazard_forces_review = (
            os.environ.get("HAZARD_FORCES_REVIEW", "true").lower() == "true"
        )
        self.tta_default = os.environ.get("TTA", "true").lower() == "true"

        self.sessions: dict[str, ort.InferenceSession] = {}
        self.model_versions: dict[str, str] = {}
        self._load_models()

    def _load_models(self) -> None:
        """Discover and initialize ONNX Runtime sessions."""
        logger.info("Scanning models directory: %s", self.models_dir)
        freshness_model_path = self.models_dir / "freshness_v1.onnx"

        # Check alternative local repo path if running outside Docker
        if not freshness_model_path.exists():
            alt_path = Path("ml/artifacts/freshness_v1.onnx")
            if alt_path.exists():
                freshness_model_path = alt_path

        if freshness_model_path.exists():
            try:
                opts = ort.SessionOptions()
                opts.intra_op_num_threads = 2
                opts.graph_optimization_level = (
                    ort.GraphOptimizationLevel.ORT_ENABLE_ALL
                )
                session = ort.InferenceSession(
                    str(freshness_model_path),
                    sess_options=opts,
                    providers=["CPUExecutionProvider"],
                )
                self.sessions["freshness"] = session
                self.model_versions["freshness"] = "freshness_v1"
                logger.info(
                    "Loaded ONNX session: freshness_v1 (%s)", freshness_model_path
                )
            except (ort.OrtError, RuntimeError, OSError) as e:
                logger.error("Failed to load freshness ONNX model: %s", e)
        else:
            logger.warning("No freshness_v1.onnx model found in %s", self.models_dir)

    def predict(
        self, image_bytes: bytes, apply_tta: bool | None = None
    ) -> dict[str, Any]:
        """Execute full inference pipeline on image bytes."""
        t_start = time.perf_counter()
        if apply_tta is None:
            apply_tta = self.tta_default

        standard_tensor, flipped_tensor = preprocess_image(
            image_bytes, target_size=(224, 224), apply_tta=apply_tta
        )

        freshness_session = self.sessions.get("freshness")
        if freshness_session is not None:
            # Run inference on standard view
            logits_std = freshness_session.run(["logits"], {"input": standard_tensor})[
                0
            ]
            probs = softmax(logits_std)[0]

            # Run inference on flipped view if TTA enabled
            if apply_tta and flipped_tensor is not None:
                logits_flip = freshness_session.run(
                    ["logits"], {"input": flipped_tensor}
                )[0]
                probs_flip = softmax(logits_flip)[0]
                probs = (probs + probs_flip) / 2.0

            pred_class_idx = int(np.argmax(probs))
            classes = ["fresh", "spoiled"]
            freshness_label = classes[pred_class_idx]
            freshness_conf = float(probs[pred_class_idx])
        else:
            # Fallback when model is loading or missing
            freshness_label = "fresh"
            freshness_conf = 0.50

        # Phase 3 Item and Hazard placeholders (upgraded to dedicated heads in Phase 4)
        item_label = "produce_fruit"
        item_conf = 0.92
        hazard_flag = "none"

        # Evaluate safety gate
        needs_review = False
        if (
            freshness_conf < self.confirm_conf
            or item_conf < self.confirm_conf
            or self.hazard_forces_review
            and hazard_flag != "none"
        ):
            needs_review = True

        latency_ms = round((time.perf_counter() - t_start) * 1000.0, 2)

        return {
            "item": item_label,
            "item_confidence": round(item_conf, 4),
            "freshness": freshness_label,
            "freshness_confidence": round(freshness_conf, 4),
            "hazard_flag": hazard_flag,
            "needs_review": needs_review,
            "model_versions": self.model_versions,
            "latency_ms": latency_ms,
        }
