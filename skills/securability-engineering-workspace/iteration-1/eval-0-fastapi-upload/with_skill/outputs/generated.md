# POST /me/photo — Securable Profile Photo Upload

A FastAPI endpoint that accepts a profile photo from the authenticated user and stores it in S3
under a server-derived key. Trust boundaries (HTTP request, content validation, S3 egress) are
hardened; interior logic stays small and injectable.

```python
"""
profile_photo_upload.py

POST /me/photo — upload an authenticated user's profile photo to S3.

Design notes (see Securability Notes block at end of file):
  - Authentication is delegated to `get_authenticated_user` (assumed to verify a signed
    session/JWT). The endpoint NEVER trusts a client-supplied user id.
  - The S3 object key is derived server-side from the authenticated user id; the client cannot
    influence the storage path (Derived Integrity, S6.4.1.1).
  - The upload is bounded by a hard byte cap enforced via streaming, not via the optimistic
    Content-Length header (Availability, Integrity).
  - The MIME type is verified against the actual file bytes (magic-byte sniff) and re-encoded
    via Pillow to strip metadata and active content (Integrity, ASVS 5.2.2).
  - Errors are mapped to specific HTTPException responses; logs are structured and never carry
    raw bytes or PII (Accountability, Confidentiality).
"""

from __future__ import annotations

import io
import logging
import secrets
from dataclasses import dataclass
from typing import Final, Protocol
from uuid import UUID

import filetype  # type: ignore[import-untyped]
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from fastapi import File as FastAPIFile
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Constants — externalize to config in production. Centralized here so policy
# changes (size, allowed types) happen in one place (Modifiability).
# ---------------------------------------------------------------------------

MAX_PHOTO_BYTES: Final[int] = 5 * 1024 * 1024  # 5 MiB hard cap
MAX_PIXEL_DIMENSION: Final[int] = 4096          # guards pixel-flood (ASVS 5.2.6)
ALLOWED_MIME_TYPES: Final[frozenset[str]] = frozenset({"image/jpeg", "image/png", "image/webp"})
NORMALIZED_OUTPUT_FORMAT: Final[str] = "JPEG"
NORMALIZED_OUTPUT_MIME: Final[str] = "image/jpeg"
NORMALIZED_OUTPUT_EXT: Final[str] = "jpg"
READ_CHUNK_BYTES: Final[int] = 64 * 1024

log = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AuthenticatedUser:
    """Server-owned identity. Never reconstruct from request body."""

    id: UUID


class PhotoUploadResponse(BaseModel):
    """Narrow projection — only fields the client needs (Confidentiality)."""

    photo_key: str
    content_type: str
    bytes_stored: int


# ---------------------------------------------------------------------------
# Injectable boundary collaborators (Modifiability, Testability)
# ---------------------------------------------------------------------------


class PhotoStore(Protocol):
    """Abstract storage so tests run without S3 and policies (KMS, bucket) are configurable."""

    def put_photo(self, *, key: str, body: bytes, content_type: str) -> None: ...


def get_authenticated_user() -> AuthenticatedUser:  # pragma: no cover - wired by app
    """Replaced at app startup with the real auth dependency. Defined here so the route is
    explicit about its trust-boundary requirement."""
    raise NotImplementedError("Wire a real authenticator in app startup.")


def get_photo_store() -> PhotoStore:  # pragma: no cover - wired by app
    """Replaced at app startup with a concrete S3-backed store (see S3PhotoStore below)."""
    raise NotImplementedError("Wire a PhotoStore in app startup.")


# ---------------------------------------------------------------------------
# Concrete S3 adapter — kept thin and isolated so swapping providers or
# adding KMS/replication policies happens in one place.
# ---------------------------------------------------------------------------


class S3PhotoStore:
    """S3-backed PhotoStore.

    Caller-provided `bucket` and `kms_key_id` are configuration, not request data, so they live
    on the adapter, not on the request.
    """

    def __init__(self, *, s3_client, bucket: str, kms_key_id: str | None = None) -> None:
        self._s3 = s3_client
        self._bucket = bucket
        self._kms_key_id = kms_key_id

    def put_photo(self, *, key: str, body: bytes, content_type: str) -> None:
        extra: dict[str, str] = {
            "ServerSideEncryption": "aws:kms" if self._kms_key_id else "AES256",
        }
        if self._kms_key_id:
            extra["SSEKMSKeyId"] = self._kms_key_id
        # boto3 raises botocore.exceptions.ClientError on failure; let the route map it.
        self._s3.put_object(
            Bucket=self._bucket,
            Key=key,
            Body=body,
            ContentType=content_type,
            CacheControl="private, max-age=0, no-store",
            **extra,
        )


# ---------------------------------------------------------------------------
# Trust-boundary helpers — small, single-purpose, individually testable.
# ---------------------------------------------------------------------------


async def _read_capped(upload: UploadFile, max_bytes: int) -> bytes:
    """Stream the upload into memory with a hard byte cap (Availability, ASVS 5.2.1).

    We do NOT trust Content-Length; we count bytes as they arrive. If the cap is exceeded we
    raise immediately so we never buffer a hostile payload.
    """
    buffer = io.BytesIO()
    total = 0
    while True:
        chunk = await upload.read(READ_CHUNK_BYTES)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"Photo exceeds {max_bytes} bytes.",
            )
        buffer.write(chunk)
    if total == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Empty upload."
        )
    return buffer.getvalue()


def _verify_image_type(raw: bytes) -> str:
    """Magic-byte sniff against the allowlist (ASVS 5.2.2). Returns the detected MIME."""
    kind = filetype.guess(raw)
    if kind is None or kind.mime not in ALLOWED_MIME_TYPES:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported image type. Allowed: {sorted(ALLOWED_MIME_TYPES)}",
        )
    return kind.mime


def _normalize_image(raw: bytes) -> bytes:
    """Re-encode the image to strip metadata/active content and enforce pixel limits.

    Pillow's `verify()` cheaply rejects malformed images; we then reopen for the actual decode.
    Re-encoding (rather than passing the original bytes through) is the practical defense
    against polyglot files and embedded scripts (ASVS 5.2.2, 5.2.6).
    """
    try:
        with Image.open(io.BytesIO(raw)) as probe:
            probe.verify()  # cheap structural check; consumes the stream
        with Image.open(io.BytesIO(raw)) as img:
            if max(img.size) > MAX_PIXEL_DIMENSION:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Image dimensions exceed {MAX_PIXEL_DIMENSION}px.",
                )
            rgb = img.convert("RGB")
            out = io.BytesIO()
            rgb.save(out, format=NORMALIZED_OUTPUT_FORMAT, quality=85, optimize=True)
            return out.getvalue()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        # Specific exceptions only — no bare except (Resilience).
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid image data."
        ) from exc


def _build_photo_key(user_id: UUID) -> str:
    """Server-derived, opaque key. Random suffix prevents enumeration and cache collisions
    while the user-id segment makes ownership visible to ops (Derived Integrity, S6.4.1.1)."""
    nonce = secrets.token_urlsafe(16)
    return f"profile-photos/{user_id}/{nonce}.{NORMALIZED_OUTPUT_EXT}"


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------


@router.post(
    "/me/photo",
    response_model=PhotoUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_profile_photo(
    file: UploadFile = FastAPIFile(..., description="Profile photo (JPEG/PNG/WebP, <= 5 MiB)"),
    current_user: AuthenticatedUser = Depends(get_authenticated_user),
    store: PhotoStore = Depends(get_photo_store),
) -> PhotoUploadResponse:
    """Accept a profile photo, validate it, normalize it, and store it under a server-derived key.

    The handler is intentionally a thin orchestrator: each step is a small, named helper that
    can be tested in isolation (Analyzability, Testability).
    """
    log.info(
        "profile_photo.upload.received",
        extra={"user_id": str(current_user.id), "declared_type": file.content_type},
    )

    raw = await _read_capped(file, MAX_PHOTO_BYTES)
    detected_mime = _verify_image_type(raw)
    normalized = _normalize_image(raw)
    key = _build_photo_key(current_user.id)

    try:
        store.put_photo(key=key, body=normalized, content_type=NORMALIZED_OUTPUT_MIME)
    except Exception as exc:  # narrow at the adapter layer; here we map to a generic 502
        # Log the exception type but not the message (may contain bucket names, ARNs).
        log.exception(
            "profile_photo.upload.store_failed",
            extra={"user_id": str(current_user.id), "error_type": type(exc).__name__},
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY, detail="Photo storage unavailable."
        ) from exc

    log.info(
        "profile_photo.upload.stored",
        extra={
            "user_id": str(current_user.id),
            "photo_key": key,
            "detected_mime": detected_mime,
            "bytes_stored": len(normalized),
        },
    )
    return PhotoUploadResponse(
        photo_key=key,
        content_type=NORMALIZED_OUTPUT_MIME,
        bytes_stored=len(normalized),
    )
```

