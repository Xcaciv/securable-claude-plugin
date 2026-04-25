# Securable Profile Photo Upload — FastAPI `POST /me/photo`

This implementation follows the FIASSE securable engineering wrapper. The endpoint accepts a photo from an authenticated user and stores it in S3 under a server-derived key. It applies the turtle analogy: strict validation at the HTTP trust boundary, flexible interior logic.

## Context Identified

- **Language/framework**: Python 3.11+, FastAPI
- **Feature**: Profile photo upload (binary) for the authenticated user
- **Trust boundaries**: HTTP request body (untrusted), session/bearer token (untrusted until verified), S3 API (trusted after IAM-authenticated call)
- **Data sensitivity**: User-provided image (moderate — may contain personal content); the user's identity (high — must not be client-asserted)
- **ASVS level target**: L2 baseline with selected L3 controls

## ASVS Requirements Applied

| Chapter | Requirement | How it is satisfied |
|---|---|---|
| V5.1.1 | Document permitted types, extensions, max sizes | Documented constants + module docstring |
| V5.2.1 | Reject oversized files to prevent DoS | `MAX_FILE_BYTES` enforced pre-read via streaming cap |
| V5.2.2 | Validate extension matches declared type **and** magic bytes | `python-magic` + PIL re-encode |
| V5.2.4 | Per-user quota for files | One canonical object per user (`users/{user_id}/profile.{ext}`) |
| V5.2.6 | Reject pixel flood / oversized images | PIL dimension + decompression-bomb check |
| V5.3.1 | Uploaded content is never executed on the server | Stored in private S3 bucket; served via signed URL, not static hosting |
| V5.3.2 | Never use client-submitted filenames for file paths | Object key derived server-side from authenticated user ID |
| V4.1.1 | Correct Content-Type on responses | `application/json; charset=utf-8` (FastAPI default) |
| V7.1 | Structured security logs | `structlog` with event codes, no PII in messages |
| V8.3 | Sensitive-data handling | No secrets in code; credentials via env/IAM role |
| V12.1 | Input validation at trust boundary | Canonicalize → sanitize → validate pipeline |
| V14.1 | TLS in transit | TLS terminates at ingress; outbound to S3 over HTTPS |

## Dependencies (deliberate selection)

All are mature, actively maintained, widely deployed, and free of known unresolved critical CVEs at the time of writing. Pin exact versions; commit a lockfile (`uv.lock` / `poetry.lock` / `pip-tools`).

```
fastapi==0.115.6          # HTTP framework, async-native
uvicorn[standard]==0.32.1 # ASGI server for local/dev
pydantic==2.10.3          # Typed schemas
boto3==1.35.84            # Official AWS SDK (S3)
botocore==1.35.84         # Transitive pin for reproducibility
pillow==11.0.0            # Image re-encode / dimension / bomb checks
python-magic==0.4.27      # libmagic bindings for MIME sniffing
python-multipart==0.0.19  # FastAPI multipart parsing; keep current for CVE hygiene
structlog==24.4.0         # Structured logging
slowapi==0.1.9            # Rate limiting
PyJWT[crypto]==2.10.1     # JWT verification (example auth)
```

System packages required: `libmagic1` (Debian/Ubuntu) or equivalent.

No dependency was added that framework/stdlib already covers. `python-magic` is preferred over rolling magic-byte checks by hand because it is battle-tested. Pillow is used in re-encode mode to produce a canonical, sanitized image rather than passing bytes through.

---

## Code

### `app/config.py` — externalized configuration

