# False Speech API Contract

Version: 0.1.0
Base URL (development): http://localhost:7860

This document describes the HTTP and WebSocket API exposed by the False
Speech backend. It is the human-readable companion to the machine-readable
spec in `docs/openapi.yaml`.

## Status Legend

- Implemented: endpoint exists and works
- Stub: endpoint exists in code but returns 501 Not Implemented
- Planned: endpoint does not exist yet

## Authentication

Protected endpoints require a JWT bearer token in the Authorization header:

```
Authorization: Bearer <access_token>
```

Tokens are issued by `POST /api/auth/login` and expire after the number of
seconds indicated in the login response.

## Health

### GET /

Returns server status and whether the model is loaded.

Status: Implemented

Response 200:

```json
{
    "status": "ok",
    "model_loaded": true,
    "device": "cpu"
}
```

## Auth

### POST /api/auth/register

Creates a new user account.

Status: Planned

Request body:

```json
{
    "name": "Zharif Aziz",
    "email": "user@example.com",
    "phone": "081234567890",
    "password": "correcthorsebattery"
}
```

Response 201:

```json
{
    "user_id": "usr_01HXYZ",
    "email": "user@example.com"
}
```

Errors:

- 400 Invalid input (missing fields, malformed email, short password)
- 409 Email or phone already registered

### POST /api/auth/login

Authenticates a user by email or phone.

Status: Planned

Request body:

```json
{
    "email_or_phone": "user@example.com",
    "password": "correcthorsebattery"
}
```

Response 200:

```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9",
    "token_type": "bearer",
    "expires_in": 3600,
    "user": {
        "id": "usr_01HXYZ",
        "name": "Zharif Aziz",
        "email": "user@example.com",
        "phone": "081234567890",
        "tier": "free",
        "quota_used": 0,
        "quota_limit": 600,
        "quota_reset_at": "2026-10-14T00:00:00Z"
    }
}
```

Errors:

- 401 Invalid credentials

### POST /api/auth/logout

Ends the current session.

Status: Planned

Auth: Bearer token required

Response 204: no content

## User

### GET /api/users/me

Returns the authenticated user profile.

Status: Planned

Auth: Bearer token required

Response 200:

```json
{
    "id": "usr_01HXYZ",
    "name": "Zharif Aziz",
    "email": "user@example.com",
    "phone": "081234567890",
    "tier": "free",
    "quota_used": 120,
    "quota_limit": 600,
    "quota_reset_at": "2026-10-14T00:00:00Z"
}
```

### PATCH /api/users/me

Updates the authenticated user profile.

Status: Planned

Auth: Bearer token required

Request body (all fields optional):

```json
{
    "name": "New Name",
    "phone": "089876543210"
}
```

Response 200: same shape as GET /api/users/me

## Subscription

### GET /api/tiers

Lists all available subscription tiers.

Status: Planned

Auth: none

Response 200:

```json
[
    {
        "id": "free",
        "name": "Free",
        "price": 0,
        "quota_seconds_daily": 600,
        "features": ["live_detection_basic"]
    },
    {
        "id": "pro",
        "name": "Pro",
        "price": 49000,
        "quota_seconds_daily": 18000,
        "features": ["live_detection_basic", "confidence_score", "history_30d"]
    },
    {
        "id": "pro_max",
        "name": "Pro Max",
        "price": 99000,
        "quota_seconds_daily": 43200,
        "features": [
            "live_detection_basic",
            "confidence_score",
            "history_90d",
            "android_widget"
        ]
    },
    {
        "id": "lifetime",
        "name": "Lifetime",
        "price": 499000,
        "quota_seconds_daily": 0,
        "features": [
            "live_detection_basic",
            "confidence_score",
            "history_unlimited",
            "android_widget",
            "fair_use_policy"
        ]
    }
]
```

Note: `quota_seconds_daily` of 0 means "not enforced by a fixed daily
limit." Lifetime tier is governed by the fair usage policy.

### POST /api/subscription/upgrade

Initiates an upgrade to a higher tier. Returns a URL to the payment
gateway.

Status: Planned

Auth: Bearer token required

Request body:

```json
{
    "target_tier": "pro"
}
```

