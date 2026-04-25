```python
"""
POST /me/photo — profile photo upload.

Trust boundaries handled:
    1. HTTP request boundary  — size caps, MIME sniffing, extension allowlist,
                                image re-decode (strip metadata / reject payloads).
    2. Storage boundary       — server-generated object key, no client filename,
                                private ACL, server-side encryption.
    3. Auth boundary          — user identity derived from the authenticated
                                principal, never from the request body/query.

This module exposes only `router` and the `PhotoUploadResponse` model.
Wire it into the app with `app.include_router(router)` and provide the four
dependency overrides (`get_current_user`, `get_photo_storage`,
`get_photo_repository`, `get_upload_rate_limiter`) to bind real
implementations. Nothing here reaches out to real infrastructure directly —
that keeps the handler unit-testable without S3, a DB, or an auth provider.
"""

from __future__ import annotations

import io
import logging
import secrets
import uuid
from dataclasses import dataclass
from typing import Protocol

import structlog
from fastapi import APIRouter, Depends, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from PIL import Image, UnidentifiedImageError

log = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Policy constants (externalize to config in production; kept here for clarity)
# ---------------------------------------------------------------------------

# Hard request-body cap. Enforced in-handler as defense-in-depth; the edge
# (ingress / ASGI server) SHOULD also enforce a body-size limit.
MAX_UPLOAD_BYTES: int = 5 * 1024 * 1024        # 5 MiB
MAX_IMAGE_PIXELS: int = 4096 * 4096            # guard against pixel-flood (ASVS 5.2.6)

# Allowlist by *sniffed* format, not by client-declared MIME or extension.
# Pillow's format string is canonical; we map to the normalized MIME we emit.
ALLOWED_IMAGE_FORMATS: dict[str, str] = {
    "JPEG": "image/jpeg",
    "PNG": "image/png",
    "WEBP": "image/webp",
}

# Pillow safety: cap decoder pixel budget to prevent decompression bombs.
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS


# ---------------------------------------------------------------------------
# Domain types
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class AuthenticatedUser:
    """Server-owned identity. Never constructed from request body."""
    id: uuid.UUID


@dataclass(frozen=True)
class NormalizedImage:
    """An image that has been decoded, re-encoded, and stripped of metadata."""
    content: bytes
    mime_type: str
    extension: str        # canonical, from allowlist — never the client filename
    width: int
    height: int


class PhotoUploadResponse(BaseModel):
    """Response projection — only fields the client is allowed to observe."""
    photo_id: uuid.UUID = Field(..., description="Opaque server-assigned ID")
    content_type: str = Field(..., description="Normalized MIME type")
    width: int
    height: int
    bytes: int


# ---------------------------------------------------------------------------
# Injectable collaborators (Protocols — so tests provide fakes, prod provides S3/DB)
# ---------------------------------------------------------------------------

class PhotoStorage(Protocol):
    """Object-storage port. Concrete impl wraps boto3 S3 client."""

    def put_photo(
        self,
        *,
        object_key: str,
        content: bytes,
        content_type: str,
    ) -> None:
        ...


class PhotoRepository(Protocol):
    """Metadata persistence port. Concrete impl writes to the app DB."""

    def record_photo(
        self,
        *,
        user_id: uuid.UUID,
        photo_id: uuid.UUID,
        object_key: str,
        content_type: str,
        byte_size: int,
        width: int,
        height: int,
    ) -> None:
        ...


class UploadRateLimiter(Protocol):
    """Per-user rate limiter. Raises no exceptions; returns a verdict."""

    def check(self, user_id: uuid.UUID) -> bool:
        ...


# ---------------------------------------------------------------------------
# Dependency placeholders — replaced via `app.dependency_overrides` in tests
# and by real wiring in the composition root.
# ---------------------------------------------------------------------------

def get_current_user() -> AuthenticatedUser:  # pragma: no cover - wired in app
    raise NotImplementedError("Override get_current_user in composition root")


def get_photo_storage() -> PhotoStorage:  # pragma: no cover - wired in app
    raise NotImplementedError("Override get_photo_storage in composition root")


def get_photo_repository() -> PhotoRepository:  # pragma: no cover - wired in app
    raise NotImplementedError("Override get_photo_repository in composition root")


def get_upload_rate_limiter() -> UploadRateLimiter:  # pragma: no cover - wired in app
    raise NotImplementedError("Override get_upload_rate_limiter in composition root")


# ---------------------------------------------------------------------------
# Boundary helpers — small, single-purpose, independently testable
# ---------------------------------------------------------------------------

def _read_capped(upload: UploadFile, limit_bytes: int) -> bytes:
    """
    Read the upload stream with a hard cap.

    Why read-by-chunks-with-cap rather than `upload.file.read()`:
    a client can send a Content-Length of 100 bytes and then stream gigabytes.
    We enforce the cap on actual bytes consumed, not on declared length.
    """
    buf = bytearray()
    chunk_size = 64 * 1024
    while True:
        chunk = upload.file.read(chunk_size)
        if not chunk:
            break
        buf.extend(chunk)
        if len(buf) > limit_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Photo exceeds maximum allowed size",
            )
    return bytes(buf)


def _normalize_image(raw: bytes) -> NormalizedImage:
    """
    Decode -> verify -> re-encode. This:
      - validates the bytes are actually the declared image format (magic bytes)
      - strips EXIF/metadata (Confidentiality: no geolocation leak)
      - neutralizes polyglot/embedded-payload files (re-encode drops extras)
      - bounds pixel dimensions (ASVS 5.2.6, pixel-flood)
    """
    try:
        # First pass: verify() catches many malformed images cheaply.
        with Image.open(io.BytesIO(raw)) as probe:
            probe.verify()
        # Second pass: actually decode (verify() invalidates the image object).
        with Image.open(io.BytesIO(raw)) as img:
            fmt = (img.format or "").upper()
            if fmt not in ALLOWED_IMAGE_FORMATS:
                raise HTTPException(
                    status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                    detail="Unsupported image format",
                )
            # Convert palette/alpha modes to a safe baseline before re-encoding.
            safe_mode = "RGB" if fmt == "JPEG" else "RGBA" if img.mode == "RGBA" else "RGB"
            img = img.convert(safe_mode)
            out = io.BytesIO()
            img.save(out, format=fmt)  # re-encode drops metadata and embedded junk
            width, height = img.size
    except UnidentifiedImageError as exc:
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail="File is not a recognized image",
        ) from exc
    except Image.DecompressionBombError as exc:
        # Pillow raises this when pixel budget exceeds MAX_IMAGE_PIXELS.
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Image dimensions exceed maximum allowed",
        ) from exc

    mime = ALLOWED_IMAGE_FORMATS[fmt]
    extension = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}[fmt]
    return NormalizedImage(
        content=out.getvalue(),
        mime_type=mime,
        extension=extension,
        width=width,
        height=height,
    )


def _build_object_key(user_id: uuid.UUID, photo_id: uuid.UUID, extension: str) -> str:
    """
    Construct the S3 object key from *only* server-owned values.

    The client filename is never part of the key — this closes path-traversal
    and zip-slip-adjacent attacks at the storage boundary (ASVS 5.3.2).
    The `secrets` token adds an unguessable segment so keys are not enumerable
    even if user_id and photo_id are known.
    """
    unguessable = secrets.token_urlsafe(16)
    return f"users/{user_id}/profile-photo/{photo_id}-{unguessable}.{extension}"


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

router = APIRouter()


@router.post(
    "/me/photo",
    response_model=PhotoUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload or replace the authenticated user's profile photo",
)
def upload_profile_photo(
    file: UploadFile,
    current_user: AuthenticatedUser = Depends(get_current_user),
    storage: PhotoStorage = Depends(get_photo_storage),
    photos: PhotoRepository = Depends(get_photo_repository),
    rate_limiter: UploadRateLimiter = Depends(get_upload_rate_limiter),
) -> PhotoUploadResponse:
    """
    Accept a profile photo, validate it, store it, and return a projection.

    Note: we deliberately do *not* accept `user_id` from the request — the
    photo is always attached to the authenticated caller (Derived Integrity).
    """
    if not rate_limiter.check(current_user.id):
        log.warning(
            "profile_photo.rate_limited",
            user_id=str(current_user.id),
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many upload attempts; try again later",
        )

    raw = _read_capped(file, MAX_UPLOAD_BYTES)
    if not raw:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Empty upload",
        )

    image = _normalize_image(raw)

    photo_id = uuid.uuid4()
    object_key = _build_object_key(current_user.id, photo_id, image.extension)

    try:
        storage.put_photo(
            object_key=object_key,
            content=image.content,
            content_type=image.mime_type,
        )
    except Exception:
        # Log without the raw bytes or the exception detail in the response.
        log.exception(
            "profile_photo.storage_failed",
            user_id=str(current_user.id),
            photo_id=str(photo_id),
            object_key=object_key,
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Photo storage is temporarily unavailable",
        )

    try:
        photos.record_photo(
            user_id=current_user.id,
            photo_id=photo_id,
            object_key=object_key,
            content_type=image.mime_type,
            byte_size=len(image.content),
            width=image.width,
            height=image.height,
        )
    except Exception:
        # Metadata write failed after a successful object put. Log loudly so
        # an out-of-band reconciliation job can clean up the orphaned object;
        # don't attempt compensating delete here (that itself can fail and
        # obscure the original error).
        log.exception(
            "profile_photo.metadata_failed",
            user_id=str(current_user.id),
            photo_id=str(photo_id),
            object_key=object_key,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Photo could not be finalized",
        )

    log.info(
        "profile_photo.uploaded",
        user_id=str(current_user.id),
        photo_id=str(photo_id),
        content_type=image.mime_type,
        byte_size=len(image.content),
        width=image.width,
        height=image.height,
    )

    return PhotoUploadResponse(
        photo_id=photo_id,
        content_type=image.mime_type,
        width=image.width,
        height=image.height,
        bytes=len(image.content),
    )
```