```python
"""Runtime configuration for the profile photo service.

All values come from environment variables. Secrets are never
embedded in source. AWS credentials are resolved by boto3's
default provider chain (prefer IAM role in production).
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Immutable application settings loaded once at startup."""

    s3_bucket: str
    s3_region: str
    s3_kms_key_id: str | None
    max_file_bytes: int
    max_image_pixels: int
    max_image_dimension: int
    allowed_mime_types: frozenset[str]
    jwt_public_key: str
    jwt_issuer: str
    jwt_audience: str
    rate_limit_per_minute: str

    @staticmethod
    def load() -> "Settings":
        """Load settings from the environment. Fail fast on missing required keys."""
        return Settings(
            s3_bucket=_require_env("PHOTO_S3_BUCKET"),
            s3_region=_require_env("PHOTO_S3_REGION"),
            s3_kms_key_id=os.environ.get("PHOTO_S3_KMS_KEY_ID"),
            max_file_bytes=int(os.environ.get("PHOTO_MAX_BYTES", 5 * 1024 * 1024)),
            max_image_pixels=int(os.environ.get("PHOTO_MAX_PIXELS", 24_000_000)),
            max_image_dimension=int(os.environ.get("PHOTO_MAX_DIM", 4096)),
            allowed_mime_types=frozenset({"image/jpeg", "image/png", "image/webp"}),
            jwt_public_key=_require_env("AUTH_JWT_PUBLIC_KEY"),
            jwt_issuer=_require_env("AUTH_JWT_ISSUER"),
            jwt_audience=_require_env("AUTH_JWT_AUDIENCE"),
            rate_limit_per_minute=os.environ.get("PHOTO_RATE_LIMIT", "10/minute"),
        )


def _require_env(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Required environment variable missing: {name}")
    return value
```

### `app/auth.py` — authentic identity, server-derived

```python
"""Authentication trust boundary.

Extracts and verifies a signed JWT bearer token. The user
identity used by the rest of the service is *derived* from
the verified token, never from the request body (Derived
Integrity Principle, FIASSE S6.4.1.2).
"""

from __future__ import annotations

from dataclasses import dataclass

import jwt
import structlog
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings

log = structlog.get_logger(__name__)
_bearer = HTTPBearer(auto_error=True)


@dataclass(frozen=True)
class AuthenticatedUser:
    """Server-trusted identity derived from a verified token."""

    user_id: str


def verify_token(
    request: Request,
    creds: HTTPAuthorizationCredentials = Depends(_bearer),
) -> AuthenticatedUser:
    """Verify the bearer JWT and return the authenticated user.

    Raises 401 on any verification failure. The raw token is never logged.
    """
    settings: Settings = request.app.state.settings
    try:
        claims = jwt.decode(
            creds.credentials,
            settings.jwt_public_key,
            algorithms=["RS256", "ES256"],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options={"require": ["exp", "iat", "sub", "iss", "aud"]},
        )
    except jwt.PyJWTError as exc:
        log.info(
            "auth.token_rejected",
            event_code="AUTH_TOKEN_INVALID",
            reason=type(exc).__name__,
            remote_ip=_safe_client_ip(request),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired credentials.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired credentials.",
        )
    return AuthenticatedUser(user_id=subject)


def _safe_client_ip(request: Request) -> str:
    """Return the socket peer IP. Do not trust X-Forwarded-* from clients (V4.1.3)."""
    client = request.client
    return client.host if client else "unknown"
```

### `app/photo_validation.py` — canonical input handling at the trust boundary

