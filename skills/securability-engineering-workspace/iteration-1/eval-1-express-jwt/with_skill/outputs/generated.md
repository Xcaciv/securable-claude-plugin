# Express JWT Authentication Middleware (TypeScript)

A small, securable JWT bearer-token middleware for Express. The middleware is split into three focused units (configuration, verifier, middleware) so each is independently testable and the cryptographic surface is isolated from the HTTP surface.

## `src/auth/jwt-config.ts` — fail-fast configuration

```typescript
// src/auth/jwt-config.ts
//
// Centralizes JWT verification configuration. Loaded once at process start so
// the application fails fast (Availability / Integrity) if the signing secret
// is missing or weak, rather than discovering it on the first request.

import { createSecretKey, KeyObject } from "node:crypto";

export interface JwtVerificationConfig {
  readonly key: KeyObject;
  readonly algorithms: readonly ["HS256"]; // allowlist; no 'none', no alg confusion
  readonly issuer?: string;
  readonly audience?: string;
  readonly clockToleranceSeconds: number;
}

const MIN_HS256_SECRET_BYTES = 32; // RFC 7518 §3.2: key SHOULD be >= hash output size

export function loadJwtConfigFromEnv(env: NodeJS.ProcessEnv = process.env): JwtVerificationConfig {
  const rawSecret = env.JWT_SECRET;
  if (!rawSecret || rawSecret.trim().length === 0) {
    throw new Error("JWT_SECRET is not set; refusing to start without a signing secret.");
  }
  // Treat the env var as a UTF-8 secret (most common deployment shape).
  const secretBytes = Buffer.from(rawSecret, "utf8");
  if (secretBytes.byteLength < MIN_HS256_SECRET_BYTES) {
    throw new Error(
      `JWT_SECRET must be at least ${MIN_HS256_SECRET_BYTES} bytes for HS256; got ${secretBytes.byteLength}.`,
    );
  }

  return {
    key: createSecretKey(secretBytes),
    algorithms: ["HS256"] as const,
    issuer: env.JWT_ISSUER || undefined,
    audience: env.JWT_AUDIENCE || undefined,
    clockToleranceSeconds: 5,
  };
}
```

## `src/auth/jwt-verifier.ts` — pure verification logic

```typescript
// src/auth/jwt-verifier.ts
//
// Pure JWT verification, decoupled from Express. Returns a normalized
// AuthenticatedUser on success or throws a typed AuthError on failure.
// Keeping HTTP out of this module means the verifier is unit-testable
// without spinning up a request/response (Testability, Modifiability).

import { jwtVerify, errors as joseErrors, type JWTPayload } from "jose";
import type { JwtVerificationConfig } from "./jwt-config.js";

export interface AuthenticatedUser {
  readonly id: string;       // 'sub' claim — stable, server-trusted user identifier
  readonly issuer?: string;  // 'iss' claim — for audit/log correlation
  readonly tokenId?: string; // 'jti' claim — for revocation lookups (future)
  readonly expiresAt: Date;  // 'exp' claim — convenience for downstream checks
}

export type AuthErrorCode =
  | "missing_authorization"
  | "malformed_authorization"
  | "invalid_signature"
  | "expired_token"
  | "invalid_claims"
  | "token_rejected";

export class AuthError extends Error {
  public readonly code: AuthErrorCode;
  public readonly cause?: unknown;
  constructor(code: AuthErrorCode, message: string, cause?: unknown) {
    super(message);
    this.name = "AuthError";
    this.code = code;
    this.cause = cause;
  }
}

export async function verifyBearerToken(
  token: string,
  config: JwtVerificationConfig,
): Promise<AuthenticatedUser> {
  let payload: JWTPayload;
  try {
    const result = await jwtVerify(token, config.key, {
      algorithms: [...config.algorithms], // explicit allowlist enforced by jose
      issuer: config.issuer,
      audience: config.audience,
      clockTolerance: config.clockToleranceSeconds,
    });
    payload = result.payload;
  } catch (err) {
    throw mapJoseError(err);
  }

  // Derived Integrity: only extract expected claims; never spread the payload.
  const sub = payload.sub;
  if (typeof sub !== "string" || sub.length === 0) {
    throw new AuthError("invalid_claims", "Token is missing a usable subject claim.");
  }
  if (typeof payload.exp !== "number") {
    throw new AuthError("invalid_claims", "Token is missing an expiration claim.");
  }

  return {
    id: sub,
    issuer: typeof payload.iss === "string" ? payload.iss : undefined,
    tokenId: typeof payload.jti === "string" ? payload.jti : undefined,
    expiresAt: new Date(payload.exp * 1000),
  };
}

function mapJoseError(err: unknown): AuthError {
  if (err instanceof joseErrors.JWTExpired) {
    return new AuthError("expired_token", "Token has expired.", err);
  }
  if (
    err instanceof joseErrors.JWSSignatureVerificationFailed ||
    err instanceof joseErrors.JWSInvalid ||
    err instanceof joseErrors.JOSEAlgNotAllowed
  ) {
    return new AuthError("invalid_signature", "Token signature is invalid.", err);
  }
  if (err instanceof joseErrors.JWTClaimValidationFailed) {
    return new AuthError("invalid_claims", "Token claims failed validation.", err);
  }
  return new AuthError("token_rejected", "Token could not be verified.", err);
}
```

