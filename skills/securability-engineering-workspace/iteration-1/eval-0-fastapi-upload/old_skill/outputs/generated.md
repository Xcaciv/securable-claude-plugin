# Profile Photo Upload — `POST /me/photo`

A FastAPI endpoint that accepts a profile photo from an authenticated user and stores it
in S3. Engineered against FIASSE/SSEM constraints and the relevant ASVS V5 (File
Handling), V2 (Authentication), V7 (Logging), V8 (Data Protection), and V12 (Input
Validation) requirements.

## Module layout

The implementation is split into small, single-purpose modules to keep functions short,
testable, and loosely coupled. All four files belong to one Python package; they are
shown as one fenced block per the output spec.

```python
# =============================================================================
# file: app/config.py
# =============================================================================
"""Centralized, externalized configuration.

All security-sensitive values (bucket names, size caps, allowed types) come from
environment variables. No secrets in code (Confidentiality, ASVS V10/V14).
"""
from __future__ import annotations

from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class PhotoUploadSettings(BaseSettings):
    """Profile-photo upload limits and storage configuration.

    Externalized so operators can tune limits without code changes (Modifiability).
    """

    model_config = SettingsConfigDict(env_prefix="PHOTO_", extra="ignore")

    # ASVS 5.2.1 — bound the size the app is willing to process.
    max_bytes: int = Field(default=5 * 1024 * 1024, ge=1, le=50 * 1024 * 1024)

    # ASVS 5.2.6 — pixel-flood protection.
    max_pixels: int = Field(default=4096 * 4096, ge=1)
    max_dimension: int = Field(default=4096, ge=1)

    # S3 / object storage
    s3_bucket: str = Field(min_length=3, max_length=63)
    s3_region: str = Field(default="us-east-1", min_length=2, max_length=32)
    s3_key_prefix: str = Field(default="profile-photos/", max_length=128)
    s3_endpoint_url: str | None = None  # for local/MinIO testing
    s3_request_timeout_seconds: float = Field(default=10.0, gt=0, le=60)


@lru_cache(maxsize=1)
def get_photo_settings() -> PhotoUploadSettings:
    """FastAPI dependency-friendly singleton accessor."""
    return PhotoUploadSettings()  # type: ignore[call-arg]


# =============================================================================
# file: app/logging_setup.py
# =============================================================================
"""Structured logging helper.

Emits JSON-ish structured records so trust-boundary events are queryable
(Transparency, Accountability, ASVS V7).
"""
from __future__ import annotations

import logging
from typing import Any, Mapping

_logger = logging.getLogger("app.profile_photo")


def audit(event: str, *, outcome: str, **fields: Any) -> None:
    """Emit a structured audit record.

    Never log file bytes, raw tokens, or PII. Caller is responsible for passing
    only safe identifiers (subject id, content-type, byte count).
    """
    safe_fields: Mapping[str, Any] = {k: v for k, v in fields.items() if v is not None}
    _logger.info(
        "audit",
        extra={"event": event, "outcome": outcome, "fields": dict(safe_fields)},
    )


# =============================================================================
# file: app/auth.py
# =============================================================================
"""Authentication dependency.

Resolves the calling principal from a bearer token. Centralized so token
verification logic is not scattered (Modifiability, ASVS V2/V3).

The token verifier is injected so production wiring can plug in a real JWT
verifier (e.g., `PyJWT`) and tests can use a fake (Testability).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Annotated, Protocol

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_bearer_scheme = HTTPBearer(auto_error=False)


@dataclass(frozen=True)
class AuthenticatedUser:
    """Server-derived principal. Never populated from request body fields."""

    subject_id: str  # opaque, server-issued user id


class TokenVerifier(Protocol):
    def verify(self, token: str) -> AuthenticatedUser: ...


_verifier: TokenVerifier | None = None


def configure_token_verifier(verifier: TokenVerifier) -> None:
    """Wire the production verifier at app startup; tests can override."""
    global _verifier
    _verifier = verifier


def get_current_user(
    creds: Annotated[
        HTTPAuthorizationCredentials | None, Depends(_bearer_scheme)
    ],
) -> AuthenticatedUser:
    """Trust-boundary check: verify token and derive identity server-side.

    Applies the Derived Integrity Principle — the user id comes from a verified
    token, never from a request field.
    """
    if creds is None or creds.scheme.lower() != "bearer" or not creds.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if _verifier is None:  # configuration error, not a client error
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication is not configured.",
        )
    try:
        return _verifier.verify(creds.credentials)
    except Exception:  # noqa: BLE001 — converted to a generic 401 below
        # Do not leak verification details to the caller (Confidentiality).
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        )


# =============================================================================
# file: app/photo_validation.py
# =============================================================================
"""Canonicalize -> sanitize -> validate for uploaded photo bytes.

Implements ASVS 5.2.1, 5.2.2, 5.2.6 and FIASSE S6.4.1 canonical input handling.
"""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from PIL import Image, UnidentifiedImageError


# Allowlist — explicit, narrow, and tied to a canonical extension/MIME pair.
_ALLOWED_FORMATS: dict[str, tuple[str, str]] = {
    # PIL format -> (canonical extension, canonical content-type)
    "JPEG": (".jpg", "image/jpeg"),
    "PNG": (".png", "image/png"),
    "WEBP": (".webp", "image/webp"),
}


class PhotoValidationError(ValueError):
    """Raised when an uploaded photo fails validation."""


@dataclass(frozen=True)
class ValidatedPhoto:
    """Result of validating an upload — only canonical, server-derived fields."""

    canonical_bytes: bytes
    canonical_extension: str
    canonical_content_type: str
    width: int
    height: int


def validate_and_canonicalize(
    raw_bytes: bytes, *, max_bytes: int, max_dimension: int, max_pixels: int
) -> ValidatedPhoto:
    """Validate magic bytes, dimensions, and re-encode to a canonical image.

    Re-encoding strips EXIF/metadata (Confidentiality / data minimization) and
    normalizes the file (ASVS 5.2.2 image re-writing).
    """
    if not raw_bytes:
        raise PhotoValidationError("Empty upload.")
    if len(raw_bytes) > max_bytes:
        raise PhotoValidationError("File exceeds maximum allowed size.")

    image = _open_image_safely(raw_bytes)
    _enforce_dimensions(image, max_dimension=max_dimension, max_pixels=max_pixels)
    pil_format = (image.format or "").upper()
    if pil_format not in _ALLOWED_FORMATS:
        raise PhotoValidationError("Unsupported image format.")

    extension, content_type = _ALLOWED_FORMATS[pil_format]
    canonical_bytes = _reencode(image, pil_format)
    return ValidatedPhoto(
        canonical_bytes=canonical_bytes,
        canonical_extension=extension,
        canonical_content_type=content_type,
        width=image.width,
        height=image.height,
    )


def _open_image_safely(raw_bytes: bytes) -> Image.Image:
    try:
        image = Image.open(BytesIO(raw_bytes))
        image.verify()  # cheap structural check
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise PhotoValidationError("File is not a valid image.") from exc
    # `verify()` consumes the stream; reopen for actual use.
    return Image.open(BytesIO(raw_bytes))


def _enforce_dimensions(
    image: Image.Image, *, max_dimension: int, max_pixels: int
) -> None:
    width, height = image.size
    if width <= 0 or height <= 0:
        raise PhotoValidationError("Image has invalid dimensions.")
    if width > max_dimension or height > max_dimension:
        raise PhotoValidationError("Image dimensions exceed maximum allowed.")
    if width * height > max_pixels:
        raise PhotoValidationError("Image pixel count exceeds maximum allowed.")


def _reencode(image: Image.Image, pil_format: str) -> bytes:
    """Re-encode the image to strip metadata and normalize content (ASVS 5.2.2)."""
    buffer = BytesIO()
    target = image.convert("RGB") if pil_format == "JPEG" else image
    save_kwargs: dict[str, object] = {"format": pil_format}
    if pil_format == "JPEG":
        save_kwargs["quality"] = 90
        save_kwargs["optimize"] = True
    target.save(buffer, **save_kwargs)
    return buffer.getvalue()


# =============================================================================
# file: app/photo_storage.py
# =============================================================================
"""S3 storage adapter for profile photos.

Encapsulates object-storage details so the route stays thin (Modifiability) and
the storage layer can be mocked in tests (Testability).
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Protocol

from botocore.config import Config as BotoConfig

from app.config import PhotoUploadSettings


@dataclass(frozen=True)
class StoredPhoto:
    bucket: str
    key: str
    content_type: str
    size_bytes: int


class PhotoStore(Protocol):
    def put(
        self,
        *,
        subject_id: str,
        body: bytes,
        content_type: str,
        extension: str,
    ) -> StoredPhoto: ...


class S3PhotoStore:
    """boto3-backed implementation. Construct once at app startup."""

    def __init__(self, settings: PhotoUploadSettings, s3_client=None) -> None:
        self._settings = settings
        self._client = s3_client or self._build_client(settings)

    @staticmethod
    def _build_client(settings: PhotoUploadSettings):
        import boto3  # imported lazily to keep test imports cheap

        boto_config = BotoConfig(
            connect_timeout=settings.s3_request_timeout_seconds,
            read_timeout=settings.s3_request_timeout_seconds,
            retries={"max_attempts": 3, "mode": "standard"},
            signature_version="s3v4",
        )
        return boto3.client(
            "s3",
            region_name=settings.s3_region,
            endpoint_url=settings.s3_endpoint_url,
            config=boto_config,
        )

    def put(
        self,
        *,
        subject_id: str,
        body: bytes,
        content_type: str,
        extension: str,
    ) -> StoredPhoto:
        """Upload bytes under a server-generated key.

        Key is built from server-owned values only (Derived Integrity, ASVS 5.3.2).
        Server-side encryption is requested explicitly (ASVS V8).
        """
        key = self._build_key(subject_id=subject_id, extension=extension)
        self._client.put_object(
            Bucket=self._settings.s3_bucket,
            Key=key,
            Body=body,
            ContentType=content_type,
            ServerSideEncryption="AES256",
            CacheControl="private, max-age=0, no-store",
            Metadata={"subject-id": subject_id},
        )
        return StoredPhoto(
            bucket=self._settings.s3_bucket,
            key=key,
            content_type=content_type,
            size_bytes=len(body),
        )

    def _build_key(self, *, subject_id: str, extension: str) -> str:
        # subject_id is from the verified token; uuid4 is server-generated.
        # Neither value is influenced by client-supplied filenames.
        safe_subject = "".join(ch for ch in subject_id if ch.isalnum() or ch in "-_")
        if not safe_subject:
            raise ValueError("subject_id is not safe for use in an object key.")
        return (
            f"{self._settings.s3_key_prefix.rstrip('/')}"
            f"/{safe_subject}/{uuid.uuid4().hex}{extension}"
        )


# =============================================================================
# file: app/routes_profile_photo.py
# =============================================================================
"""POST /me/photo — profile photo upload endpoint."""
from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field

from app.auth import AuthenticatedUser, get_current_user
from app.config import PhotoUploadSettings, get_photo_settings
from app.logging_setup import audit
from app.photo_storage import PhotoStore, StoredPhoto
from app.photo_validation import (
    PhotoValidationError,
    validate_and_canonicalize,
)

router = APIRouter(tags=["profile"])


class PhotoUploadResponse(BaseModel):
    """Response surface — only server-derived fields are exposed."""

    object_key: str = Field(..., description="Server-generated S3 object key.")
    content_type: str
    size_bytes: int = Field(..., ge=0)
    width: int = Field(..., ge=1)
    height: int = Field(..., ge=1)


_photo_store: PhotoStore | None = None


def configure_photo_store(store: PhotoStore) -> None:
    """Wire the storage adapter at app startup; tests can override."""
    global _photo_store
    _photo_store = store


def _get_photo_store() -> PhotoStore:
    if _photo_store is None:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Photo storage is not configured.",
        )
    return _photo_store


@router.post(
    "/me/photo",
    response_model=PhotoUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload the authenticated user's profile photo.",
)
async def upload_profile_photo(
    file: Annotated[UploadFile, File(..., description="Profile photo file.")],
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    settings: Annotated[PhotoUploadSettings, Depends(get_photo_settings)],
    store: Annotated[PhotoStore, Depends(_get_photo_store)],
) -> PhotoUploadResponse:
    """Validate, canonicalize, and persist the uploaded photo.

    Trust-boundary discipline:
      1. Identity is derived from the verified bearer token, never the body.
      2. Bytes are read with a hard cap (Availability, ASVS 5.2.1).
      3. Content is validated by magic bytes + re-encoded (ASVS 5.2.2).
      4. Storage key is server-generated (Derived Integrity, ASVS 5.3.2).
    """
    raw_bytes = await _read_with_cap(file, max_bytes=settings.max_bytes)
    try:
        validated = validate_and_canonicalize(
            raw_bytes,
            max_bytes=settings.max_bytes,
            max_dimension=settings.max_dimension,
            max_pixels=settings.max_pixels,
        )
    except PhotoValidationError as exc:
        audit(
            "profile_photo.upload",
            outcome="rejected",
            subject_id=user.subject_id,
            reason=str(exc),
            received_bytes=len(raw_bytes),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)
        ) from exc

    stored = _persist(store, user=user, validated=validated)
    audit(
        "profile_photo.upload",
        outcome="accepted",
        subject_id=user.subject_id,
        content_type=stored.content_type,
        size_bytes=stored.size_bytes,
        object_key=stored.key,
    )
    return PhotoUploadResponse(
        object_key=stored.key,
        content_type=stored.content_type,
        size_bytes=stored.size_bytes,
        width=validated.width,
        height=validated.height,
    )


async def _read_with_cap(file: UploadFile, *, max_bytes: int) -> bytes:
    """Read the upload stream, refusing anything beyond `max_bytes`.

    Guards against unbounded memory use even if the client lies about size
    (Availability/Resilience, ASVS 5.2.1).
    """
    chunk_size = 64 * 1024
    buffer = bytearray()
    try:
        while True:
            chunk = await file.read(chunk_size)
            if not chunk:
                break
            buffer.extend(chunk)
            if len(buffer) > max_bytes:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="File exceeds maximum allowed size.",
                )
    finally:
        await file.close()
    return bytes(buffer)


def _persist(
    store: PhotoStore,
    *,
    user: AuthenticatedUser,
    validated,
) -> StoredPhoto:
    """Wrap the storage call so transport errors map to a stable 502."""
    try:
        return store.put(
            subject_id=user.subject_id,
            body=validated.canonical_bytes,
            content_type=validated.canonical_content_type,
            extension=validated.canonical_extension,
        )
    except Exception as exc:  # noqa: BLE001 — re-raised as a sanitized 502
        audit(
            "profile_photo.upload",
            outcome="storage_error",
            subject_id=user.subject_id,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not store the uploaded photo. Please try again.",
        ) from exc
```

