# Express JWT Authentication Middleware (TypeScript, HS256)

A drop-in Express middleware that verifies a `Bearer` JWT signed with HS256, attaches a minimal verified identity to `req.user`, and returns a generic 401 for anything that doesn't pass.

## Implementation

### `src/auth/jwt-config.ts`

Centralizes the secret and verification policy in one place. Loaded once at startup so the secret never lives in a request-handling code path. Fail-fast at boot rather than fail-open at request time.

```typescript
import { createSecretKey, type KeyObject } from "node:crypto";

/**
 * Verification policy for HS256 access tokens.
 * Build once at process start; treat the resulting object as immutable.
 */
export interface JwtVerificationPolicy {
  /** Symmetric key derived from process.env.JWT_SECRET. Never logged. */
  readonly key: KeyObject;
  /** Algorithm allowlist. HS256 only — guards against alg-confusion (V9.1.2). */
  readonly algorithms: readonly ["HS256"];
  /** Expected issuer (iss). Optional in this build but configurable. */
  readonly issuer?: string;
  /** Expected audience (aud). Optional in this build but configurable. */
  readonly audience?: string;
  /** Clock skew tolerance in seconds for nbf/exp checks. */
  readonly clockToleranceSeconds: number;
}

const MIN_HS256_SECRET_BYTES = 32; // 256-bit MAC key — RFC 7518 §3.2 floor.

/**
 * Build the verification policy from environment configuration.
 * Throws at boot if JWT_SECRET is missing or too short — preferred over
 * silently accepting a weak key (Resilience: fail closed, not open).
 */
export function loadJwtVerificationPolicy(
  env: NodeJS.ProcessEnv = process.env,
): JwtVerificationPolicy {
  const secret = env.JWT_SECRET;
  if (typeof secret !== "string" || secret.length === 0) {
    throw new Error("JWT_SECRET is not set");
  }
  // Treat as raw UTF-8 bytes; reject obviously-too-short keys.
  if (Buffer.byteLength(secret, "utf8") < MIN_HS256_SECRET_BYTES) {
    throw new Error(
      `JWT_SECRET must be at least ${MIN_HS256_SECRET_BYTES} bytes for HS256`,
    );
  }
  return Object.freeze({
    key: createSecretKey(Buffer.from(secret, "utf8")),
    algorithms: ["HS256"] as const,
    issuer: env.JWT_ISSUER || undefined,
    audience: env.JWT_AUDIENCE || undefined,
    clockToleranceSeconds: 5,
  });
}
```

### `src/auth/extract-bearer.ts`

Boundary parsing isolated into a pure function — easy to unit-test with hostile inputs. Handles RFC 6750 / RFC 7235 case-insensitivity, whitespace, and Express's array-valued header shape without leaking those shapes downstream.

```typescript
const BEARER_SCHEME = /^bearer$/i; // RFC 6750: scheme token is case-insensitive.

/**
 * Extract a bearer token from a raw Authorization header value.
 * Returns null for any shape that is not a single, well-formed `Bearer <token>`.
 * No exception is thrown — the caller decides how to respond at the boundary.
 */
export function extractBearerToken(
  headerValue: string | string[] | undefined,
): string | null {
  // Reject duplicate Authorization headers outright — ambiguous and unusual.
  if (Array.isArray(headerValue)) return null;
  if (typeof headerValue !== "string") return null;

  // Trim incidental whitespace (proxies, copy-paste); reject empty.
  const trimmed = headerValue.trim();
  if (trimmed.length === 0) return null;

  // Split into exactly two parts on the first run of whitespace.
  const firstSpace = trimmed.search(/\s+/);
  if (firstSpace <= 0) return null;
  const scheme = trimmed.slice(0, firstSpace);
  const credentials = trimmed.slice(firstSpace).trim();

  if (!BEARER_SCHEME.test(scheme)) return null;
  if (credentials.length === 0) return null;
  // Defense in depth: the token itself must not contain whitespace.
  if (/\s/.test(credentials)) return null;

  return credentials;
}
```

### `src/auth/jwt-middleware.ts`

The middleware: small, single-purpose, dependency-injected, and uses the `jose` library for verification (active maintenance, no historical algorithm-confusion CVEs in current major versions, first-class TypeScript types, native `crypto` under the hood).