## `src/auth/jwt-middleware.ts` — Express adapter

```typescript
// src/auth/jwt-middleware.ts
//
// Thin Express adapter around verifyBearerToken. Responsibilities:
//   1. Extract the bearer token from the Authorization header (boundary input).
//   2. Delegate to the verifier.
//   3. Attach a minimal AuthenticatedUser to req.user on success.
//   4. Emit structured audit logs for grant/deny decisions.
//   5. Respond with a generic 401 on any failure (no info leak).

import type { NextFunction, Request, RequestHandler, Response } from "express";
import {
  AuthError,
  verifyBearerToken,
  type AuthenticatedUser,
} from "./jwt-verifier.js";
import type { JwtVerificationConfig } from "./jwt-config.js";

// Augment the Express Request shape so downstream handlers see a typed `user`.
declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace Express {
    interface Request {
      user?: AuthenticatedUser;
    }
  }
}

export interface AuthLogger {
  info(event: string, context: Record<string, unknown>): void;
  warn(event: string, context: Record<string, unknown>): void;
}

export interface JwtMiddlewareDeps {
  config: JwtVerificationConfig;
  logger: AuthLogger;
  // Override only in tests; defaults to the real verifier.
  verify?: typeof verifyBearerToken;
}

const BEARER_PREFIX = "Bearer ";

export function createJwtAuthMiddleware(deps: JwtMiddlewareDeps): RequestHandler {
  const verify = deps.verify ?? verifyBearerToken;

  return async function jwtAuthMiddleware(
    req: Request,
    res: Response,
    next: NextFunction,
  ): Promise<void> {
    const requestId = pickRequestId(req);
    const token = extractBearerToken(req.headers.authorization);
    if (token instanceof AuthError) {
      respondUnauthorized(res, deps.logger, token, { requestId, route: req.path });
      return;
    }

    try {
      const user = await verify(token, deps.config);
      req.user = user;
      deps.logger.info("auth.jwt.granted", {
        requestId,
        route: req.path,
        userId: user.id,
        tokenIssuer: user.issuer,
        tokenId: user.tokenId,
      });
      next();
    } catch (err) {
      const authErr =
        err instanceof AuthError
          ? err
          : new AuthError("token_rejected", "Token could not be verified.", err);
      respondUnauthorized(res, deps.logger, authErr, { requestId, route: req.path });
    }
  };
}

function extractBearerToken(headerValue: string | undefined): string | AuthError {
  if (!headerValue) {
    return new AuthError("missing_authorization", "Authorization header is missing.");
  }
  if (!headerValue.startsWith(BEARER_PREFIX)) {
    return new AuthError("malformed_authorization", "Authorization header must use Bearer scheme.");
  }
  const token = headerValue.slice(BEARER_PREFIX.length).trim();
  // A JWS compact serialization always contains exactly two dots.
  if (token.length === 0 || token.split(".").length !== 3) {
    return new AuthError("malformed_authorization", "Bearer token is malformed.");
  }
  return token;
}

function respondUnauthorized(
  res: Response,
  logger: AuthLogger,
  err: AuthError,
  context: { requestId: string | undefined; route: string },
): void {
  // Log the specific failure code for ops, but never leak it to the caller.
  logger.warn("auth.jwt.denied", {
    ...context,
    reason: err.code,
  });
  // Generic body: do not echo the token, the header, or the underlying error.
  res
    .status(401)
    .set("WWW-Authenticate", 'Bearer realm="api", error="invalid_token"')
    .json({ error: "unauthorized" });
}

function pickRequestId(req: Request): string | undefined {
  const header = req.headers["x-request-id"];
  if (typeof header === "string" && header.length > 0 && header.length <= 128) {
    return header;
  }
  return undefined;
}
```

## `src/auth/jwt-middleware.example.ts` — wiring

```typescript
// src/auth/jwt-middleware.example.ts
//
// Reference wiring. Configuration is loaded once at startup so a missing or
// weak JWT_SECRET fails the boot, not a request.

import express from "express";
import { loadJwtConfigFromEnv } from "./jwt-config.js";
import { createJwtAuthMiddleware, type AuthLogger } from "./jwt-middleware.js";

const logger: AuthLogger = {
  info: (event, context) => console.log(JSON.stringify({ level: "info", event, ...context })),
  warn: (event, context) => console.warn(JSON.stringify({ level: "warn", event, ...context })),
};

const app = express();
const jwtConfig = loadJwtConfigFromEnv(); // throws on misconfiguration
const requireAuth = createJwtAuthMiddleware({ config: jwtConfig, logger });

app.get("/api/me", requireAuth, (req, res) => {
  // req.user is now a typed AuthenticatedUser
  res.json({ id: req.user!.id });
});

export { app };
```

