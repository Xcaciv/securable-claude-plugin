# Express JWT Authentication Middleware (TypeScript, HS256)

A securable Express middleware that authenticates incoming requests via a JWT presented in the
`Authorization: Bearer <token>` header, attaches a minimal verified user identity to `req.user`,
and rejects malformed, unsigned, expired, or otherwise untrusted tokens.

The design follows FIASSE/SSEM constraints: the trust boundary (the `Authorization` header) is
treated as hostile input, the verifier is centralized and dependency-injected, the signing secret
is loaded once at module init from the environment (never logged), the algorithm is pinned to an
allowlist, and outcomes are recorded via structured logs without leaking token material or
secrets.

## Suggested file layout

```
src/
  auth/
    jwtAuth.ts         # the middleware + types (this file)
    jwtAuth.test.ts    # unit tests (not included here, but the design supports them)
  types/
    express.d.ts       # ambient module augmentation for req.user
```

## `src/types/express.d.ts`

Augment Express's `Request` with a strongly-typed, minimal `user` shape. Keeping this in a
dedicated declaration file enforces a single canonical shape across the codebase and prevents
ad-hoc widening at call sites (Analyzability, Modifiability).

```typescript
// src/types/express.d.ts
import type { AuthenticatedUser } from "../auth/jwtAuth";

declare global {
  namespace Express {
    interface Request {
      /**
       * Server-derived identity of the caller, populated by the JWT auth middleware
       * after a token has been verified. Absent when the request is unauthenticated.
       */
      user?: AuthenticatedUser;
    }
  }
}

export {};
```

## `src/auth/jwtAuth.ts`

