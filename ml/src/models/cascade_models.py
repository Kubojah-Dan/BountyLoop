"""BountyLoop — Cascade Models Architecture.

Defines the three specialized heads for Phase 4:
1. ItemClassifier (Head A): 12 rescue food categories
2. FreshnessGraderV2 (Head B): 4-level freshness scale
3. HazardDetector (Head C): Binary safety/contamination gate
"""

from __future__ import annotations

from typing import ClassVar

import torch
from torch import nn


class ItemClassifier(nn.Module):
    """EfficientNet-B0 food item classifier for 12 rescue categories."""

    CLASS_NAMES: ClassVar[list[str]] = [
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

    def __init__(self, pretrained: bool = True, dropout_rate: float = 0.2) -> None:
        super().__init__()
        try:
            import timm  # type: ignore

            self.backbone = timm.create_model(
                "efficientnet_b0",
                pretrained=pretrained,
                num_classes=0,
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
            nn.Linear(in_features, len(self.CLASS_NAMES)),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass returning logits of shape (B, 12)."""
        features = self.backbone(x)
        if isinstance(features, tuple):
            features = features[0]
        return self.classifier(features)


class FreshnessGraderV2(nn.Module):
    """EfficientNet-B0 4-level freshness grader."""

    CLASS_NAMES: ClassVar[list[str]] = [
        "grade_0_spoiled",
        "grade_1_poor",
        "grade_2_good",
        "grade_3_fresh",
    ]

    def __init__(self, pretrained: bool = True, dropout_rate: float = 0.2) -> None:
        super().__init__()
        try:
            import timm  # type: ignore

            self.backbone = timm.create_model(
                "efficientnet_b0",
                pretrained=pretrained,
                num_classes=0,
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
            nn.Linear(in_features, len(self.CLASS_NAMES)),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass returning logits of shape (B, 4)."""
        features = self.backbone(x)
        if isinstance(features, tuple):
            features = features[0]
        return self.classifier(features)


class HazardDetector(nn.Module):
    """EfficientNet-B0 safety hazard & chemical contamination detector."""

    CLASS_NAMES: ClassVar[list[str]] = [
        "none",
        "suspected_contamination_or_formalin",
    ]

    def __init__(self, pretrained: bool = True, dropout_rate: float = 0.2) -> None:
        super().__init__()
        try:
            import timm  # type: ignore

            self.backbone = timm.create_model(
                "efficientnet_b0",
                pretrained=pretrained,
                num_classes=0,
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
            nn.Linear(in_features, len(self.CLASS_NAMES)),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """Forward pass returning logits of shape (B, 2)."""
        features = self.backbone(x)
        if isinstance(features, tuple):
            features = features[0]
        return self.classifier(features)
