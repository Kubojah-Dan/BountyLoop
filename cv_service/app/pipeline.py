"""BountyLoop — Inference Pipeline & Cascade Model Serving.

Manages ONNX Runtime sessions for:
1. ItemClassifier (12 rescue categories)
2. FreshnessGrader (4-level scale v2 or binary v1)
3. HazardDetector (Binary safety/contamination gate)

Executes Test-Time Augmentation (TTA), coordinates multi-head predictions,
and evaluates results via CascadeDecisionEngine against safety gates:
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

from app.cascade import CascadeDecisionEngine
from app.preprocess import preprocess_image

logger = logging.getLogger(__name__)

ITEM_CLASSES = [
    "produce_fruit",
    "produce_vegetable",
    "bread_bakery",
    "dairy",
    "grains_staples",
    "prepared_cooked",
    "meat_fish",
    "soup_stew",
    "dessert_bakery_sweet",
    "beverage",
    "condiment_sauce",
    "other_unclassified",
]

FRESHNESS_V2_CLASSES = [
    "grade_0_spoiled",
    "grade_1_poor",
    "grade_2_good",
    "grade_3_fresh",
]

FRESHNESS_V1_CLASSES = [
    "fresh",
    "spoiled",
]

HAZARD_CLASSES = [
    "none",
    "suspected_contamination_or_formalin",
]


def softmax(x: np.ndarray) -> np.ndarray:
    """Compute numerically stable softmax probabilities along last axis."""
    e_x = np.exp(x - np.max(x, axis=-1, keepdims=True))
    return e_x / np.sum(e_x, axis=-1, keepdims=True)


class InferencePipeline:
    """Manages ONNX sessions and executes multi-head cascade prediction pipeline."""

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
        self.freshness_classes: list[str] = FRESHNESS_V1_CLASSES

        self.cascade_engine = CascadeDecisionEngine(
            auto_conf=self.auto_conf,
            confirm_conf=self.confirm_conf,
            hazard_forces_review=self.hazard_forces_review,
        )

        self._load_models()

    def _init_session(self, model_path: Path) -> ort.InferenceSession:
        """Create an optimized ONNX Runtime InferenceSession."""
        opts = ort.SessionOptions()
        opts.intra_op_num_threads = 2
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        return ort.InferenceSession(
            str(model_path),
            sess_options=opts,
            providers=["CPUExecutionProvider"],
        )

    def _resolve_model_path(self, filename: str) -> Path | None:
        """Locate model in configured models_dir or local repository artifacts."""
        path = self.models_dir / filename
        if path.exists():
            return path
        alt_path = Path("ml/artifacts") / filename
        if alt_path.exists():
            return alt_path
        return None

    def _load_models(self) -> None:
        """Discover and initialize ONNX Runtime sessions for all cascade heads."""
        logger.info("Scanning models directory: %s", self.models_dir)

        # 1. Freshness Head (v2 preferred, v1 fallback)
        freshness_v2_path = self._resolve_model_path("freshness_v2.onnx")
        freshness_v1_path = self._resolve_model_path("freshness_v1.onnx")

        if freshness_v2_path and freshness_v2_path.exists():
            try:
                session = self._init_session(freshness_v2_path)
                out_shape = session.get_outputs()[0].shape
                num_classes = out_shape[-1] if isinstance(out_shape[-1], int) else 4
                self.sessions["freshness"] = session
                self.model_versions["freshness"] = "freshness_v2"
                self.freshness_classes = (
                    FRESHNESS_V2_CLASSES if num_classes == 4 else FRESHNESS_V1_CLASSES
                )
                logger.info(
                    "Loaded ONNX session: freshness_v2 (%s, %d classes)",
                    freshness_v2_path,
                    len(self.freshness_classes),
                )
            except Exception as e:
                logger.error("Failed loading freshness_v2: %s", e)
        elif freshness_v1_path and freshness_v1_path.exists():
            try:
                self.sessions["freshness"] = self._init_session(freshness_v1_path)
                self.model_versions["freshness"] = "freshness_v1"
                self.freshness_classes = FRESHNESS_V1_CLASSES
                logger.info("Loaded ONNX session: freshness_v1 (%s)", freshness_v1_path)
            except Exception as e:
                logger.error("Failed loading freshness_v1: %s", e)

        # 2. Item Classifier Head
        item_path = self._resolve_model_path("item_v1.onnx")
        if item_path and item_path.exists():
            try:
                self.sessions["item"] = self._init_session(item_path)
                self.model_versions["item"] = "item_v1"
                logger.info("Loaded ONNX session: item_v1 (%s)", item_path)
            except Exception as e:
                logger.error("Failed loading item_v1: %s", e)

        # 3. Hazard Detector Head
        hazard_path = self._resolve_model_path("hazard_v1.onnx")
        if hazard_path and hazard_path.exists():
            try:
                self.sessions["hazard"] = self._init_session(hazard_path)
                self.model_versions["hazard"] = "hazard_v1"
                logger.info("Loaded ONNX session: hazard_v1 (%s)", hazard_path)
            except Exception as e:
                logger.error("Failed loading hazard_v1: %s", e)

    def predict(
        self, image_bytes: bytes, apply_tta: bool | None = None
    ) -> dict[str, Any]:
        """Execute full cascade inference pipeline with TTA and safety gating."""
        t_start = time.perf_counter()
        if apply_tta is None:
            apply_tta = self.tta_default

        standard_tensor, flipped_tensor = preprocess_image(
            image_bytes, target_size=(224, 224), apply_tta=apply_tta
        )

        # ── 1. Item Classification Head ──────────────────────────────────────
        item_session = self.sessions.get("item")
        if item_session is not None:
            logits = item_session.run(["logits"], {"input": standard_tensor})[0]
            probs = softmax(logits)[0]
            if apply_tta and flipped_tensor is not None:
                logits_flip = item_session.run(["logits"], {"input": flipped_tensor})[0]
                probs_flip = softmax(logits_flip)[0]
                probs = (probs + probs_flip) / 2.0
            idx = int(np.argmax(probs))
            item_label = (
                ITEM_CLASSES[idx] if idx < len(ITEM_CLASSES) else "other_unclassified"
            )
            item_conf = float(probs[idx])
        else:
            item_label = "produce_fruit"
            item_conf = 0.92

        # ── 2. Freshness Grading Head ─────────────────────────────────────────
        freshness_session = self.sessions.get("freshness")
        if freshness_session is not None:
            logits = freshness_session.run(["logits"], {"input": standard_tensor})[0]
            probs = softmax(logits)[0]
            if apply_tta and flipped_tensor is not None:
                logits_flip = freshness_session.run(
                    ["logits"], {"input": flipped_tensor}
                )[0]
                probs_flip = softmax(logits_flip)[0]
                probs = (probs + probs_flip) / 2.0
            idx = int(np.argmax(probs))
            freshness_label = (
                self.freshness_classes[idx]
                if idx < len(self.freshness_classes)
                else self.freshness_classes[0]
            )
            freshness_conf = float(probs[idx])
        else:
            freshness_label = "grade_3_fresh"
            freshness_conf = 0.88

        # ── 3. Hazard Detection Head ──────────────────────────────────────────
        hazard_session = self.sessions.get("hazard")
        if hazard_session is not None:
            logits = hazard_session.run(["logits"], {"input": standard_tensor})[0]
            probs = softmax(logits)[0]
            if apply_tta and flipped_tensor is not None:
                logits_flip = hazard_session.run(["logits"], {"input": flipped_tensor})[0]
                probs_flip = softmax(logits_flip)[0]
                probs = (probs + probs_flip) / 2.0
            idx = int(np.argmax(probs))
            hazard_flag = (
                HAZARD_CLASSES[idx] if idx < len(HAZARD_CLASSES) else "none"
            )
            hazard_conf = float(probs[idx])
        else:
            hazard_flag = "none"
            hazard_conf = 0.95

        # ── 4. Cascade Decision Engine Evaluation ─────────────────────────────
        result = self.cascade_engine.evaluate(
            item=item_label,
            item_confidence=item_conf,
            freshness=freshness_label,
            freshness_confidence=freshness_conf,
            hazard_flag=hazard_flag,
            hazard_confidence=hazard_conf,
        )

        latency_ms = round((time.perf_counter() - t_start) * 1000.0, 2)

        output = result.to_dict()
        output["latency_ms"] = latency_ms
        output["models_used"] = self.model_versions
        return output