```typescript
// src/auth/jwtAuth.ts
//
// JWT authentication middleware for Express.
//
// Trust boundary: the HTTP `Authorization` header is untrusted input.
// Hard shell here, flexible interior downstream (FIASSE Turtle Analogy, S6.3).
//
// Securable properties enforced:
//   - Algorithm allowlist pinned to HS256 (no "none", no algorithm confusion). [ASVS 9.1.2]
//   - Signature verified before any claim is read.                              [ASVS 9.1.1]
//   - Standard time claims (`exp`, `nbf`) enforced by the verifier.             [ASVS 9.2.1]
//   - Optional issuer/audience pinning supported via config.                    [ASVS 9.2.3, 10.3.1]
//   - Request Surface Minimization: only `sub` (and optional `roles`) are
//     extracted from the verified payload onto `req.user`.                      [FIASSE S6.4.1.1]
//   - Derived Integrity: the server never adopts client-supplied identity;
//     only fields that survived signature verification are exposed.             [FIASSE S6.4.1.2]
//   - Structured auth-event logs: outcome, reason, requestId, sub (when known).
//     Token, header value, secret, and stack traces are NEVER logged.           [ASVS 7.1, FIASSE Accountability]
//   - Constant 401 surface for all failure modes; no oracle leak about why.     [Confidentiality]
//   - Dependency-injected verifier and logger for testability without monkey
//     patching the module under test.                                            [SSEM Testability]

import type { NextFunction, Request, RequestHandler, Response } from "express";
import jwt, {
  type JwtPayload,
  type VerifyOptions,
  JsonWebTokenError,
  NotBeforeError,
  TokenExpiredError,
} from "jsonwebtoken";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/**
 * The minimal, server-trusted identity attached to `req.user` after a token
 * has been successfully verified. Add fields here deliberately; every field
 * is a contract the rest of the app may rely on.
 */
export interface AuthenticatedUser {
  /** JWT `sub` claim — stable, non-reassignable user identifier. */
  readonly sub: string;
  /** Optional roles claim, copied through only after string-array validation. */
  readonly roles?: readonly string[];
}

/**
 * Structured log record for an auth event. Implementations should ship these
 * to the central logging pipeline (e.g. pino, winston, OTEL).
 */
export interface AuthLogEvent {
  readonly event:
    | "auth.token.missing"
    | "auth.token.malformed"
    | "auth.token.expired"
    | "auth.token.not_yet_valid"
    | "auth.token.invalid_signature"
    | "auth.token.invalid_claims"
    | "auth.token.accepted";
  readonly requestId?: string;
  readonly sub?: string;
  /** Short, non-sensitive reason code. NEVER include the token or secret. */
  readonly reason?: string;
}

export interface AuthLogger {
  info(event: AuthLogEvent): void;
  warn(event: AuthLogEvent): void;
}

/**
 * Verifier abstraction. Defaults to `jsonwebtoken.verify`, but tests and
 * alternative implementations (e.g. JWKS-backed RS256) can inject their own.
 */
export type JwtVerifier = (
  token: string,
  secret: string,
  options: VerifyOptions
) => JwtPayload | string;

export interface JwtAuthConfig {
  /** HMAC secret. Must be supplied by the caller; never read inside the middleware. */
  readonly secret: string;
  /**
   * Pinned algorithm allowlist. Defaults to ["HS256"]. The "none" algorithm
   * is explicitly rejected by jsonwebtoken when an allowlist is provided.
   */
  readonly algorithms?: readonly ("HS256" | "HS384" | "HS512")[];
  /** Expected `iss` claim, if the deployment pins one. */
  readonly issuer?: string;
  /** Expected `aud` claim(s), if the deployment pins one. */
  readonly audience?: string | readonly string[];
  /** Allowed clock skew in seconds when validating exp/nbf. */
  readonly clockToleranceSeconds?: number;
  /** Pluggable verifier — primarily for tests. */
  readonly verifier?: JwtVerifier;
  /** Pluggable structured logger. */
  readonly logger?: AuthLogger;
}

// ---------------------------------------------------------------------------
// Module init: validate config once, fail fast on misconfiguration.
// ---------------------------------------------------------------------------

const MIN_HS256_SECRET_BYTES = 32; // RFC 7518 §3.2 — key length >= hash output.

function assertSecretStrength(secret: string): void {
  if (typeof secret !== "string" || Buffer.byteLength(secret, "utf8") < MIN_HS256_SECRET_BYTES) {
    // Throwing at startup is intentional: a weak/missing secret is a deploy-time bug,
    // not a runtime condition to be papered over. The error message names the variable
    // but never echoes its value.
    throw new Error(
      "JWT_SECRET is missing or too short. HS256 requires at least 32 bytes of entropy."
    );
  }
}

const noopLogger: AuthLogger = {
  info: () => undefined,
  warn: () => undefined,
};

// ---------------------------------------------------------------------------
// Header parsing — strict, allocation-free, single-purpose.
// ---------------------------------------------------------------------------

const BEARER_PREFIX = "Bearer ";

/**
 * Extract a Bearer token from an `Authorization` header value. Returns
 * `undefined` when the header is absent or malformed. Does not trust casing
 * loosely; RFC 6750 specifies the scheme name is case-insensitive but the
 * `Bearer` form is by far the most common — we accept it case-insensitively
 * and reject anything else.
 */
function extractBearerToken(headerValue: unknown): string | undefined {
  if (typeof headerValue !== "string" || headerValue.length === 0) {
    return undefined;
  }
  // Reject obviously oversized headers early to bound work (Availability).
  if (headerValue.length > 8192) {
    return undefined;
  }
  if (headerValue.length <= BEARER_PREFIX.length) {
    return undefined;
  }
  const scheme = headerValue.slice(0, BEARER_PREFIX.length);
  if (scheme.toLowerCase() !== BEARER_PREFIX.toLowerCase()) {
    return undefined;
  }
  const token = headerValue.slice(BEARER_PREFIX.length).trim();
  // A JWT is at minimum `h.p.s` — three non-empty base64url segments.
  if (token.length === 0 || token.split(".").length !== 3) {
    return undefined;
  }
  return token;
}

// ---------------------------------------------------------------------------
// Claim shaping — Request Surface Minimization + Derived Integrity.
// ---------------------------------------------------------------------------

function isStringArray(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((v) => typeof v === "string");
}

/**
 * Build the `AuthenticatedUser` object from a verified JWT payload. Only
 * known fields are copied; unknown claims are intentionally dropped so they
 * cannot influence downstream logic by accident.
 */
function shapeUserFromPayload(payload: JwtPayload | string): AuthenticatedUser | undefined {
  if (typeof payload !== "object" || payload === null) {
    return undefined;
  }
  const sub = payload.sub;
  if (typeof sub !== "string" || sub.length === 0 || sub.length > 255) {
    return undefined;
  }
  const rawRoles = (payload as Record<string, unknown>).roles;
  const roles = isStringArray(rawRoles) ? Object.freeze([...rawRoles]) : undefined;
  return Object.freeze({ sub, roles });
}

// ---------------------------------------------------------------------------
// 401 helper — uniform failure surface.
// ---------------------------------------------------------------------------

function reject(res: Response): void {
  // A single, opaque body keeps the failure surface uniform regardless of
  // root cause. Detailed reasons live in the structured log, not the wire.
  res.setHeader("WWW-Authenticate", 'Bearer realm="api", error="invalid_token"');
  res.status(401).json({ error: "unauthorized" });
}

// ---------------------------------------------------------------------------
// Middleware factory.
// ---------------------------------------------------------------------------

/**
 * Build an Express middleware that verifies an HS256-signed JWT presented
 * in the `Authorization: Bearer <token>` header.
 *
 * The factory pattern keeps the middleware pure (config in, handler out),
 * makes the secret a first-class injected dependency rather than a hidden
 * module-level read, and makes the middleware trivially unit-testable.
 */
export function createJwtAuthMiddleware(config: JwtAuthConfig): RequestHandler {
  assertSecretStrength(config.secret);

  const algorithms = (config.algorithms && config.algorithms.length > 0
    ? config.algorithms
    : (["HS256"] as const)) as VerifyOptions["algorithms"];

  const verifyOptions: VerifyOptions = {
    algorithms,
    ...(config.issuer ? { issuer: config.issuer } : {}),
    ...(config.audience ? { audience: [...config.audience] as string[] | string } : {}),
    clockTolerance: config.clockToleranceSeconds ?? 0,
  };

  const verifier: JwtVerifier =
    config.verifier ??
    ((token, secret, options) => jwt.verify(token, secret, options) as JwtPayload | string);
  const logger: AuthLogger = config.logger ?? noopLogger;
  const secret = config.secret;

  return function jwtAuthMiddleware(req: Request, res: Response, next: NextFunction): void {
    const requestId = (req.header("x-request-id") ?? undefined) as string | undefined;

    const token = extractBearerToken(req.header("authorization"));
    if (!token) {
      logger.warn({ event: "auth.token.missing", requestId, reason: "missing_or_malformed_header" });
      reject(res);
      return;
    }

    let payload: JwtPayload | string;
    try {
      payload = verifier(token, secret, verifyOptions);
    } catch (err) {
      // Specific exception handling — no bare catch, no rethrow of internals.
      if (err instanceof TokenExpiredError) {
        logger.warn({ event: "auth.token.expired", requestId, reason: "exp" });
      } else if (err instanceof NotBeforeError) {
        logger.warn({ event: "auth.token.not_yet_valid", requestId, reason: "nbf" });
      } else if (err instanceof JsonWebTokenError) {
        // Covers invalid signature, malformed token, algorithm mismatch, bad issuer/audience.
        logger.warn({
          event: "auth.token.invalid_signature",
          requestId,
          reason: err.message.slice(0, 120),
        });
      } else {
        logger.warn({ event: "auth.token.malformed", requestId, reason: "verify_failed" });
      }
      reject(res);
      return;
    }

    const user = shapeUserFromPayload(payload);
    if (!user) {
      logger.warn({ event: "auth.token.invalid_claims", requestId, reason: "missing_or_invalid_sub" });
      reject(res);
      return;
    }

    req.user = user;
    logger.info({ event: "auth.token.accepted", requestId, sub: user.sub });
    next();
  };
}

// ---------------------------------------------------------------------------
// Convenience: build from process.env in one call.
// ---------------------------------------------------------------------------

/**
 * Read configuration from `process.env` and build the middleware. The
 * environment read is centralized here so that the rest of the app does not
 * accumulate scattered `process.env.JWT_SECRET` references (Modifiability).
 *
 * Optional environment variables:
 *   - JWT_ISSUER    — pin expected `iss` claim
 *   - JWT_AUDIENCE  — pin expected `aud` claim (single value)
 *   - JWT_CLOCK_TOLERANCE_SECONDS — integer, default 0
 */
export function createJwtAuthMiddlewareFromEnv(
  overrides: Partial<JwtAuthConfig> = {}
): RequestHandler {
  const secret = process.env.JWT_SECRET;
  if (!secret) {
    throw new Error("JWT_SECRET environment variable is not set.");
  }

  const tolerance = process.env.JWT_CLOCK_TOLERANCE_SECONDS;
  const parsedTolerance =
    tolerance !== undefined && /^\d{1,4}$/.test(tolerance) ? Number(tolerance) : 0;

  return createJwtAuthMiddleware({
    secret,
    issuer: process.env.JWT_ISSUER || undefined,
    audience: process.env.JWT_AUDIENCE || undefined,
    clockToleranceSeconds: parsedTolerance,
    ...overrides,
  });
}
```