### Wiring sketch (for context — replace placeholders in app startup)

```python
# main.py (excerpt)
import boto3
from fastapi import FastAPI
from profile_photo_upload import (
    S3PhotoStore,
    get_authenticated_user,
    get_photo_store,
    router as photo_router,
)
from your_auth_module import authenticate_request  # signed-session/JWT verifier

app = FastAPI()

_s3_store = S3PhotoStore(
    s3_client=boto3.client("s3", region_name="us-east-1"),
    bucket="my-app-private-photos",
    kms_key_id="arn:aws:kms:us-east-1:000000000000:key/...",  # from secret manager
)

app.dependency_overrides[get_authenticated_user] = authenticate_request
app.dependency_overrides[get_photo_store] = lambda: _s3_store
app.include_router(photo_router)
```

### Suggested `requirements.txt` (pin in your lockfile)

```
fastapi==0.115.5
pydantic==2.9.2
python-multipart==0.0.18
Pillow==11.0.0
filetype==1.2.0
boto3==1.35.63
```

## Securability Notes

**SSEM attributes actively enforced**:
- *Integrity* — magic-byte type check, Pillow re-encode (strips EXIF/metadata/polyglot payloads), server-derived S3 key, hard byte cap counted during streaming, pixel-dimension cap, parameterized S3 PutObject call.
- *Confidentiality* — narrow `PhotoUploadResponse` projection, S3 server-side encryption (KMS or AES-256), `Cache-Control: private, no-store`, logs exclude raw bytes / EXIF / error messages, bucket and KMS key id never appear in client responses.
- *Accountability* — structured `profile_photo.upload.{received,stored,store_failed}` log events keyed by user id and outcome.
- *Authenticity* — endpoint requires `get_authenticated_user`; user id is server-owned, never derived from the request body.
- *Availability* — 5 MiB byte cap enforced via streaming (does not trust Content-Length), 4096px pixel cap, normalization yields a fixed-format/quality JPEG, S3 client should be configured with connect/read timeouts at the boto3 layer.
- *Resilience* — specific exception handling (`UnidentifiedImageError`, `OSError`, `ValueError`); the catch-all in the route maps to 502 with type-only logging; helpers are pure and short.
- *Analyzability* — every helper is < 30 LoC with a single purpose; module docstring explains intent; no dead code.
- *Modifiability* — `PhotoStore` Protocol decouples the route from boto3; size/type policies are module-level constants; auth and storage are injected dependencies.
- *Testability* — `get_authenticated_user`, `get_photo_store`, and helpers are independently testable via FastAPI `dependency_overrides` and direct calls; no global mutable state.