## Securability Notes

- **SSEM attributes enforced**:
  - *Integrity* — bytes are decoded, re-encoded, and metadata-stripped; object key is built from server-owned values only (Derived Integrity, S6.4.1.1); client filename and client-declared MIME are ignored.
  - *Confidentiality* — response is a projection (`PhotoUploadResponse`); EXIF metadata (geolocation) stripped by re-encode; logs carry IDs, never photo bytes or raw filenames.
  - *Resilience* — streamed read with hard byte cap (defeats lying `Content-Length`); pixel budget guard (`Image.MAX_IMAGE_PIXELS`); specific exception handling per failure class; no bare `except`; partial-failure path between S3 put and DB write is logged explicitly for reconciliation rather than silently compensated.
  - *Testability / Modifiability* — all I/O (auth, S3, DB, rate limit) behind `Protocol` ports with `Depends(...)` placeholders, overridable via `app.dependency_overrides` without touching the handler.
- **ASVS references**:
  - V5.2.1 (size cap), V5.2.2 (magic-byte / re-encode validation), V5.2.6 (pixel-flood guard).
  - V5.3.1 (storage is object store with private ACL — see trade-offs), V5.3.2 (server-generated key, no user-supplied filename).
  - V4.1.1 (Content-Type on response via FastAPI/Pydantic default `application/json`).
  - V7.1 (structured logging of upload events with user_id, photo_id, outcome).
  - V11.1 (per-user rate limiting at the boundary).