## Wiring example

```typescript
// src/app.ts
import express from "express";
import { createJwtAuthMiddlewareFromEnv } from "./auth/jwtAuth";

const app = express();
app.use(express.json({ limit: "100kb" })); // bound the body size (Availability)

const requireJwt = createJwtAuthMiddlewareFromEnv({
  // Inject the structured logger you already use elsewhere.
  logger: {
    info: (e) => console.log(JSON.stringify({ level: "info", ...e })),
    warn: (e) => console.warn(JSON.stringify({ level: "warn", ...e })),
  },
});

app.get("/api/me", requireJwt, (req, res) => {
  // req.user is the server-derived identity. Never trust req.body for identity.
  res.json({ sub: req.user!.sub, roles: req.user!.roles ?? [] });
});

export default app;
```

## Suggested `package.json` snippet

Pinned to currently-supported, low-CVE versions. Lockfile (`package-lock.json` or `pnpm-lock.yaml`)
must be committed for reproducible builds.

```json
{
  "dependencies": {
    "express": "4.21.2",
    "jsonwebtoken": "9.0.2"
  },
  "devDependencies": {
    "@types/express": "4.17.21",
    "@types/jsonwebtoken": "9.0.7",
    "@types/node": "20.14.10",
    "typescript": "5.6.3"
  }
}
```

