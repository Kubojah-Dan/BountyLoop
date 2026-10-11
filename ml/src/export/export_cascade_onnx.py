"""BountyLoop — Cascade ONNX Exporter & Parity Verifier.

Exports ItemClassifier (12 classes), FreshnessGraderV2 (4 classes), and
HazardDetector (2 classes) to ONNX with dynamic batch size.
Verifies numerical parity with ONNX Runtime within 0.05 tolerance.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch
from torch import nn

from ml.src.models.cascade_models import (
    FreshnessGraderV2,
    HazardDetector,
    ItemClassifier,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def export_model_to_onnx(
    model: nn.Module,
    output_path: Path,
    num_classes: int,
    opset_version: int = 17,
) -> Path:
    """Export a PyTorch vision module to ONNX format."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    model.eval()

    dummy_input = torch.randn(1, 3, 224, 224, dtype=torch.float32)

    logger.info("Exporting model to ONNX at %s (opset %d)...", output_path, opset_version)
    try:
        torch.onnx.export(
            model,
            dummy_input,
            str(output_path),
            export_params=True,
            opset_version=opset_version,
            do_constant_folding=True,
            input_names=["input"],
            output_names=["logits"],
            dynamic_axes={
                "input": {0: "batch_size"},
                "logits": {0: "batch_size"},
            },
            dynamo=False,
        )
    except TypeError:
        torch.onnx.export(
            model,
            dummy_input,
            str(output_path),
            export_params=True,
            opset_version=opset_version,
            do_constant_folding=True,
            input_names=["input"],
            output_names=["logits"],
            dynamic_axes={
                "input": {0: "batch_size"},
                "logits": {0: "batch_size"},
            },
        )
    logger.info("Exported successfully to %s", output_path)
    return output_path


def verify_model_parity(
    model: nn.Module,
    onnx_path: Path,
    num_classes: int,
    atol: float = 0.05,
) -> bool:
    """Verify PyTorch and ONNX Runtime predictions match within tolerance."""
    logger.info("Verifying numerical parity for %s...", onnx_path)
    model.eval()

    test_input = torch.randn(4, 3, 224, 224, dtype=torch.float32)

    with torch.no_grad():
        pt_out = model(test_input).numpy()

    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    onnx_inputs = {"input": test_input.numpy()}
    onnx_out = session.run(["logits"], onnx_inputs)[0]

    assert onnx_out.shape == (4, num_classes), (
        f"Unexpected ONNX output shape: {onnx_out.shape} != (4, {num_classes})"
    )

    max_diff = float(np.max(np.abs(pt_out - onnx_out)))
    is_close = np.allclose(pt_out, onnx_out, atol=atol)

    logger.info(
        "Parity Check: Max diff = %.6f (Tolerance = %.4f) -> %s",
        max_diff,
        atol,
        "PASSED" if is_close else "FAILED",
    )
    if not is_close:
        raise ValueError(
            f"Parity check failed: max difference {max_diff} exceeds tolerance {atol}"
        )
    return is_close


def export_all_cascade_models(output_dir: Path) -> dict[str, Path]:
    """Export all three cascade models to the specified directory."""
    models: dict[str, tuple[nn.Module, int, str]] = {
        "item": (ItemClassifier(pretrained=False), 12, "item_v1.onnx"),
        "freshness": (FreshnessGraderV2(pretrained=False), 4, "freshness_v2.onnx"),
        "hazard": (HazardDetector(pretrained=False), 2, "hazard_v1.onnx"),
    }

    exported_paths = {}
    for name, (module, num_cls, filename) in models.items():
        out_file = output_dir / filename
        export_model_to_onnx(module, out_file, num_classes=num_cls)
        verify_model_parity(module, out_file, num_classes=num_cls)
        exported_paths[name] = out_file

    return exported_paths


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Export BountyLoop Cascade Models to ONNX")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("ml/artifacts"),
        help="Directory to save exported ONNX models",
    )
    args = parser.parse_args()
    export_all_cascade_models(args.output_dir)