- **Trust boundaries**:
  - HTTP -> handler: bytes capped, image decoded/verified/re-encoded, allowlist by sniffed format.
  - Handler -> S3: object key composed from server-owned values + unguessable token; content-type comes from sniffed format, not client.
  - Handler -> DB: only normalized, post-validation values persisted.
  - Identity: `current_user` is always the authenticated caller; no `user_id` parameter accepted.
- **Dependencies**: `fastapi`, `pydantic`, `structlog`, `Pillow` (image decode + re-encode is the single most important defense here; a hand-rolled magic-byte check would pass polyglot files). Pin versions in the project lockfile (`pyproject.toml`/`requirements.txt`); Pillow in particular is CVE-active, so keep it current.
- **Trade-offs a reviewer should revisit**:
  - **Rate limiter is a port, not an implementation.** Pick a shared backing store (Redis, etc.) for multi-instance deployments — an in-process limiter won't bind across replicas.
  - **Private ACL + server-side encryption must be enforced in the S3 client implementation** (bucket policy + `ServerSideEncryption='AES256'` or KMS on `put_object`). The handler intentionally doesn't know about S3 specifics, so this invariant lives in the `PhotoStorage` concrete class and its bucket policy — test for it there.
  - **Antivirus/CDR is out of scope.** Re-encoding an image drops most embedded payloads, but if the threat model includes targeted malware in image containers, add an AV scan step between normalize and `put_photo`.
  - **Orphaned-object handling**: if DB write fails after S3 put, we log and return 500 rather than best-effort delete. A periodic reconciliation job (DB-of-record vs. bucket listing) is the intended cleanup path — flag this for ops.
  - **Content-Length enforcement at ingress is still required.** The in-handler cap is defense-in-depth, not the primary control; without an ingress cap a hostile client can still exhaust upstream buffers.
  - **Authentication is assumed upstream.** `get_current_user` must validate the session/JWT and return a `AuthenticatedUser`; this handler does not re-verify.