## Suggested `pyproject.toml` dependencies

Pin to current latest-stable, low-CVE-exposure releases and use a lockfile
(`uv.lock` / `poetry.lock` / `pip-tools` `requirements.txt`) for reproducible
builds.

```python
# Recommended pins (latest stable as of 2026-04):
# fastapi          >=0.115,<0.116
# pydantic         >=2.9,<3
# pydantic-settings>=2.5,<3
# python-multipart >=0.0.18,<0.1   # required by FastAPI for UploadFile
# pillow           >=11.0,<12       # actively maintained image lib
# boto3            >=1.35,<2
# botocore         >=1.35,<2
```

## Securability Notes

**SSEM attributes actively enforced**

- *Analyzability* — Each function is small (well under 30 LoC), single-purpose, and
  named for intent (`validate_and_canonicalize`, `_read_with_cap`, `_build_key`).
- *Modifiability* — Auth verification (`TokenVerifier`), storage (`PhotoStore`), and
  configuration (`PhotoUploadSettings`) are interface-driven and externalized.
  Security logic is centralized in dedicated modules, not scattered through the
  route handler.
- *Testability* — `configure_token_verifier` and `configure_photo_store` allow tests
  to inject fakes; `validate_and_canonicalize` is a pure function operating on
  bytes; the route depends on protocols, not concrete classes.