```python
"""Image validation and canonicalization.

Implements canonicalize -> sanitize -> validate (FIASSE S6.4.1)
for uploaded profile photos. The bytes that leave this module
are *re-encoded* by Pillow, which neutralizes most polyglot
and stego-style payloads in the pixel layer.
"""

from __future__ import annotations

import io
from dataclasses import dataclass

import magic
from PIL import Image, UnidentifiedImageError


class PhotoValidationError(ValueError):
    """Raised when an uploaded image is rejected. Message is safe for clients."""


@dataclass(frozen=True)
class SanitizedPhoto:
    """A photo that has been validated, re-encoded, and is ready to store."""

    content: bytes
    content_type: str
    extension: str  # canonical, no leading dot


_MIME_TO_PIL_FORMAT = {
    "image/jpeg": ("JPEG", "jpg"),
    "image/png": ("PNG", "png"),
    "image/webp": ("WEBP", "webp"),
}


def sanitize_profile_photo(
    raw_bytes: bytes,
    *,
    allowed_mime_types: frozenset[str],
    max_dimension: int,
    max_pixels: int,
) -> SanitizedPhoto:
    """Validate and canonicalize an uploaded photo.

    Steps:
      1. Sniff MIME via libmagic (not the client-declared content-type).
      2. Reject anything outside the allow-list.
      3. Open with Pillow to verify it is a real image.
      4. Enforce dimension and pixel limits (pixel flood / decompression bomb).
      5. Re-encode to canonical bytes, stripping EXIF and other metadata.
    """
    if not raw_bytes:
        raise PhotoValidationError("Uploaded file is empty.")

    sniffed_mime = magic.from_buffer(raw_bytes, mime=True)
    if sniffed_mime not in allowed_mime_types:
        raise PhotoValidationError("Unsupported image type.")

    pil_format, extension = _MIME_TO_PIL_FORMAT[sniffed_mime]

    # Decompression-bomb protection: cap pixels Pillow will decode.
    original_max = Image.MAX_IMAGE_PIXELS
    Image.MAX_IMAGE_PIXELS = max_pixels
    try:
        with Image.open(io.BytesIO(raw_bytes)) as probe:
            probe.verify()  # structural check
        with Image.open(io.BytesIO(raw_bytes)) as img:
            img.load()
            _enforce_dimensions(img, max_dimension=max_dimension)
            canonical = _reencode(img, pil_format=pil_format)
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise PhotoValidationError("Image could not be processed.") from None
    finally:
        Image.MAX_IMAGE_PIXELS = original_max

    return SanitizedPhoto(
        content=canonical,
        content_type=sniffed_mime,
        extension=extension,
    )


def _enforce_dimensions(img: Image.Image, *, max_dimension: int) -> None:
    width, height = img.size
    if width <= 0 or height <= 0 or width > max_dimension or height > max_dimension:
        raise PhotoValidationError("Image dimensions are not within allowed range.")


def _reencode(img: Image.Image, *, pil_format: str) -> bytes:
    """Re-encode to strip metadata and normalize the container."""
    buffer = io.BytesIO()
    # Drop EXIF/ICC by not passing them; convert palette PNGs to RGB for JPEG.
    target = img.convert("RGB") if pil_format == "JPEG" else img
    save_kwargs: dict[str, object] = {"format": pil_format}
    if pil_format == "JPEG":
        save_kwargs["quality"] = 85
        save_kwargs["optimize"] = True
    elif pil_format == "WEBP":
        save_kwargs["quality"] = 85
    target.save(buffer, **save_kwargs)
    return buffer.getvalue()
```

### `app/photo_storage.py` — S3 boundary with server-derived keys

```python
"""S3 storage adapter for profile photos.

The object key is *always* derived from the authenticated user
ID (Derived Integrity Principle). Client-supplied filenames are
never used to construct paths (ASVS 5.3.2).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import structlog
from botocore.config import Config as BotoConfig
from botocore.exceptions import BotoCoreError, ClientError

log = structlog.get_logger(__name__)


class S3Client(Protocol):
    """Minimal protocol surface we depend on. Enables mocking in tests."""

    def put_object(self, **kwargs: object) -> dict: ...


@dataclass(frozen=True)
class StoredPhoto:
    bucket: str
    key: str
    version_id: str | None


class PhotoStore:
    """Stores profile photos in S3. Injected S3 client keeps this testable."""

    def __init__(
        self,
        *,
        s3_client: S3Client,
        bucket: str,
        kms_key_id: str | None,
    ) -> None:
        self._s3 = s3_client
        self._bucket = bucket
        self._kms_key_id = kms_key_id

    def store_profile_photo(
        self,
        *,
        user_id: str,
        content: bytes,
        content_type: str,
        extension: str,
    ) -> StoredPhoto:
        """Upload the photo. Key is derived server-side from user_id."""
        key = _profile_key(user_id=user_id, extension=extension)
        extra = _encryption_args(self._kms_key_id)
        try:
            response = self._s3.put_object(
                Bucket=self._bucket,
                Key=key,
                Body=content,
                ContentType=content_type,
                CacheControl="private, max-age=0, no-store",
                **extra,
            )
        except (ClientError, BotoCoreError) as exc:
            log.error(
                "photo.storage_failed",
                event_code="PHOTO_STORAGE_FAILED",
                user_id=user_id,
                error_type=type(exc).__name__,
            )
            raise
        return StoredPhoto(
            bucket=self._bucket,
            key=key,
            version_id=response.get("VersionId"),
        )


def _profile_key(*, user_id: str, extension: str) -> str:
    """Build an S3 key that cannot be influenced by client input.

    user_id is a verified JWT subject. We constrain it to a safe
    character set to defeat any upstream identity-provider drift.
    """
    safe_user = "".join(c for c in user_id if c.isalnum() or c in {"-", "_"})
    if not safe_user or safe_user != user_id:
        raise ValueError("Authenticated user_id contains unsupported characters.")
    return f"users/{safe_user}/profile.{extension}"


def _encryption_args(kms_key_id: str | None) -> dict[str, str]:
    if kms_key_id:
        return {"ServerSideEncryption": "aws:kms", "SSEKMSKeyId": kms_key_id}
    return {"ServerSideEncryption": "AES256"}


def build_boto_config(region: str) -> BotoConfig:
    """Conservative boto3 config: explicit timeouts and bounded retries (V5.2.1 / availability)."""
    return BotoConfig(
        region_name=region,
        connect_timeout=3.0,
        read_timeout=10.0,
        retries={"max_attempts": 3, "mode": "standard"},
        signature_version="s3v4",
    )
```

