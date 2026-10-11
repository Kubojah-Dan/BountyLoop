# BountyLoop — Dataset Audit and Provenance

This document contains verified counts, dimensions, class distributions, and licensing provenance
for datasets used across the computer vision training pipeline.

---

## 1. Summary of Verified Datasets

| Dataset | Status | Verified Files | Classes | Resolution (Avg) | Licence / Source |
|---|---|---|---|---|---|
| Fresh and Spoiled Food (Kaggle) | `VERIFIED` ✅ | **2,715** | 8 | 1172x951 | Research / CC BY-SA 4.0 (`maheen00shahid/fresh-and-spoiled-food-image-dataset`) |
| FruitVision (Mendeley Data) | `VERIFIED` ✅ | **10,154** | 15 | 1085x1282 | CC BY 4.0 (DOI `10.17632/xkbjx8959c.2`) |
| Food-101 (ImageNet / Kaggle mirror) | `VERIFIED` ✅ | **101,000** | 101 | 492x476 | Academic Fair Use (`kmader/food41` / ETH Zurich Food-101) |

---

## 2. Per-Dataset Breakdown

### 2.1 Fresh and Spoiled Food (Kaggle)

- **Path:** `ml/data/freshness`
- **Total verified files:** 2715
- **Corrupt files detected in audit sample:** 0
- **Resolution range:** min `390x132`, max `5472x3648`, avg `1172x951`
- **Formats present:** `{"JPEG": 200}`

#### Class Distribution

| Class | Count |
|---|---|
| `fresh_bread` | 205 |
| `fresh_dairy` | 204 |
| `fresh_fruits` | 450 |
| `fresh_vegetables` | 433 |
| `spoiled_bread` | 344 |
| `spoiled_dairy` | 299 |
| `spoiled_fruits` | 289 |
| `spoiled_vegetables` | 491 |

### 2.2 FruitVision (Mendeley Data)

- **Path:** `ml/data/fruitvision`
- **Total verified files:** 10154
- **Corrupt files detected in audit sample:** 0
- **Resolution range:** min `718x780`, max `2408x3692`, avg `1085x1282`
- **Formats present:** `{"JPEG": 200}`

#### Class Distribution

| Class | Count |
|---|---|
| `Apple/Formalin-mixed` | 643 |
| `Apple/Fresh` | 765 |
| `Apple/Rotten` | 630 |
| `Banana/Formalin-mixed` | 660 |
| `Banana/Fresh` | 749 |
| `Banana/Rotten` | 632 |
| `Grape/Formalin-mixed` | 610 |
| `Grape/Fresh` | 770 |
| `Grape/Rotten` | 630 |
| `Mango/Formalin-mixed` | 616 |
| `Mango/Fresh` | 763 |
| `Mango/Rotten` | 630 |
| `Orange/Formalin-mixed` | 647 |
| `Orange/Fresh` | 753 |
| `Orange/Rotten` | 656 |

### 2.3 Food-101 (ImageNet / Kaggle mirror)

- **Path:** `ml/data/food101/images`
- **Total verified files:** 101000
- **Corrupt files detected in audit sample:** 0
- **Resolution range:** min `288x288`, max `512x512`, avg `492x476`
- **Formats present:** `{"JPEG": 200}`

#### Class Distribution