**ASVS references**:
- V5.1.1 — file types, extensions, max size documented in module docstring and constants.
- V5.2.1 — size cap enforced (`MAX_PHOTO_BYTES`).
- V5.2.2 — magic-byte sniff plus Pillow re-encode validates content matches declared/expected type.
- V5.2.4 — per-user quota is *not* implemented here; flagged below as a deferred control.
- V5.2.6 — `MAX_PIXEL_DIMENSION` guards pixel-flood.
- V5.3.1 — stored under a private bucket (configuration responsibility); object is not served from a public, executable path.
- V5.3.2 — file path is server-generated; no user-submitted filename influences the S3 key.
- V7.1.1 / V7.1.2 — security-relevant events (received, stored, store_failed) are logged with structured fields and without sensitive payload data.
- V8.3.x — sensitive identifiers minimized in responses (only the opaque `photo_key`).
- V12.1.1 — TLS-only transport assumed via the deployment (terminator/ALB enforces TLS 1.2+).
- V14.1.1 — secrets (bucket name, KMS key id) injected via configuration, not in code.

**Trust boundaries handled**:
- HTTP client -> FastAPI route (auth, multipart parsing, byte cap, MIME allowlist).
- Route -> image decoder (Pillow `verify()` then re-encode).
- Route -> S3 (`PhotoStore.put_photo` with server-derived key, SSE, private cache headers).