- *Confidentiality* — Re-encoding strips EXIF/GPS metadata (data minimization);
  no token, byte content, or PII is ever logged; objects are uploaded with
  `ServerSideEncryption=AES256` and `Cache-Control: private, no-store`; auth
  failures return generic messages.
- *Accountability* — Every accept/reject/storage-error path emits a structured
  `audit` record keyed by `event` + `outcome` with subject id, byte count, and
  object key (no payload data).
- *Authenticity* — Identity is taken from a verified bearer token via
  `HTTPBearer` + injected `TokenVerifier`; the request body cannot supply or
  override `subject_id` (Derived Integrity).
- *Availability* — Hard byte cap enforced by streaming read with chunked
  accumulation; pixel and dimension caps prevent decompression bombs; boto3
  client is configured with explicit connect/read timeouts and bounded retries.
- *Integrity* — Canonicalize -> sanitize -> validate is applied: magic-byte
  check via PIL, allowlisted formats, full re-encode, server-generated S3 key
  built from a sanitized subject id and a `uuid4` (no client filename ever
  reaches the storage path).
- *Resilience* — Specific exception types are caught (`PhotoValidationError`,
  `UnidentifiedImageError`, `OSError`); storage failures are translated to a
  stable 502 without leaking internals; `UploadFile` is closed in a `finally`
  block to avoid file-handle leaks.

