"""BountyLoop — EfficientNet-B0 Binary Freshness Model.

Architecture:
- Backbone: EfficientNet-B0 (pretrained on ImageNet)
- Global Average Pooling -> Dropout (0.2) -> Linear(in_features, 2)
- Binary classification: class 0 = "fresh", class 1 = "spoiled"
"""

from __future__ import annotations

from typing import ClassVar

import torch
from torch import nn


class FreshnessBaseline(nn.Module):
    """EfficientNet-B0 binary freshness classifier."""

    CLASS_NAMES: ClassVar[list[str]] = ["fresh", "spoiled"]

    def __init__(self, pretrained: bool = True, dropout_rate: float = 0.2) -> None:
        super().__init__()
        # Try loading via timm first, fallback to torchvision
        try:
            import timm  # type: ignore

            self.backbone = timm.create_model(
                "efficientnet_b0",
                pretrained=pretrained,
                num_classes=0,  # Pool feature extractor
                drop_rate=dropout_rate,
            )
            in_features = self.backbone.num_features
        except (ImportError, RuntimeError, ModuleNotFoundError):
            from torchvision import models  # type: ignore

            weights = models.EfficientNet_B0_Weights.DEFAULT if pretrained else None
            model = models.efficientnet_b0(weights=weights)
            in_features = model.classifier[1].in_features
            model.classifier = nn.Identity()  # type: ignore
            self.backbone = model

        self.classifier = nn.Sequential(
            nn.Dropout(p=dropout_rate),
            nn.Linear(in_features, 2),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass returning raw logits of shape (B, 2)."""
        features = self.backbone(x)
        if isinstance(features, tuple):
            features = features[0]
        logits = self.classifier(features)
        return logits


def create_model(pretrained: bool = True) -> FreshnessBaseline:
    """Factory helper for FreshnessBaseline."""
    return FreshnessBaseline(pretrained=pretrained)