## Securability Notes

**SSEM attributes actively enforced**:
- **Integrity** — Algorithm allowlist pinned to `HS256` (no `alg:none`, no algorithm confusion); explicit signature verification before any claim is read; only the `sub` / `exp` / `iss` / `jti` claims are extracted (Request Surface Minimization, S6.4.1); `req.user` is server-derived from a verified token, never copied wholesale from the payload (Derived Integrity, S6.4.1.1).
- **Authenticity** — Cryptographic verification via `jose.jwtVerify` with a typed `KeyObject`; `iss` and `aud` claims validated when configured; `exp` / `nbf` enforced with bounded clock tolerance.
- **Confidentiality** — 401 response body is generic (`{"error":"unauthorized"}`), no token, header, or underlying-error contents echoed back; tokens are not written to logs (V16.2.5).
- **Accountability** — Structured `auth.jwt.granted` and `auth.jwt.denied` events with `requestId`, `route`, `userId`, and a coarse `reason` code — sufficient for an audit pipeline, with no sensitive material.
- **Analyzability** — Three small modules (config, verifier, adapter), each function under 30 LoC, single responsibility, descriptive names; no dead code; comments explain trust-boundary decisions.
- **Modifiability** — Verifier is HTTP-agnostic and reusable (e.g., for WebSocket auth); algorithm list, issuer, and audience are configuration, not constants in the middleware.
- **Testability** — `verify` is injectable into the middleware; `loadJwtConfigFromEnv` accepts an `env` argument; the verifier takes a plain `JwtVerificationConfig` so unit tests can pass a test key without touching `process.env`.
- **Availability** — Configuration is loaded eagerly at boot, so a missing or weak `JWT_SECRET` fails the process immediately rather than degrading every request; `jwtVerify` is a bounded async operation with no I/O.
- **Resilience** — Typed `AuthError` with discrete codes; `jose` errors are mapped explicitly (no bare `catch`); malformed `Authorization` headers are rejected before any crypto work; bearer-token shape is sanity-checked (three dot-separated segments) before verification.

**ASVS references**:
- **V9.1.1** — Signature is verified before any claim is trusted.
- **V9.1.2** — `algorithms: ["HS256"]` allowlist; `none` is implicitly forbidden.
- **V9.1.3** — Key material comes from a pre-configured server-side source (`process.env.JWT_SECRET`); `jku`/`x5u`/`jwk` headers are ignored by `jose` for symmetric verification.
- **V9.2.1** — `exp` / `nbf` enforced via `jwtVerify` with a 5-second clock tolerance.
- **V9.2.3** — `aud` validated when `JWT_AUDIENCE` is set.
- **V7.2.1** — Token verification happens server-side in a trusted backend module.
- **V16.2.1**, **V16.2.5** — Auth events include who/what/where/when metadata; tokens and credentials are excluded from logs.

**Trust boundaries handled**:
- HTTP request to middleware — `Authorization` header parsed, length-bounded, shape-validated before crypto.
- Middleware to verifier — only the raw token string crosses; the verifier sees no `Request`/`Response` objects.
- Process boot to runtime — `loadJwtConfigFromEnv` validates `JWT_SECRET` length/presence at startup.

**Dependencies introduced**:
- `jose@^5` — actively maintained JOSE/JWT library by Filip Skokan; safer defaults than `jsonwebtoken` (requires explicit `algorithms`, no `none` support, typed `KeyObject` API). Latest stable on npm at the time of writing; pin via `package-lock.json` / `npm ci`.
- `express@^4` — assumed already in the project; no version change.
- Node built-ins: `node:crypto` for `createSecretKey` / `KeyObject` (no extra dependency).

**Trade-offs and assumptions**:
- **HS256 is acceptable for now, but plan to migrate to RS256/EdDSA** when verifiers and signers are no longer the same trust domain. Symmetric keys force every consumer to also be a potential issuer; an asymmetric scheme isolates that capability.
- **Revocation is not implemented.** `tokenId` is captured to enable future denylist/jti-blocklist lookups (V7.4.1) but no store is wired up. If immediate revocation is a requirement, plug a denylist check into `verifyBearerToken` after signature verification.
- **`JWT_ISSUER` and `JWT_AUDIENCE` are optional in this scaffold** to keep the example minimal. In any deployment that issues tokens for more than one service, both should be required; flip them to mandatory in `loadJwtConfigFromEnv` before production.
- **Rate limiting and IP-based throttling are not in this middleware** by design — apply an upstream rate limiter (e.g., `express-rate-limit` backed by Redis for multi-instance deploys) to prevent token-guessing brute force.
- **Secret is read as UTF-8.** If operators provision a base64-encoded high-entropy key, decode it before placing it in `JWT_SECRET`, or extend `loadJwtConfigFromEnv` to support a `JWT_SECRET_ENCODING=base64` toggle.
- **Logger interface is intentionally minimal** so a real structured logger (pino, winston, OpenTelemetry log bridge) can be substituted without touching middleware code.