**ASVS coverage**

- V2.1 / V3 — Bearer-token auth via `HTTPBearer`; identity is server-derived.
- V5.1.1 — Permitted formats (JPEG/PNG/WEBP), size cap, and rejection behavior
  are explicit in code and configuration.
- V5.2.1 — Streaming read enforces `max_bytes` before any processing.
- V5.2.2 — Magic-byte check + image re-write via Pillow.
- V5.2.4 — Per-user storage prefix supports per-user quotas at the storage
  layer (lifecycle/quotas configured in S3 outside this code).
- V5.2.6 — Pixel-flood protection via `max_dimension` and `max_pixels`.
- V5.3.1 — Bucket is private; objects are not served via a public web root.
- V5.3.2 — Object keys are constructed from server-owned values only; client
  filenames are never used.
- V7 (Logging) — Structured audit events at every trust-boundary outcome,
  with no sensitive payload data.
- V8 / V14 — Server-side encryption (`AES256`) and `s3v4` signing; the bucket
  is expected to enforce TLS via bucket policy.
- V12 (Input Validation) — Allowlisted formats, dimension and size limits,
  canonical re-encoding.

**Dependency selection rationale**

- `fastapi` / `pydantic` / `pydantic-settings` — Current stable line; widely
  used, actively maintained, strong release cadence.
- `pillow` — Pinned to the current major (`>=11`) which contains fixes for
  prior image-decoder CVEs; older Pillow lines are avoided.
- `boto3` / `botocore` — AWS-maintained, frequent releases; configured with
  explicit timeouts and bounded retries to prevent hangs.
- `python-multipart` >=0.0.18 — Versions <0.0.18 had a DoS CVE in form
  parsing; this floor avoids it.
- No additional file-type or AV libraries are introduced; magic-byte and
  re-encoding via Pillow are sufficient for the documented threat model.
  Versions are pinned via upper bounds and a lockfile is expected.

**Trade-offs**

- The endpoint loads the full file into memory up to `max_bytes` to allow
  Pillow validation. For larger limits this should move to a temporary file
  with the same hard cap.
- Per-user quota enforcement (ASVS 5.2.4 L3) is delegated to S3 lifecycle and
  application-level accounting; this handler enforces only per-request limits.
- AV scanning is not performed inline. For higher assurance, store the object
  in a quarantine prefix and gate publication on an async scanner result.
