# BountyLoop API Documentation & Authentication Guide

This document describes the API architecture, authentication flow, role-based access control (RBAC), error formatting standards, and testing conventions implemented in **Phase 2**.

---

## 1. Overview & API Structure

- **Base URL Prefix:** `/v1`
- **Interactive Documentation:**
  - Swagger UI: `http://localhost:8000/docs`
  - ReDoc: `http://localhost:8000/redoc`
  - OpenAPI JSON Specification: `http://localhost:8000/openapi.json`
- **Health Check:** `GET /healthz` (200 OK with `{"status": "ok"}`)

---

## 2. Authentication Flow

BountyLoop uses **Firebase Authentication** as its primary identity provider (supporting Google, Apple, and Email Sign-in on web and mobile clients) combined with **PostgreSQL auto-provisioning on first sight**.

```mermaid
sequenceid
sequenceDiagram
    autonumber
    actor User as User / Client App
    participant FB as Firebase Auth
    participant API as BountyLoop API (/v1)
    participant DB as PostgreSQL (PostGIS)

    User->>FB: Sign in (OAuth / Email Link)
    FB-->>User: Firebase ID Token (JWT)
    User->>API: POST /v1/auth/session { "id_token": "<jwt>" }
    API->>FB: Verify token (Firebase Admin SDK)
    FB-->>API: Decoded claims (uid, email, name)
    API->>DB: Query User by firebase_uid
    alt First Time User (New)
        API->>DB: INSERT INTO users (role='donor', display_name, email)
        DB-->>API: New User Created
    else Existing User
        API->>DB: UPDATE last_active_at
    end
    API-->>User: 200 OK { user_id, role, profile, is_new_user }
    Note over User,API: For subsequent requests, client includes Bearer Token:<br/>Authorization: Bearer <id_token>
```

### Auto-Provisioning on First Sight
When a client presents a valid Firebase ID token for a user that does not yet exist in BountyLoop's database:
1. The backend extracts `uid`, `email`, and `name` from the verified token claims.
2. A new `User` row is provisioned with default role `UserRole.DONOR` and `is_active=True`.
3. The response indicates `is_new_user: true` so frontend onboarding flows can redirect the user to role selection if needed.

---

## 3. Endpoints

### 3.1 Authentication & Session

#### `POST /v1/auth/session`
Initiate or verify an active session using a Firebase ID token.

- **Request Headers:** `Content-Type: application/json`
- **Request Body (`SessionCreate`):**
  ```json
  {
    "id_token": "eyJhbGciOiJSUzI1NiIs..."
  }
  ```
- **Response (`SessionResponse`, 200 OK):**
  ```json
  {
    "user_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "role": "donor",
    "profile": {
      "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
      "firebase_uid": "fb_12345",
      "email": "sarah@austinrescue.org",
      "display_name": "Sarah Chen",
      "phone_e164": "+15125550101",
      "org_name": "Austin Food Rescue",
      "role": "donor",
      "is_active": true,
      "created_at": "2026-10-10T12:00:00Z",
      "updated_at": "2026-10-10T12:00:00Z"
    },
    "is_new_user": false
  }
  ```

#### `POST /v1/auth/role` & `POST /v1/me/role`
Assign or update role during user onboarding (e.g., choosing `donor`, `recipient`, `volunteer`, or `buyer`).

- **Headers:** `Authorization: Bearer <id_token>`
- **Request Body (`RoleUpdateRequest`):**
  ```json
  {
    "role": "recipient",
    "org_name": "Central Texas Food Bank"
  }
  ```
- **Response (`UserRead`, 200 OK):** Updated user profile.

---

### 3.2 User Profile Management

#### `GET /v1/me`
Retrieve the current authenticated user's profile.

- **Headers:** `Authorization: Bearer <id_token>`
- **Response (`UserRead`, 200 OK):**
  ```json
  {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "firebase_uid": "fb_12345",
    "email": "sarah@austinrescue.org",
    "display_name": "Sarah Chen",
    "phone_e164": "+15125550101",
    "org_name": "Austin Food Rescue",
    "role": "donor",
    "is_active": true,
    "created_at": "2026-10-10T12:00:00Z",
    "updated_at": "2026-10-10T12:00:00Z"
  }
  ```