```typescript
import type { NextFunction, Request, Response } from "express";
import { errors as joseErrors, jwtVerify, type JWTPayload } from "jose";

import { extractBearerToken } from "./extract-bearer.js";
import type { JwtVerificationPolicy } from "./jwt-config.js";

/** Minimal verified identity attached to req.user. */
export interface AuthenticatedUser {
  /** Stable subject identifier (JWT 'sub' claim). */
  readonly id: string;
  /** Issuer (JWT 'iss' claim) when present — useful with multiple IdPs. */
  readonly issuer?: string;
}

/** Structured logger contract — bring your own (pino, winston, console). */
export interface AuthLogger {
  info(event: string, fields: Record<string, unknown>): void;
  warn(event: string, fields: Record<string, unknown>): void;
}

export interface JwtAuthMiddlewareOptions {
  readonly policy: JwtVerificationPolicy;
  readonly logger: AuthLogger;
  /** Override for tests — defaults to jose's jwtVerify. */
  readonly verify?: typeof jwtVerify;
}

// Express type augmentation kept local — apps can re-export as needed.
declare module "express-serve-static-core" {
  interface Request {
    user?: AuthenticatedUser;
  }
}

/**
 * Build an Express middleware that authenticates requests via an HS256 JWT
 * in the Authorization header. Rejects with a generic 401 on any failure —
 * specific failure reasons are logged, never returned to the client.
 */
export function buildJwtAuthMiddleware(opts: JwtAuthMiddlewareOptions) {
  const { policy, logger } = opts;
  const verify = opts.verify ?? jwtVerify;

  return async function jwtAuthMiddleware(
    req: Request,
    res: Response,
    next: NextFunction,
  ): Promise<void> {
    // Normalize header name retrieval — Express lowercases header keys.
    const token = extractBearerToken(req.headers.authorization);
    if (token === null) {
      logger.info("auth.jwt.rejected", {
        reason: "missing_or_malformed_authorization_header",
        request_id: req.header("x-request-id"),
        path: req.path,
        method: req.method,
      });
      sendUnauthorized(res);
      return;
    }

    try {
      const { payload } = await verify(token, policy.key, {
        algorithms: [...policy.algorithms],
        issuer: policy.issuer,
        audience: policy.audience,
        clockTolerance: policy.clockToleranceSeconds,
        // jose enforces exp/nbf automatically; typ defaults to JWT.
      });

      const user = projectAuthenticatedUser(payload);
      if (user === null) {
        logger.warn("auth.jwt.rejected", {
          reason: "missing_subject_claim",
          request_id: req.header("x-request-id"),
        });
        sendUnauthorized(res);
        return;
      }

      req.user = user;
      logger.info("auth.jwt.accepted", {
        user_id: user.id,
        issuer: user.issuer,
        request_id: req.header("x-request-id"),
        path: req.path,
        method: req.method,
      });
      next();
    } catch (err: unknown) {
      logger.info("auth.jwt.rejected", {
        reason: classifyVerifyError(err),
        request_id: req.header("x-request-id"),
        path: req.path,
        method: req.method,
      });
      sendUnauthorized(res);
    }
  };
}

/**
 * Project the verified JWT payload into the minimal server-owned identity
 * shape. Applies Request Surface Minimization — only `sub` and `iss` are
 * lifted; nothing else from the token is exposed to downstream handlers.
 */
function projectAuthenticatedUser(payload: JWTPayload): AuthenticatedUser | null {
  if (typeof payload.sub !== "string" || payload.sub.length === 0) return null;
  return Object.freeze({
    id: payload.sub,
    issuer: typeof payload.iss === "string" ? payload.iss : undefined,
  });
}

/** Map jose error classes to short, log-safe reason codes. */
function classifyVerifyError(err: unknown): string {
  if (err instanceof joseErrors.JWTExpired) return "expired";
  if (err instanceof joseErrors.JWTClaimValidationFailed) return "claim_invalid";
  if (err instanceof joseErrors.JWSSignatureVerificationFailed) return "bad_signature";
  if (err instanceof joseErrors.JWSInvalid) return "malformed_jws";
  if (err instanceof joseErrors.JWTInvalid) return "malformed_jwt";
  if (err instanceof joseErrors.JOSEAlgNotAllowed) return "algorithm_not_allowed";
  return "verify_failed";
}

function sendUnauthorized(res: Response): void {
  // Generic message — never leak which check failed (V16.5.1).
  res
    .status(401)
    .set("WWW-Authenticate", 'Bearer realm="api", error="invalid_token"')
    .json({ error: "unauthorized" });
}
```

### `src/auth/index.ts`