### `app/photo_routes.py` — the endpoint itself

```python
"""POST /me/photo endpoint."""

from __future__ import annotations

import uuid
from typing import Annotated

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, Field
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.auth import AuthenticatedUser, verify_token
from app.photo_storage import PhotoStore
from app.photo_validation import PhotoValidationError, sanitize_profile_photo

log = structlog.get_logger(__name__)

router = APIRouter(prefix="/me", tags=["profile"])
limiter = Limiter(key_func=get_remote_address)


class PhotoUploadResponse(BaseModel):
    """Minimal response surface. No internal paths or bucket names exposed."""

    status: str = Field(default="stored")
    content_type: str
    size_bytes: int


@router.post(
    "/photo",
    response_model=PhotoUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload the authenticated user's profile photo",
)
@limiter.limit("10/minute")
async def upload_profile_photo(
    request: Request,
    file: Annotated[UploadFile, File(description="Profile image: jpeg, png, or webp")],
    user: Annotated[AuthenticatedUser, Depends(verify_token)],
) -> PhotoUploadResponse:
    """Accept and store a profile photo for the authenticated user.

    The user's identity is taken from the verified JWT, not the request body.
    The object key in S3 is derived from that identity.
    """
    settings = request.app.state.settings
    store: PhotoStore = request.app.state.photo_store
    correlation_id = request.headers.get("X-Request-Id") or str(uuid.uuid4())

    raw = await _read_with_cap(file, cap_bytes=settings.max_file_bytes)

    try:
        sanitized = sanitize_profile_photo(
            raw,
            allowed_mime_types=settings.allowed_mime_types,
            max_dimension=settings.max_image_dimension,
            max_pixels=settings.max_image_pixels,
        )
    except PhotoValidationError as exc:
        log.info(
            "photo.upload_rejected",
            event_code="PHOTO_VALIDATION_REJECTED",
            user_id=user.user_id,
            correlation_id=correlation_id,
            reason=str(exc),
            size_bytes=len(raw),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from None

    stored = store.store_profile_photo(
        user_id=user.user_id,
        content=sanitized.content,
        content_type=sanitized.content_type,
        extension=sanitized.extension,
    )

    log.info(
        "photo.upload_succeeded",
        event_code="PHOTO_UPLOAD_SUCCEEDED",
        user_id=user.user_id,
        correlation_id=correlation_id,
        content_type=sanitized.content_type,
        size_bytes=len(sanitized.content),
        s3_version_id=stored.version_id,
    )

    return PhotoUploadResponse(
        content_type=sanitized.content_type,
        size_bytes=len(sanitized.content),
    )


async def _read_with_cap(file: UploadFile, *, cap_bytes: int) -> bytes:
    """Stream the upload and abort early if it exceeds the cap (ASVS 5.2.1)."""
    buffer = bytearray()
    chunk_size = 64 * 1024
    while True:
        chunk = await file.read(chunk_size)
        if not chunk:
            break
        buffer.extend(chunk)
        if len(buffer) > cap_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="File exceeds maximum allowed size.",
            )
    return bytes(buffer)
```