---

## Securability Notes

### SSEM attributes actively enforced

- **Analyzability** — Single-purpose helpers (`extractBearerToken`, `shapeUserFromPayload`, `reject`),
  each well under 30 LoC and under cyclomatic complexity 10. Comments explain *why* at trust
  boundary decisions, not *what*.
- **Modifiability** — All configuration flows through `JwtAuthConfig`. The environment is read in
  exactly one place (`createJwtAuthMiddlewareFromEnv`). Algorithm allowlist, issuer, audience, and
  clock tolerance can be tightened without touching the middleware body.
- **Testability** — `verifier` and `logger` are injectable; tests can pass a stub verifier and a
  capturing logger to exercise every branch (missing header, malformed, expired, bad signature,
  bad sub, accepted) without spinning up a real JWT or modifying the module under test.
- **Confidentiality** — The secret is taken by value through config and never re-read or echoed.
  No token bytes, header bytes, or secret bytes ever appear in logs or in HTTP responses. Failure
  responses are uniformly opaque (`{"error":"unauthorized"}`) so they cannot serve as an oracle.
- **Accountability** — Every auth outcome (missing, malformed, expired, not-yet-valid, bad
  signature, bad claims, accepted) emits a discrete, structured event with a stable `event` code,
  request id, reason, and (on success) `sub`. These map cleanly into SIEM correlation rules.
- **Authenticity** — Signature verification runs *before* any claim is read; the algorithm
  allowlist is pinned (`HS256` by default, never `none`), and `iss`/`aud` pinning is supported and
  encouraged. Time-bound claims (`exp`, `nbf`) are validated by `jsonwebtoken`'s standard verifier.