#### `PATCH /v1/me`
Update mutable profile fields (display name, phone, organization name).

- **Headers:** `Authorization: Bearer <id_token>`
- **Request Body (`UserUpdate`):**
  ```json
  {
    "display_name": "Sarah Chen-Miller",
    "phone_e164": "+15125550199",
    "org_name": "Austin Food Rescue Network"
  }
  ```
- **Response (`UserRead`, 200 OK):** Updated user profile.

---

### 3.3 Role Guards & RBAC Demo Endpoints

Role-based access is enforced via FastAPI dependency factories:
```python
@router.get("/admin-only")
async def admin_route(user: User = Depends(require_role(UserRole.ADMIN))):
    ...
```

- `GET /v1/users/admin-only` — requires `role: admin`
- `GET /v1/users/donor-only` — requires `role: donor` or `role: admin`

If an authenticated user has insufficient permissions, the endpoint returns **403 Forbidden** in RFC-7807 format.

---

## 4. RFC-7807 Problem Details Standard

All errors (HTTP 4xx and 5xx) returned by BountyLoop conform to the **RFC-7807 Problem Details** standard with `Content-Type: application/problem+json`.

### 4.1 Schema Definition
| Field | Type | Description |
|---|---|---|
| `type` | `string` | URI identifying problem classification (e.g. `https://bountyloop.org/errors/unauthorized`) |
| `title` | `string` | Short human-readable summary of problem |
| `status` | `integer` | HTTP status code matching the response |
| `detail` | `string` | Specific explanation for this error occurrence |
| `instance` | `string` (optional) | URI reference of request path (e.g. `/v1/me`) |
| `invalid_params` | `list[dict]` (optional) | Present on 422 validation errors with field-level details |

### 4.2 Example Responses

#### 401 Unauthorized (Missing or Invalid Token)
```json
{
  "type": "https://bountyloop.org/errors/unauthorized",
  "title": "Unauthorized",
  "status": 401,
  "detail": "Missing Authorization header with Bearer token.",
  "instance": "/v1/me",
  "invalid_params": null
}
```

#### 403 Forbidden (Insufficient Role)
```json
{
  "type": "https://bountyloop.org/errors/forbidden",
  "title": "Forbidden",
  "status": 403,
  "detail": "Role 'donor' is not authorized to access this resource. Required: ['admin'].",
  "instance": "/v1/users/admin-only",
  "invalid_params": null
}
```

#### 422 Unprocessable Entity (Schema Validation Error)
```json
{
  "type": "https://bountyloop.org/errors/validation-error",
  "title": "Unprocessable Entity",
  "status": 422,
  "detail": "Request body validation failed for 1 parameter(s).",
  "instance": "/v1/auth/session",
  "invalid_params": [
    {
      "loc": ["body", "id_token"],
      "msg": "Field required",
      "type": "missing"
    }
  ]
}
```

---

## 5. Rate Limiting

Rate limiting is enforced using `slowapi` with in-memory storage (backed by Redis in multi-instance production environments).
- Sensitive authentication routes (such as `POST /v1/auth/session`) are limited to **60 requests / minute per client IP**.
- When rate limit is exceeded, HTTP **429 Too Many Requests** is returned in RFC-7807 format.

---

## 6. Local Development & Testing

### 6.1 Running Tests
Execute the full test suite inside the container:
```bash
docker compose exec api pytest tests/ -v
```

### 6.2 Test Coverage
To generate a coverage report:
```bash
docker compose exec api pytest --cov=app tests/
```
Current coverage for Phase 2: **85%** across all application modules.

### 6.3 Local Bearer Token Mocking
In tests and development mode, `verify_firebase_token` can be mocked using `unittest.mock.patch`:
```python
from unittest.mock import patch

mock_claims = {
    "uid": "fb_dev_user_001",
    "email": "dev@bountyloop.org",
    "name": "Dev User",
}

with patch("app.core.security.verify_firebase_token", return_value=mock_claims):
    # API calls using Authorization: Bearer mock_token are authenticated
    ...
```
