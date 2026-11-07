# BountyLoop — Impact Measurement Methodology & Verification Framework

> **Document Version:** 1.0  
> **Last Verified:** 2026-11-07  
> **Applies to:** API version ≥ 0.1.0, Methodology version `v1.0`

---

## 1. Executive Summary & Transparency Commitment

BountyLoop quantifies the social, nutritional, and environmental benefits of surplus food rescue. Because impact claims are often subjected to greenwashing or unverified inflation, BountyLoop adheres to strict **scientific honesty principles**:

1. **Empirical Measurement First:** Rescued food weight ($W_{\text{kg}}$) is empirically recorded by donors and verified upon physical pickup by recipient partners.
2. **Defensible Nutritional Conversion:** Meals equivalent ($M$) are computed using recognized international standards (FAO / USDA ERS / ReFED), representing typical portion weights.
3. **Explicit Estimate Labeling:** Greenhouse gas emissions avoided ($E_{\text{CO}_2\text{e}}$) are **statistically modeled estimates** derived from landfill diversion lifecycle analysis. They are explicitly marked as **`UNVERIFIED estimate`** across all API responses, dashboards, and reports.
4. **Zero Duplicate Counting:** Exactly one immutable `impact_log` row is persisted per completed rescue. Database constraints enforce uniqueness at the database level (`UNIQUE(donation_id)`).

> [!IMPORTANT]
> **Scientific Integrity Disclosure:** Avoided emissions metrics are estimates based on EPA WARM and UNEP landfill methane diversion factors. They must **never** be presented to stakeholders or donors as direct laboratory-measured facts.

---

## 2. Mathematical Formulation & Conversion Factors

### 2.1 Rescued Weight ($W_{\text{kg}}$)
- **Definition:** Physical net mass of food saved from disposal and delivered to recipient organization.
- **Unit:** Kilograms ($\text{kg}$), rounded to 2 decimal places.
- **Verification Status:** `VERIFIED_EMPIRICAL` (confirmed at pickup).

### 2.2 Meal Equivalents ($M$)
- **Formula:**
  $$M = \frac{W_{\text{kg}}}{\text{MEAL\_KG\_FACTOR}}$$
- **Default Factor:** $1.2 \text{ kg / meal}$
- **Source:** USDA Economic Research Service (ERS) Food Loss and Waste metrics; ReFED Food Waste Reduction Standard; FAO Food Balance calculations.
- **Verification Status:** `VERIFIED_STANDARD` (widely recognized food rescue benchmark).

### 2.3 Greenhouse Gas Emissions Avoided ($E_{\text{CO}_2\text{e}}$)
- **Formula:**
  $$E_{\text{CO}_2\text{e}} = W_{\text{kg}} \times \text{IMPACT\_CO2E\_FACTOR}$$
- **Default Factor:** $2.5 \text{ kg CO}_2\text{e} / \text{kg food waste avoided}$
- **Source:** Derived from EPA Waste Reduction Model (WARM) v15 (food waste to landfill anaerobic digestion methane emissions) and UNEP Food Waste Index Report (2021).
- **Verification Status:** `UNVERIFIED_ESTIMATE` (proxy-based model pending pilot-city compost/landfill lifecycle validation).

---

## 3. Factors Specification & Provenance Table

| Metric | Factor Name | Value | Units | Provenance / Citation | Integrity Status |
|---|---|---|---|---|---|
| **Rescued Weight** | `est_weight_kg` | Measured | $\text{kg}$ | Donor scale or CV volume estimate verified upon pickup | `VERIFIED_EMPIRICAL` |
| **Meal Equivalents** | `meal_kg_factor` | $1.20$ | $\text{kg/meal}$ | USDA ERS / ReFED Standard (adult meal equivalent ~1.2 kg) | `VERIFIED_STANDARD` |
| **Avoided Emissions** | `impact_co2e_factor` | $2.50$ | $\text{kg CO}_2\text{e} / \text{kg}$ | EPA WARM v15 / UNEP Food Waste Index 2021 landfill diversion | `UNVERIFIED_ESTIMATE` |

---

## 4. Single-Row Idempotency Contract

Every food rescue follows a strict lifecycle:
```
Open → Matched → In Transit → Completed (Picked Up)
```
Upon pickup confirmation (`POST /v1/claims/{id}/pickup`), the system executes an atomic transaction:
1. Updates `Claim.status = ClaimStatus.picked_up`.
2. Updates `Donation.status = DonationStatus.completed`.
3. Performs an upsert on `impact_log` with `donation_id = donation.id`.
4. Dispatches WebSocket and push/SMS notifications.

**Integrity Invariants:**
- `COUNT(completed donations) == COUNT(impact_log rows)`
- `SUM(donation.est_weight_kg WHERE status='completed') == SUM(impact_log.kg_rescued)`
- Calling the pickup endpoint multiple times is idempotent and produces zero duplicate rows.

---

## 5. Pilot Report Template

Use the following template for weekly and monthly pilot evaluations:

```markdown
# BountyLoop Pilot Impact Report

**Reporting Period:** [YYYY-MM-DD to YYYY-MM-DD]  
**Pilot Zone:** [City / Neighborhood, e.g., Austin Central]  
**Report Generated:** [YYYY-MM-DD HH:MM UTC]  
**Methodology Version:** v1.0  

---

### 1. Headline Impact Metrics

| Metric | Total Value | Unit | Basis / Status |
|---|---|---|---|
| Food Rescued | 0.00 | kg | Empirical (weighed at pickup) |
| Meal Equivalents | 0.0 | meals | Standard (1.2 kg/meal FAO/USDA) |
| Avoided GHG Emissions | 0.00 | kg CO₂e | Modeled estimate (2.5 factor, UNVERIFIED) |
| Completed Rescues | 0 | transactions | Verified loop closures |

---

### 2. SQL Audit & Reconciliation

- Total Completed Claims: `[N]`
- Total ImpactLog Records: `[N]`
- Reconciliation Delta: `0.0 kg` (100% Reconciled ✅)

---

### 3. Weekly Trend Breakdown

| Week | Completed Rescues | Weight Rescued (kg) | Meals Equivalent | CO₂e Avoided (kg, est.) |
|---|---|---|---|---|
| Week 1 | ... | ... | ... | ... |
| Week 2 | ... | ... | ... | ... |
| Week 3 | ... | ... | ... | ... |
| Week 4 | ... | ... | ... | ... |

---

### 4. Partner Participation

#### Donors
- [Donor Name 1]: [kg] kg ([N] donations)
- [Donor Name 2]: [kg] kg ([N] donations)

#### Recipients
- [Recipient Name 1]: [kg] kg rescued ([meals] meals distributed)
- [Recipient Name 2]: [kg] kg rescued ([meals] meals distributed)

---

### 5. Methodological Notes & Disclosures
- Avoided emissions calculations reflect modeled landfill diversion factors and are flagged as estimates.
- Net emissions do not account for vehicle transport fuel consumption unless vehicle routing telematics are integrated.
```