Response 200:

```json
{
    "payment_url": "https://app.midtrans.com/snap/v2/vtweb/abc123"
}
```

Errors:

- 400 Target tier is not higher than current tier

### POST /api/subscription/downgrade

Initiates a downgrade to a lower tier. Takes effect at the next billing
cycle.

Status: Planned

Auth: Bearer token required

Request body:

```json
{
    "target_tier": "free"
}
```

Response 200:

```json
{
    "success": true,
    "effective_at": "2026-11-01T00:00:00Z"
}
```

Errors:

- 400 Target tier is not lower than current tier

### GET /api/billing/history

Lists past invoices.

Status: Planned

Auth: Bearer token required

Query parameters:

- `page` (integer, default 1)
- `per_page` (integer, default 20)

Response 200:

```json
[
    {
        "invoice_id": "inv_01HABC",
        "amount_idr": 49000,
        "status": "paid",
        "issued_at": "2026-10-01T10:00:00Z",
        "paid_at": "2026-10-01T10:02:15Z",
        "tier": "pro"
    }
]
```

## Detection History

### GET /api/history

Lists past detection sessions for the authenticated user.

Status: Planned

Auth: Bearer token required

Query parameters:

- `page` (integer, default 1)
- `per_page` (integer, default 20)

Response 200:

```json
[
    {
        "session_id": "ses_01HDEF",
        "started_at": "2026-10-13T15:54:00Z",
        "duration": 42.5,
        "fake_ratio": 0.75,
        "verdict": "fake"
    }
]
```

The `verdict` field is derived from `fake_ratio`:

- `fake_ratio` >= 0.5 -> `fake`
- `fake_ratio` <= 0.1 -> `real`
- otherwise -> `mixed`

### GET /api/history/{session_id}

Returns per-segment detail for one detection session.

Status: Planned

Auth: Bearer token required

Path parameters:

- `session_id` (string)

Response 200:

```json
{
    "session_id": "ses_01HDEF",
    "segments": [
        {
            "offset": 0.0,
            "is_fake": false,
            "fake_prob": 0.08
        },
        {
            "offset": 10.0,
            "is_fake": true,
            "fake_prob": 0.998
        }
    ]
}
```

Errors:

- 404 Session not found

## WebSocket

### WS /ws/audio

Live audio streaming endpoint for real-time deepfake detection.

Status: Implemented

Auth: Planned (will require `?token=<jwt>` in the connection URL)

Protocol:

- Client sends raw audio bytes, any format `soundfile` can decode
  (WAV, FLAC, MP3, M4A)
- Server responds with a JSON text frame per received audio message

Server response:

```json
{
    "real_prob": 0.8317,
    "fake_prob": 0.1683,
    "is_fake": false
}
```

Error response:

```json
{
    "error": "audio ga bisa di-decode"
}
```

Notes:

- OpenAPI does not support WebSocket. This endpoint appears only in this
  Markdown document and is not part of `openapi.yaml`.
- The server processes each received message as one audio chunk. It does
  not accumulate across messages. The client is responsible for segmenting
  audio into fixed durations (for example, 10 seconds per chunk).

## Tier Feature Matrix

| Feature                  | Free | Pro  | Pro Max | Lifetime  |
| ------------------------ | ---- | ---- | ------- | --------- |
| Live detection           | Yes  | Yes  | Yes     | Yes       |
| Daily quota              | 10m  | 5h   | 12h     | Fair use  |
| Confidence score visible | No   | Yes  | Yes     | Yes       |
| Detection history length | 7d   | 30d  | 90d     | Unlimited |
| Android widget           | No   | No   | Yes     | Yes       |
| AI queue priority        | Std  | High | Highest | Highest   |

## Error Response Format

All HTTP errors return JSON in this shape:

```json
{
    "detail": "Human-readable error message"
}
```

The `detail` field is set by FastAPI's `HTTPException` and is safe to
display to end users for 4xx errors. For 5xx errors, log the detail
server-side and show a generic message to the user.

## Change Log

- 0.1.0 (2026-10-13): Initial contract. Health and WebSocket implemented.
  All other endpoints specified as stubs.