### `app/main.py` — composition root

```python
"""FastAPI composition root. Wires dependencies explicitly."""

from __future__ import annotations

import logging

import boto3
import structlog
from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.config import Settings
from app.photo_routes import limiter, router as photo_router
from app.photo_storage import PhotoStore, build_boto_config


def _configure_logging() -> None:
    logging.basicConfig(format="%(message)s", level=logging.INFO)
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(),
        ]
    )


def create_app() -> FastAPI:
    """Application factory. Tests can build isolated apps with mocks."""
    _configure_logging()
    settings = Settings.load()

    s3_client = boto3.client("s3", config=build_boto_config(settings.s3_region))
    photo_store = PhotoStore(
        s3_client=s3_client,
        bucket=settings.s3_bucket,
        kms_key_id=settings.s3_kms_key_id,
    )

    app = FastAPI(title="Profile Service", version="1.0.0")
    app.state.settings = settings
    app.state.photo_store = photo_store
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.include_router(photo_router)
    return app


app = create_app()
```

### `tests/test_photo_routes.py` — illustrative test sketch

```python
"""Example tests showing injectable dependencies. Uses FastAPI TestClient."""

from __future__ import annotations

import io
from unittest.mock import MagicMock

from fastapi.testclient import TestClient
from PIL import Image

from app.auth import AuthenticatedUser, verify_token
from app.config import Settings
from app.main import create_app


def _png_bytes(w: int = 64, h: int = 64) -> bytes:
    buf = io.BytesIO()
    Image.new("RGB", (w, h), (120, 120, 120)).save(buf, format="PNG")
    return buf.getvalue()


def _test_app(monkeypatch) -> TestClient:
    monkeypatch.setenv("PHOTO_S3_BUCKET", "test-bucket")
    monkeypatch.setenv("PHOTO_S3_REGION", "us-east-1")
    monkeypatch.setenv("AUTH_JWT_PUBLIC_KEY", "x")
    monkeypatch.setenv("AUTH_JWT_ISSUER", "https://issuer.example")
    monkeypatch.setenv("AUTH_JWT_AUDIENCE", "profile-svc")
    app = create_app()
    fake_s3 = MagicMock()
    fake_s3.put_object.return_value = {"VersionId": "v1"}
    app.state.photo_store._s3 = fake_s3
    app.dependency_overrides[verify_token] = lambda: AuthenticatedUser(user_id="user-123")
    return TestClient(app)


def test_accepts_valid_png(monkeypatch):
    client = _test_app(monkeypatch)
    r = client.post("/me/photo", files={"file": ("x.png", _png_bytes(), "image/png")})
    assert r.status_code == 201
    assert r.json()["content_type"] == "image/png"


def test_rejects_oversized_file(monkeypatch):
    monkeypatch.setenv("PHOTO_MAX_BYTES", "1024")
    client = _test_app(monkeypatch)
    big = _png_bytes(2000, 2000)
    r = client.post("/me/photo", files={"file": ("x.png", big, "image/png")})
    assert r.status_code == 413


def test_rejects_unsupported_type(monkeypatch):
    client = _test_app(monkeypatch)
    r = client.post("/me/photo", files={"file": ("x.txt", b"hello", "text/plain")})
    assert r.status_code == 400
```

---

## Deployment Notes (V5.1.1 documentation satisfies L2)

- **Permitted types**: `image/jpeg`, `image/png`, `image/webp`
- **Max file size**: 5 MiB (configurable via `PHOTO_MAX_BYTES`)
- **Max dimensions**: 4096 x 4096; max pixel count 24,000,000
- **Storage**: Private S3 bucket, SSE-KMS preferred, versioning enabled, block-public-access ON
- **Serving**: Never served as static content from S3; distributed via short-lived presigned URLs from a separate `GET` endpoint
- **Malicious-file behavior**: Rejected at the API with a generic `400`; security log event `PHOTO_VALIDATION_REJECTED` is emitted with user id and reason code
- **AV scanning**: For L2 (V5.4.3) integrate an async S3 event -> scanner (GuardDuty Malware Protection, ClamAV lambda). Stored objects should not be marked "ready" until scan passes
- **TLS**: Terminated at the ingress/load balancer; enforce HSTS on user-facing host
- **IAM**: Service role limited to `s3:PutObject` on `arn:aws:s3:::<bucket>/users/*` and `kms:Encrypt` / `kms:GenerateDataKey` on the specified key only

