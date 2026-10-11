"""BountyLoop — Taxonomy Builder.

Generates ml/src/data/taxonomy.yaml mapping the 101 Food-101 classes into the
12 BountyLoop surplus rescue taxonomy categories:
- produce_fruit
- produce_vegetable
- bread_bakery
- dairy
- grains_staples
- prepared_cooked
- meat_fish
- soup_stew
- dessert_bakery_sweet
- beverage
- condiment_sauce
- other_unclassified
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import yaml

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)

# Canonical mapping for the 101 Food-101 classes
FOOD101_TO_RESCUE_TAXONOMY: dict[str, str] = {
    # Desserts & Sweet Bakery
    "apple_pie": "dessert_bakery_sweet",
    "baklava": "dessert_bakery_sweet",
    "beignets": "dessert_bakery_sweet",
    "bread_pudding": "dessert_bakery_sweet",
    "cannoli": "dessert_bakery_sweet",
    "carrot_cake": "dessert_bakery_sweet",
    "cheesecake": "dessert_bakery_sweet",
    "chocolate_cake": "dessert_bakery_sweet",
    "chocolate_mousse": "dessert_bakery_sweet",
    "churros": "dessert_bakery_sweet",
    "creme_brulee": "dessert_bakery_sweet",
    "cup_cakes": "dessert_bakery_sweet",
    "donuts": "dessert_bakery_sweet",
    "frozen_yogurt": "dessert_bakery_sweet",
    "ice_cream": "dessert_bakery_sweet",
    "macarons": "dessert_bakery_sweet",
    "pancakes": "dessert_bakery_sweet",
    "panna_cotta": "dessert_bakery_sweet",
    "red_velvet_cake": "dessert_bakery_sweet",
    "strawberry_shortcake": "dessert_bakery_sweet",
    "tiramisu": "dessert_bakery_sweet",
    "waffles": "dessert_bakery_sweet",
    # Bread & Savory Bakery
    "bruschetta": "bread_bakery",
    "french_toast": "bread_bakery",
    "garlic_bread": "bread_bakery",
    # Meat & Fish (Prepared proteins)
    "baby_back_ribs": "meat_fish",
    "beef_carpaccio": "meat_fish",
    "beef_tartare": "meat_fish",
    "ceviche": "meat_fish",
    "chicken_wings": "meat_fish",
    "crab_cakes": "meat_fish",
    "escargots": "meat_fish",
    "filet_mignon": "meat_fish",
    "fish_and_chips": "meat_fish",
    "foie_gras": "meat_fish",
    "fried_calamari": "meat_fish",
    "grilled_salmon": "meat_fish",
    "mussels": "meat_fish",
    "oysters": "meat_fish",
    "peking_duck": "meat_fish",
    "pork_chop": "meat_fish",
    "prime_rib": "meat_fish",
    "sashimi": "meat_fish",
    "scallops": "meat_fish",
    "steak": "meat_fish",
    "tuna_tartare": "meat_fish",
    # Soups & Stews
    "clam_chowder": "soup_stew",
    "french_onion_soup": "soup_stew",
    "hot_and_sour_soup": "soup_stew",
    "lobster_bisque": "soup_stew",
    "miso_soup": "soup_stew",
    "pho": "soup_stew",
    "ramen": "soup_stew",
    # Dairy / Cheese
    "cheese_plate": "dairy",
    # Produce (Vegetable / Salads)
    "beet_salad": "produce_vegetable",
    "caesar_salad": "produce_vegetable",
    "caprese_salad": "produce_vegetable",
    "edamame": "produce_vegetable",
    "greek_salad": "produce_vegetable",
    "seaweed_salad": "produce_vegetable",
    # Condiments / Dips / Sauces
    "guacamole": "condiment_sauce",
    "hummus": "condiment_sauce",
    # Grains & Staples / Pasta
    "fried_rice": "grains_staples",
    "gnocchi": "grains_staples",
    "macaroni_and_cheese": "grains_staples",
    "pad_thai": "grains_staples",
    "paella": "grains_staples",
    "risotto": "grains_staples",
    "spaghetti_bolognese": "grains_staples",
    "spaghetti_carbonara": "grains_staples",
    # Prepared / Cooked Meals & Sandwiches
    "bibimbap": "prepared_cooked",
    "breakfast_burrito": "prepared_cooked",
    "chicken_curry": "prepared_cooked",
    "chicken_quesadilla": "prepared_cooked",
    "club_sandwich": "prepared_cooked",
    "croque_madame": "prepared_cooked",
    "deviled_eggs": "prepared_cooked",
    "dumplings": "prepared_cooked",
    "eggs_benedict": "prepared_cooked",
    "falafel": "prepared_cooked",
    "french_fries": "prepared_cooked",
    "grilled_cheese_sandwich": "prepared_cooked",
    "gyoza": "prepared_cooked",
    "hamburger": "prepared_cooked",
    "hot_dog": "prepared_cooked",
    "huevos_rancheros": "prepared_cooked",
    "lasagna": "prepared_cooked",
    "lobster_roll_sandwich": "prepared_cooked",
    "nachos": "prepared_cooked",
    "omelette": "prepared_cooked",
    "onion_rings": "prepared_cooked",
    "pizza": "prepared_cooked",
    "poutine": "prepared_cooked",
    "pulled_pork_sandwich": "prepared_cooked",
    "ravioli": "prepared_cooked",
    "samosa": "prepared_cooked",
    "shrimp_and_grits": "prepared_cooked",
    "spring_rolls": "prepared_cooked",
    "sushi": "prepared_cooked",
    "tacos": "prepared_cooked",
    "takoyaki": "prepared_cooked",
}

VALID_TAXONOMY_CATEGORIES = [
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


def build_taxonomy_yaml(classes_file: Path, output_file: Path) -> None:
    """Build taxonomy.yaml from classes.txt verifying coverage."""
    classes = [
        line.strip()
        for line in classes_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    logger.info("Loaded %d classes from %s", len(classes), classes_file)

    taxonomy_map: dict[str, str] = {}
    missing_classes: list[str] = []

    for cls in classes:
        if cls in FOOD101_TO_RESCUE_TAXONOMY:
            category = FOOD101_TO_RESCUE_TAXONOMY[cls]
            assert (
                category in VALID_TAXONOMY_CATEGORIES
            ), f"Invalid category {category} for {cls}"
            taxonomy_map[cls] = category
        else:
            missing_classes.append(cls)
            taxonomy_map[cls] = "prepared_cooked"  # Default fallback

    if missing_classes:
        logger.warning(
            "Defaulted %d unmapped classes: %s", len(missing_classes), missing_classes
        )

    payload = {
        "metadata": {
            "version": "1.0",
            "description": "BountyLoop surplus food redistribution rescue taxonomy mapping for Food-101",
            "total_food101_classes": len(classes),
            "rescue_categories": VALID_TAXONOMY_CATEGORIES,
        },
        "food101_mapping": taxonomy_map,
    }

    output_file.parent.mkdir(parents=True, exist_ok=True)
    with open(output_file, "w", encoding="utf-8") as f:
        yaml.safe_dump(payload, f, sort_keys=False)

    logger.info("Wrote taxonomy configuration to %s", output_file)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build BountyLoop food taxonomy YAML.")
    parser.add_argument(
        "--classes",
        type=Path,
        default=Path("ml/data/food101/meta/meta/classes.txt"),
        help="Path to Food-101 classes.txt",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("ml/src/data/taxonomy.yaml"),
        help="Path to output taxonomy.yaml",
    )
    args = parser.parse_args()
    build_taxonomy_yaml(args.classes, args.output)


if __name__ == "__main__":
    main()