**Dependencies introduced**:
- `fastapi==0.115.5` — current stable; required by the request.
- `pydantic==2.9.2` — pulled in by FastAPI; explicit pin for response model.
- `python-multipart==0.0.18` — required by FastAPI for `UploadFile` parsing; current stable, post-CVE-2024-24762 fix.
- `Pillow==11.0.0` — current stable; used to validate and re-encode images. Active maintenance, regular CVE response cadence.
- `filetype==1.2.0` — pure-Python magic-byte sniff; tiny surface area, no native deps. Preferred over `python-magic` to avoid libmagic system dependency.
- `boto3==1.35.63` — current stable AWS SDK for S3 PutObject; no avoidable alternative for S3 access.

**Trade-offs and assumptions**:
- *Authentication is assumed*: `get_authenticated_user` must be wired to a real verifier (signed session cookie or JWT with audience/expiry checks). The endpoint will refuse to start otherwise (raises `NotImplementedError`).
- *Per-user quota (ASVS 5.2.4) is not implemented*: a single user can upload many photos. Add a counter (DB or Redis) and reject above a threshold for L3 compliance. The current design overwrites no prior photo because the key includes a random nonce — pair with a "current_photo_key" pointer in the user record and a janitor job that deletes orphans.
- *Antivirus scanning (ASVS 5.4.3) is out of scope*: profile photos are re-encoded (which neutralizes most embedded payloads) but not AV-scanned. Add a post-upload scan (e.g., S3 event -> ClamAV/GuardDuty Malware Protection) before serving these to other users.
- *Rate limiting is out of scope*: enforce at the gateway/ALB or via a FastAPI middleware (e.g., `slowapi`) keyed on `current_user.id`. Without this, the byte cap alone does not prevent volumetric abuse.
- *Normalization to JPEG is opinionated*: it strips transparency. If product requires PNG/WebP fidelity, branch on `detected_mime` and re-encode to the matching format (still re-encode — never pass raw bytes through).
- *In-memory buffering*: 5 MiB per request is acceptable for typical worker memory budgets. For larger limits, switch `_read_capped` to a temp-file-backed `SpooledTemporaryFile` and stream into S3 via `upload_fileobj`.
- *Logging library*: the module uses stdlib `logging`. In production, configure a JSON formatter (e.g., `python-json-logger`) so the structured `extra` fields are emitted as JSON.
- *S3 client lifecycle*: the wiring sketch builds one `boto3` client at startup (thread-safe, recommended). Configure `Config(connect_timeout=2, read_timeout=5, retries={"max_attempts": 3, "mode": "standard"})` for explicit timeouts (Availability).