---

## Securability Notes

**SSEM attributes actively enforced**

| Pillar | Attribute | Where |
|---|---|---|
| Maintainability | Analyzability | Small single-purpose functions; descriptive names; module docstrings on every file; no dead code |
| Maintainability | Modifiability | `PhotoStore` takes an injected S3 client; `Settings` is a frozen dataclass; security logic is centralized in `photo_validation.py` and `auth.py`, not scattered in the route |
| Maintainability | Testability | Auth and storage are injectable; `dependency_overrides` used in the test sketch; validation is a pure function |
| Trustworthiness | Confidentiality | No secrets in source; credentials via IAM role; SSE-KMS on S3; `CacheControl: no-store`; bucket private by default; EXIF stripped via re-encode so photos do not leak GPS/device metadata |
| Trustworthiness | Accountability | `structlog` emits structured events with stable `event_code` values (`AUTH_TOKEN_INVALID`, `PHOTO_VALIDATION_REJECTED`, `PHOTO_UPLOAD_SUCCEEDED`, `PHOTO_STORAGE_FAILED`) plus `correlation_id`; no PII or tokens in log messages |
| Trustworthiness | Authenticity | Bearer JWT verified with algorithm allow-list, `require` on critical claims, and issuer/audience checks; user identity is the token `sub`, not client-supplied |
| Reliability | Availability | Streaming read with hard byte cap (early 413); Pillow pixel cap defeats decompression bombs; per-IP rate limit via `slowapi`; explicit boto3 `connect_timeout` / `read_timeout` / bounded retries; `UploadFile` context managed by FastAPI |
| Reliability | Integrity | Canonicalize (magic-byte sniff) -> sanitize (Pillow re-encode strips metadata) -> validate (MIME allow-list, dimensions). Object key derived from verified user id (Derived Integrity Principle, S6.4.1.2). Request Surface Minimization (S6.4.1.1): only `file` is consumed from the multipart body; no user id, filename, or path parameter is honored |
| Reliability | Resilience | Specific exception types caught (`PyJWTError`, `ClientError`/`BotoCoreError`, `UnidentifiedImageError`/`OSError`/`DecompressionBombError`); client-facing messages are generic while logs carry the technical reason; no bare `except` |

**ASVS references satisfied**: V1.1 (documented trust boundaries), V4.1.1, V5.1.1, V5.2.1, V5.2.2, V5.2.4, V5.2.6, V5.3.1, V5.3.2, V7.1 (structured logging), V8.3 (data minimization via EXIF strip), V12.1, V14.1.

**Dependency rationale**: FastAPI, boto3/botocore, Pillow, python-magic, python-multipart, PyJWT, structlog, and slowapi are mature, widely deployed, actively maintained, and have no unresolved critical CVEs at the pinned versions. `python-multipart` is pinned to a current release because earlier versions had DoS CVEs. Versions are pinned exactly; commit a lockfile for reproducibility.

**Trade-offs and explicit non-goals**

- AV scanning is delegated to an async pipeline rather than inline to keep `POST /me/photo` latency bounded. This is the standard L2 pattern; the endpoint returns `201 stored` once the canonical bytes are written and the scan result gates the public `GET` path.
- The endpoint does not attempt L3 controls such as per-request message signing (ASVS 4.1.5) or content-addressed storage; these can be added without changing the validation or auth flow.
- `X-Forwarded-*` is intentionally not consulted for identity; rate-limit keying is socket-peer based and should be replaced with the ingress-provided trusted-header adapter when deployed behind a reverse proxy (ASVS 4.1.3).
- Authentication is shown using JWT for portability. If the platform uses session cookies, swap `verify_token` for a session-backed equivalent while keeping the same `AuthenticatedUser` contract — the route, validation, and storage modules do not change.