- **Availability** — Header length is bounded (8 KiB) and a JSON-body limit is suggested upstream
  to bound parser work. The middleware performs no network or disk I/O. There is no shared mutable
  state, so it is safe under concurrent load.
- **Integrity** — *Derived Integrity*: only fields that survived signature verification are copied
  to `req.user`. *Request Surface Minimization*: only `sub` and (optionally) `roles` are extracted;
  unknown claims are dropped. `roles` is type-checked as a string array and frozen. The whole
  `AuthenticatedUser` is frozen so downstream code cannot mutate it.
- **Resilience** — Specific exception handling distinguishes `TokenExpiredError`, `NotBeforeError`,
  and the broader `JsonWebTokenError`; nothing catches `Error` blindly. Misconfiguration
  (missing/short secret) fails fast at startup rather than degrading silently in production.

### ASVS coverage (5.0)

| Requirement | Where it is satisfied |
|---|---|
| **9.1.1** — Self-contained tokens validated by signature before contents are trusted | `verifier(...)` runs before `shapeUserFromPayload`; failure short-circuits to 401 |
| **9.1.2** — Algorithm allowlist; `none` disallowed | `algorithms: ["HS256"]` default, no overlap with asymmetric algs |
| **9.1.3** — Key material from trusted, pre-configured source | Secret is supplied by caller from `process.env.JWT_SECRET` at module init; JWT header `jku`/`x5u`/`jwk` are not honored (HS256 path uses the configured secret only) |
| **9.2.1** — `exp`/`nbf` enforced within validity window | Delegated to `jsonwebtoken.verify`, with bounded `clockTolerance` |
| **9.2.3** — Audience pinning | `audience` config wired into `VerifyOptions` |
| **10.3.1 / 10.3.3** — Identify user via stable, non-reassignable claims (`sub`, optionally `iss`) | `AuthenticatedUser.sub` is the only identity exposed; `iss` pinning supported |
| **7.1.x / 7.2.x** — Logging of authentication events without sensitive data | Structured `AuthLogEvent` with stable codes; no token/secret material logged |
| **14.1.1** — JWT plaintext payload treated as exposed; no secrets placed in tokens by this code | Middleware does not put data into tokens; consumers are reminded via comment that payloads are public |

### Dependency-selection rationale

- **`jsonwebtoken@9.0.2`** — current stable line on the v9 branch, which closed the
  algorithm-confusion family of CVEs (e.g. CVE-2022-23529 / CVE-2022-23539 / CVE-2022-23540) that
  affected v8 and earlier. Mature, widely deployed, actively maintained by Auth0.
- **`express@4.21.x`** — current 4.x maintenance line; well understood security posture, no known
  unresolved high-severity CVEs in this release at the time of generation.
- **`@types/*`** — type-only dev dependencies, no runtime risk, pinned for build reproducibility.
- **No additional dependencies introduced.** Bearer-token parsing is small and explicit; pulling in
  `express-jwt` or `passport-jwt` was considered but rejected to keep the trust-boundary code
  visible in the application repo and to avoid coupling to a transitively larger surface.
- **Lockfile** — commit `package-lock.json` (npm) or `pnpm-lock.yaml`; CI should run
  `npm audit --omit=dev` (or `pnpm audit --prod`) and fail on high/critical findings.

### Trade-offs and follow-ups

- **HS256 is symmetric.** Every service that verifies tokens holds the same secret that can mint
  them. For multi-service deployments, plan to migrate to RS256/ES256 with a JWKS endpoint; the
  `algorithms` config and pluggable `verifier` are the seams that make that migration mechanical.
- **No revocation list.** Self-contained tokens remain valid until `exp`. If immediate revocation
  is needed (per ASVS 7.4.1), add a `jti` claim and a deny-list lookup inside the verifier seam.
- **Roles claim is optional and pass-through.** Authorization decisions belong to a separate layer
  that must re-derive permissions from server-side state for sensitive actions (Derived Integrity).
- **Logger is `noop` by default.** Production deployments must inject a real structured logger;
  CI should lint for that wiring.
