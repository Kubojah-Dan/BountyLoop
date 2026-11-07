# BountyLoop Data Privacy, Retention & Governance Policy (Phase 12)

> [!IMPORTANT]
> **Privacy-by-Design Commitment**  
> BountyLoop handles surplus food rescue logistics while ensuring that food donors, recipients, and volunteer couriers retain full sovereignty over their personal information and visual media. No likeness, biometric data, or private GPS metadata is ever stored or exposed.

---

## 1. Metadata Sanitization & EXIF/GPS Stripping

### Dual-Layer Stripping Architecture
Every food photograph submitted to BountyLoop undergoes mandatory metadata stripping:

1. **Client-Side Sanitization:** Mobile camera streams and gallery pickers re-encode captured images into clean memory buffers prior to multipart network transit.
2. **Server-Side Enforcement (`backend/app/services/storage.py`):**
   - Transposes image orientation based on EXIF orientation tags.
   - Discards all EXIF, GPS coordinates, camera serial numbers, and device fingerprints.
   - Re-encodes the image using Pillow into a clean JPEG container with zero metadata dictionaries.
   - Computes SHA-256 hash strictly from the sanitized pixel bytes for duplicate submission detection.

### Verification Assertions
Automated test `test_exif_gps_metadata_is_stripped_server_side` generates synthetic JPEG fixtures containing EXIF GPS coordinates (Latitude/Longitude tags) and asserts that the stored artifact on disk contains zero EXIF metadata.

---

## 2. Model Retraining Consent (`consent_model_training`)

- **Default Opt-In Policy:** **Strictly Opt-Out by Default (`consent_model_training = False`)**.
- **User Control:** Users can view and toggle their consent status anytime via:
  - Mobile Profile & Settings screen
  - API: `PATCH /v1/me` with `{"consent_model_training": true}`
- **Retraining Manifest Gate:**
  - The monthly fine-tuning pipeline (`ml/src/data/`) queries only donations whose donating user had `consent_model_training == True` at the time of creation.
  - If consent is revoked or absent, the photo is permanently excluded from training splits.

---

## 3. Right to be Forgotten & Data Deletion (`DELETE /v1/me/data`)

Under GDPR Article 17 and CCPA, any registered user can purge their personal data and all uploaded media:

### Execution Protocol
1. **Trigger:** `DELETE /v1/me/data` (authenticated via Firebase token).
2. **Media Purge:**
   - Every file on disk in `storage/photos/<donation_id>/` associated with the donor is permanently deleted (`shutil.rmtree`).
   - `Donation.photo_paths` is emptied.
3. **PII Anonymization:**
   - `display_name` is set to `"Deleted User"`.
   - `email` is randomized and replaced with `purged_<uuid>@privacy.bountyloop.local`.
   - `phone_e164` and `org_name` are set to `NULL`.
   - `is_active` is set to `False`.
   - `consent_model_training` is set to `False`.
4. **Audit Trail:**
   - Anonymous numerical donation weights and food categories remain in aggregated tables to ensure ledger accounting integrity (`impact_logs`) without any linkable personal identity.

---

## 4. Donor Photo Capture Guidelines

To protect the privacy of kitchen staff, donors, and the general public, the mobile capture interface displays the following guidance:

> **Food Only, Please:**
> - Capture clear photos of food containers, crates, or bakery trays.
> - Do **not** include faces, employee name badges, or human likenesses.
> - Avoid customer license plates or private residential door numbers.

---

## 5. Partner NGO Data Processing Addendum (DPA)

For food banks, pantries, and municipal partners:
- **Data Minimization:** Recipient organizations receive only donor business name, pickup address, contact phone, and estimated food weight needed to complete rescue logistics.
- **Access Control:** Role-based access control (`UserRole.recipient`, `UserRole.donor`, `UserRole.admin`) is enforced at the database and API middleware levels.
- **Sub-processors:**
  - Firebase Authentication (Google Cloud) — Identity management.
  - PostgreSQL / PostGIS — Transactional state and geospatial matching.
  - Twilio — SMS notifications (strictly throttled via `SMS_DAILY_CAP`).

