"""BountyLoop — ONNX Exporter & Parity Verifier.

Exports PyTorch FreshnessBaseline checkpoint to ONNX with dynamic batch size.
Verifies numerical parity with ONNX Runtime within 1e-3 tolerance.
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import numpy as np
import onnxruntime as ort
import torch

from ml.src.models.baseline_freshness import FreshnessBaseline

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


def export_to_onnx(
    checkpoint_path: Path | None,
    output_path: Path,
    opset_version: int = 17,
) -> Path:
    """Export FreshnessBaseline model to ONNX with dynamic batch."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    model = FreshnessBaseline(pretrained=False)

    if checkpoint_path and checkpoint_path.exists():
        logger.info("Loading weights from %s", checkpoint_path)
        ckpt = torch.load(checkpoint_path, map_location="cpu")
        state_dict = ckpt.get("model_state_dict", ckpt)
        model.load_state_dict(state_dict)
    else:
        logger.warning(
            "No checkpoint provided or found at %s. Exporting architecture with initialized weights.",
            checkpoint_path,
        )

    model.eval()

    dummy_input = torch.randn(1, 3, 224, 224, dtype=torch.float32)

    logger.info("Exporting to ONNX at %s (opset %d)...", output_path, opset_version)
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
    return output_path, model


def verify_parity(
    model_or_ckpt: Path | FreshnessBaseline | None,
    onnx_path: Path,
    atol: float = 1e-3,
) -> bool:
    """Verify PyTorch and ONNX Runtime predictions match within tolerance."""
    logger.info("Verifying numerical parity for %s...", onnx_path)
    if isinstance(model_or_ckpt, FreshnessBaseline):
        pt_model = model_or_ckpt
    else:
        pt_model = FreshnessBaseline(pretrained=False)
        if model_or_ckpt and Path(model_or_ckpt).exists():
            ckpt = torch.load(model_or_ckpt, map_location="cpu")
            state_dict = ckpt.get("model_state_dict", ckpt)
            pt_model.load_state_dict(state_dict)

    pt_model.eval()

    # Generate random test batch (e.g. batch size 4)
    test_input = torch.randn(4, 3, 224, 224, dtype=torch.float32)

    with torch.no_grad():
        pt_out = pt_model(test_input).numpy()

    # Run in ONNX Runtime
    session = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    onnx_inputs = {"input": test_input.numpy()}
    onnx_out = session.run(["logits"], onnx_inputs)[0]

    max_diff = float(np.max(np.abs(pt_out - onnx_out)))
    is_close = np.allclose(pt_out, onnx_out, atol=atol)

    logger.info(
        "Parity Check Result: Max diff = %.6f (Tolerance = %.4f) -> %s",
        max_diff,
        atol,
        "PASSED" if is_close else "FAILED",
    )
    if not is_close:
        raise ValueError(
            f"Parity check failed: max difference {max_diff} exceeds tolerance {atol}"
        )

    return is_close


def main() -> None:
    parser = argparse.ArgumentParser(description="Export PyTorch model to ONNX.")
    parser.add_argument(
        "--checkpoint",
        type=Path,
        default=Path("ml/artifacts/freshness_v1/best.pt"),
        help="Path to best.pt checkpoint",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("ml/artifacts/freshness_v1.onnx"),
        help="Path to output .onnx file",
    )
    parser.add_argument("--opset", type=int, default=17, help="ONNX opset version")
    args = parser.parse_args()

    output_path, model = export_to_onnx(
        args.checkpoint, args.output, opset_version=args.opset
    )
    verify_parity(model, output_path)


if __name__ == "__main__":
    main()