| Class | Count |
|---|---|
| `apple_pie` | 1,000 |
| `baby_back_ribs` | 1,000 |
| `baklava` | 1,000 |
| `beef_carpaccio` | 1,000 |
| `beef_tartare` | 1,000 |
| `beet_salad` | 1,000 |
| `beignets` | 1,000 |
| `bibimbap` | 1,000 |
| `bread_pudding` | 1,000 |
| `breakfast_burrito` | 1,000 |
| `bruschetta` | 1,000 |
| `caesar_salad` | 1,000 |
| `cannoli` | 1,000 |
| `caprese_salad` | 1,000 |
| `carrot_cake` | 1,000 |
| `ceviche` | 1,000 |
| `cheese_plate` | 1,000 |
| `cheesecake` | 1,000 |
| `chicken_curry` | 1,000 |
| `chicken_quesadilla` | 1,000 |
| `chicken_wings` | 1,000 |
| `chocolate_cake` | 1,000 |
| `chocolate_mousse` | 1,000 |
| `churros` | 1,000 |
| `clam_chowder` | 1,000 |
| `club_sandwich` | 1,000 |
| `crab_cakes` | 1,000 |
| `creme_brulee` | 1,000 |
| `croque_madame` | 1,000 |
| `cup_cakes` | 1,000 |
| `deviled_eggs` | 1,000 |
| `donuts` | 1,000 |
| `dumplings` | 1,000 |
| `edamame` | 1,000 |
| `eggs_benedict` | 1,000 |
| `escargots` | 1,000 |
| `falafel` | 1,000 |
| `filet_mignon` | 1,000 |
| `fish_and_chips` | 1,000 |
| `foie_gras` | 1,000 |
| `french_fries` | 1,000 |
| `french_onion_soup` | 1,000 |
| `french_toast` | 1,000 |
| `fried_calamari` | 1,000 |
| `fried_rice` | 1,000 |
| `frozen_yogurt` | 1,000 |
| `garlic_bread` | 1,000 |
| `gnocchi` | 1,000 |
| `greek_salad` | 1,000 |
| `grilled_cheese_sandwich` | 1,000 |
| `grilled_salmon` | 1,000 |
| `guacamole` | 1,000 |
| `gyoza` | 1,000 |
| `hamburger` | 1,000 |
| `hot_and_sour_soup` | 1,000 |
| `hot_dog` | 1,000 |
| `huevos_rancheros` | 1,000 |
| `hummus` | 1,000 |
| `ice_cream` | 1,000 |
| `lasagna` | 1,000 |
| `lobster_bisque` | 1,000 |
| `lobster_roll_sandwich` | 1,000 |
| `macaroni_and_cheese` | 1,000 |
| `macarons` | 1,000 |
| `miso_soup` | 1,000 |
| `mussels` | 1,000 |
| `nachos` | 1,000 |
| `omelette` | 1,000 |
| `onion_rings` | 1,000 |
| `oysters` | 1,000 |
| `pad_thai` | 1,000 |
| `paella` | 1,000 |
| `pancakes` | 1,000 |
| `panna_cotta` | 1,000 |
| `peking_duck` | 1,000 |
| `pho` | 1,000 |
| `pizza` | 1,000 |
| `pork_chop` | 1,000 |
| `poutine` | 1,000 |
| `prime_rib` | 1,000 |
| `pulled_pork_sandwich` | 1,000 |
| `ramen` | 1,000 |
| `ravioli` | 1,000 |
| `red_velvet_cake` | 1,000 |
| `risotto` | 1,000 |
| `samosa` | 1,000 |
| `sashimi` | 1,000 |
| `scallops` | 1,000 |
| `seaweed_salad` | 1,000 |
| `shrimp_and_grits` | 1,000 |
| `spaghetti_bolognese` | 1,000 |
| `spaghetti_carbonara` | 1,000 |
| `spring_rolls` | 1,000 |
| `steak` | 1,000 |
| `strawberry_shortcake` | 1,000 |
| `sushi` | 1,000 |
| `tacos` | 1,000 |
| `takoyaki` | 1,000 |
| `tiramisu` | 1,000 |
| `tuna_tartare` | 1,000 |
| `waffles` | 1,000 |

---

## 3. Data Leakage and Bias Controls

1. **Grouping by Original Identity:** In FruitVision and augmented variations, all augmented views share an `original_id` and are strictly partitioned into either `train`, `val`, or `test`.
2. **Domain Separation:** Kaggle images represent consumer/mobile photography; FruitVision images represent controlled studio capture. Evaluation scripts report metrics per-source to prevent studio overconfidence.
3. **Freshness Separation:** Food-101 has no freshness labels; Food-101 is exclusively used for the **ITEM** classification head and is prohibited from entering the freshness head.
4. **EXIF Stripping:** All user-donated and training images undergo strict EXIF/GPS stripping at ingestion.