Public surface — keeps consumers off internal modules.

```typescript
export { buildJwtAuthMiddleware } from "./jwt-middleware.js";
export type {
  AuthenticatedUser,
  AuthLogger,
  JwtAuthMiddlewareOptions,
} from "./jwt-middleware.js";
export { loadJwtVerificationPolicy } from "./jwt-config.js";
export type { JwtVerificationPolicy } from "./jwt-config.js";
```

### Usage

```typescript
import express from "express";
import {
  buildJwtAuthMiddleware,
  loadJwtVerificationPolicy,
} from "./auth/index.js";

const app = express();

// Build once, at startup, so any config error fails the boot — not a request.
const policy = loadJwtVerificationPolicy();
const requireAuth = buildJwtAuthMiddleware({
  policy,
  logger: console as unknown as import("./auth/index.js").AuthLogger,
});

app.get("/me", requireAuth, (req, res) => {
  // req.user is the verified, minimal identity — never trust other claims here.
  res.json({ id: req.user!.id });
});
```

### Dependency notes

- `jose@^5` — actively maintained, TypeScript-first, no `alg: none` accepted, requires explicit `algorithms` allowlist (matches V9.1.2). Pin via `package.json` and commit `package-lock.json`.
- No other runtime dependencies introduced.
- `npm install jose@^5` and run `npm audit` (or `npm audit --omit=dev`) in CI before each release.

### Suggested test cases (not included here, but the API supports them)

The `verify` injection point and the pure `extractBearerToken` make the following table-driven tests trivial to add:

- Missing header, empty header, array-valued header → 401, `auth.jwt.rejected`.
- `bearer`/`BEARER`/`Bearer  ` (extra whitespace) → all accepted as scheme; 401 only on the credential check.
- `none` algorithm token → `JOSEAlgNotAllowed` → 401.
- HS256 token signed with wrong key → `JWSSignatureVerificationFailed` → 401.
- Expired token → `JWTExpired` → 401.
- Token without `sub` → `missing_subject_claim` → 401.
- Valid token → `req.user` populated, `auth.jwt.accepted` logged, `next()` called.

---

## Securability Notes

- **SSEM attributes enforced**: Authenticity (HS256-only allowlist via `jose`, signature + exp/nbf + optional iss/aud verification — V9.1.1, V9.1.2, V9.2.1, V9.2.3); Integrity (Derived Integrity / Request Surface Minimization — only `sub` and `iss` are lifted into `req.user`, never raw claims; `JWT_SECRET` length validated at boot); Accountability (structured `auth.jwt.accepted` / `auth.jwt.rejected` events with reason code, request id, path, method — never the token, never the secret); Resilience (specific `jose` error classes mapped to internal reason codes; generic 401 + `WWW-Authenticate` returned; missing/short secret fails the process at boot, not the request); Modifiability/Testability (policy and verify function injected; pure boundary parser).
- **ASVS references**: V9.1.1, V9.1.2, V9.1.3 (key from trusted pre-configured source), V9.2.1, V9.2.3, V10.3.1, V10.3.3 (subject identity from `sub` + `iss`), V16.5.1 (generic error), V7.2.1 (server-side verification), V6.8.2 (signature integrity).
- **Trust boundaries**: `Authorization` header — canonicalized in `extractBearerToken` (case-insensitive scheme, whitespace trimming, array rejection, single-token enforcement); JWT contents — verified via `jose.jwtVerify` with explicit algorithm allowlist before any claim is read.
- **Dependencies**: `jose@^5` — preferred over `jsonwebtoken` due to a stronger track record on algorithm-confusion safety, mandatory `algorithms` parameter, and active maintenance.
- **Trade-offs**:
  - HS256 was specified ("for now"). Symmetric MAC means every verifier holds the signing key; rotate to RS256/EdDSA before this token leaves a single trust zone. The `algorithms` allowlist is the single line to change.
  - No revocation list / `jti` denylist — required by ASVS V7.4.1 for self-contained tokens. Add a short-TTL cache lookup before `next()` once a revocation store exists.
  - `aud` and `iss` are optional in the loaded policy (env-driven). Set `JWT_AUDIENCE` and `JWT_ISSUER` in production — they materially raise the cost of cross-service token reuse (V9.2.3, V9.2.4).
  - Logger is an injected interface; the example wires `console` for brevity. Production should use a structured logger (e.g., `pino`) and ensure the token string is never passed through.
  - Clock tolerance is 5 seconds — tighten or loosen per deployment.
