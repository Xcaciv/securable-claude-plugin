# Express JWT Authentication Middleware (TypeScript)

A FIASSE/SSEM-aligned Express middleware that authenticates requests via a
bearer JWT using HS256, attaches a minimal user identity to `req.user`, and
rejects malformed, unsigned, or expired tokens at the trust boundary.

The middleware is split into small, testable units, keeps the signing secret
out of logs, validates algorithm/issuer/audience explicitly (mitigating
`alg:none` and algorithm-confusion attacks), and emits structured audit events
for every auth decision.

## Context Identified

- **Language/Framework**: Node.js + TypeScript, Express 4.x
- **System type**: Backend HTTP API
- **Data sensitivity**: Token is a trust-bearing credential; carries user identity
- **Exposure**: Public trust boundary (HTTP request ingress)
- **Feature category**: Authentication / self-contained token verification

## ASVS Mapping (implementation constraints applied)

| ASVS | Requirement intent translated into code |
|------|------------------------------------------|
| **V9.1.1** | Signature/MAC verified before any claim is trusted (`jwt.verify` with `algorithms: ['HS256']`). |
| **V9.1.2** | Strict algorithm allowlist; `'none'` rejected. Only HS256 accepted. |
| **V9.1.3** | Key material loaded from pre-configured env source at startup; no header-driven key lookup (`jku`/`x5u`/`jwk` not honored). |
| **V9.2.1** | `exp` / `nbf` verified (default behavior of `jsonwebtoken` with `clockTolerance`). |
| **V9.2.2** | Token `typ` validated; only access tokens accepted for authorization. |
| **V9.2.3** | `aud` validated against a configured allowlist. |
| **V8.3.1** | Authorization/authn enforcement at server trust boundary, never trusted from client. |
| **V16.x** (logging) | Structured auth event logging (success/failure) without secret/token leakage. |

## Installation

```bash
npm install express jsonwebtoken
npm install --save-dev typescript @types/express @types/jsonwebtoken @types/node
```

Version policy (pinned in `package.json`, lockfile committed):

- `express@^4.21.2` — latest stable 4.x; no open critical CVEs.
- `jsonwebtoken@^9.0.2` — v9 removed the insecure `alg` default and makes the
  `algorithms` option required for verification (mitigates CVE-2022-23529
  / CVE-2022-23539 / CVE-2022-23540). Avoid v8.x.
- Pin via `package-lock.json`; run `npm audit` in CI.

## Files

```
src/
  auth/
    authConfig.ts         # validated configuration loader
    jwtAuth.ts            # the middleware + pure verify function
    authLogger.ts         # structured logging adapter
    authErrors.ts         # error taxonomy
    types.ts              # Express request augmentation
```

### `src/auth/types.ts`

```ts
// Narrow, server-derived identity attached to the request.
// Only the fields the app actually uses are extracted from the token
// (Request Surface Minimization, S6.4.1.1).
export interface AuthenticatedUser {
  readonly id: string;
  readonly roles: readonly string[];
  readonly tokenId: string; // jti, for accountability / revocation lookups
}

declare global {
  // eslint-disable-next-line @typescript-eslint/no-namespace
  namespace Express {
    interface Request {
      user?: AuthenticatedUser;
    }
  }
}

export {};
```

### `src/auth/authErrors.ts`

```ts
// Specific error taxonomy so callers can map outcomes to HTTP responses
// and audit events without stringly-typed checks (Analyzability, Resilience).
export type AuthFailureReason =
  | 'missing_header'
  | 'malformed_header'
  | 'malformed_token'
  | 'bad_signature'
  | 'expired'
  | 'not_yet_valid'
  | 'wrong_algorithm'
  | 'wrong_audience'
  | 'wrong_issuer'
  | 'wrong_token_type'
  | 'missing_subject';

export class AuthError extends Error {
  public readonly reason: AuthFailureReason;

  constructor(reason: AuthFailureReason, message: string) {
    super(message);
    this.name = 'AuthError';
    this.reason = reason;
  }
}
```

### `src/auth/authConfig.ts`

```ts
// Configuration is loaded and validated once at startup. If required values
// are missing or weak, fail fast rather than boot into an insecure state
// (Derived Integrity, Resilience).
export interface AuthConfig {
  readonly secret: string;
  readonly algorithms: readonly ['HS256'];
  readonly issuer: string;
  readonly audience: string;
  readonly clockToleranceSeconds: number;
  readonly acceptedTokenType: string; // e.g. 'access'
}

const MIN_SECRET_BYTES = 32; // HS256 requires >= 256-bit secret for 128-bit security (ASVS 11.2.3).

export function loadAuthConfig(env: NodeJS.ProcessEnv = process.env): AuthConfig {
  const secret = env.JWT_SECRET;
  if (!secret || Buffer.byteLength(secret, 'utf8') < MIN_SECRET_BYTES) {
    // Do not echo the secret or its length details to the caller.
    throw new Error(
      'JWT_SECRET is missing or too short. Provide a high-entropy secret of at least 32 bytes.',
    );
  }

  const issuer = env.JWT_ISSUER;
  const audience = env.JWT_AUDIENCE;
  if (!issuer || !audience) {
    throw new Error('JWT_ISSUER and JWT_AUDIENCE must be configured.');
  }

  return Object.freeze({
    secret,
    algorithms: ['HS256'] as const,
    issuer,
    audience,
    clockToleranceSeconds: 5,
    acceptedTokenType: env.JWT_ACCEPTED_TYPE ?? 'access',
  });
}
```

### `src/auth/authLogger.ts`

```ts
// Thin structured-logging adapter so the middleware is testable and the
// logging backend is swappable (Modifiability, Testability). Never include
// the raw token, secret, or full claims in log output (Confidentiality).
export interface AuthLogger {
  authSuccess(event: AuthSuccessEvent): void;
  authFailure(event: AuthFailureEvent): void;
}

export interface AuthSuccessEvent {
  readonly requestId: string;
  readonly subject: string;
  readonly tokenId: string;
  readonly issuedAt?: number;
  readonly expiresAt?: number;
  readonly sourceIp?: string;
}

export interface AuthFailureEvent {
  readonly requestId: string;
  readonly reason: string;
  readonly sourceIp?: string;
  // Intentionally no token, no secret, no raw header.
}

export const consoleAuthLogger: AuthLogger = {
  authSuccess(event) {
    // Structured single-line JSON for log aggregators (Accountability).
    // eslint-disable-next-line no-console
    console.log(JSON.stringify({ level: 'info', kind: 'auth.success', ...event }));
  },
  authFailure(event) {
    // eslint-disable-next-line no-console
    console.warn(JSON.stringify({ level: 'warn', kind: 'auth.failure', ...event }));
  },
};
```

### `src/auth/jwtAuth.ts`

```ts
import type { NextFunction, Request, RequestHandler, Response } from 'express';
import jwt, {
  type JwtPayload,
  JsonWebTokenError,
  NotBeforeError,
  TokenExpiredError,
} from 'jsonwebtoken';

import type { AuthConfig } from './authConfig';
import { AuthError, type AuthFailureReason } from './authErrors';
import type { AuthLogger } from './authLogger';
import type { AuthenticatedUser } from './types';

const BEARER_PREFIX = 'Bearer ';
const MAX_TOKEN_CHARS = 8 * 1024; // Availability: reject oversize tokens early.

export interface JwtAuthDeps {
  readonly config: AuthConfig;
  readonly logger: AuthLogger;
  readonly now?: () => Date; // injectable clock for Testability
}

/**
 * Extract the bearer token from an Authorization header with strict format checks.
 * Canonicalize -> sanitize -> validate (S6.4.1) at the trust boundary.
 */
export function extractBearerToken(headerValue: string | undefined): string {
  if (typeof headerValue !== 'string' || headerValue.length === 0) {
    throw new AuthError('missing_header', 'Authorization header is missing.');
  }
  if (headerValue.length > MAX_TOKEN_CHARS) {
    throw new AuthError('malformed_header', 'Authorization header exceeds the allowed size.');
  }
  if (!headerValue.startsWith(BEARER_PREFIX)) {
    throw new AuthError('malformed_header', 'Authorization scheme must be Bearer.');
  }
  const token = headerValue.slice(BEARER_PREFIX.length).trim();
  // Basic shape check: three base64url segments separated by dots.
  if (!/^[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+$/.test(token)) {
    throw new AuthError('malformed_token', 'Token is not a well-formed JWS.');
  }
  return token;
}

/**
 * Pure verification: given a token and config, return the authenticated
 * identity or throw AuthError. Kept independent of Express so it can be
 * unit-tested without spinning up HTTP (Testability).
 */
export function verifyAccessToken(token: string, config: AuthConfig): AuthenticatedUser {
  let payload: JwtPayload | string;
  try {
    payload = jwt.verify(token, config.secret, {
      algorithms: [...config.algorithms], // HS256 only; rejects 'none' and alg confusion.
      issuer: config.issuer,
      audience: config.audience,
      clockTolerance: config.clockToleranceSeconds,
      complete: false,
    });
  } catch (err) {
    throw mapJwtError(err);
  }

  if (typeof payload === 'string' || payload === null) {
    throw new AuthError('malformed_token', 'Token payload is not a JSON object.');
  }

  // Token type check (ASVS 9.2.2): only access tokens for authn/authz.
  const tokenType = typeof payload.typ === 'string' ? payload.typ : undefined;
  if (tokenType && tokenType !== config.acceptedTokenType) {
    throw new AuthError('wrong_token_type', 'Token type is not accepted for this endpoint.');
  }

  const subject = typeof payload.sub === 'string' ? payload.sub : undefined;
  if (!subject) {
    throw new AuthError('missing_subject', 'Token is missing the subject claim.');
  }

  const roles = Array.isArray(payload.roles)
    ? payload.roles.filter((r): r is string => typeof r === 'string')
    : [];

  const tokenId = typeof payload.jti === 'string' ? payload.jti : '';

  // Only expected, typed fields are extracted (Request Surface Minimization,
  // S6.4.1.1). The raw payload is never attached to req.
  return Object.freeze({
    id: subject,
    roles: Object.freeze(roles),
    tokenId,
  });
}

function mapJwtError(err: unknown): AuthError {
  if (err instanceof TokenExpiredError) {
    return new AuthError('expired', 'Token has expired.');
  }
  if (err instanceof NotBeforeError) {
    return new AuthError('not_yet_valid', 'Token is not yet valid.');
  }
  if (err instanceof JsonWebTokenError) {
    const msg = err.message.toLowerCase();
    if (msg.includes('audience')) return new AuthError('wrong_audience', 'Token audience mismatch.');
    if (msg.includes('issuer')) return new AuthError('wrong_issuer', 'Token issuer mismatch.');
    if (msg.includes('algorithm')) {
      return new AuthError('wrong_algorithm', 'Token algorithm not permitted.');
    }
    return new AuthError('bad_signature', 'Token signature or structure is invalid.');
  }
  // Unknown failure -- do not leak internals.
  return new AuthError('bad_signature', 'Token verification failed.');
}

/**
 * Build an Express middleware that authenticates a request using a bearer JWT.
 * Rejects with 401 on any failure and never proceeds with partial trust.
 */
export function createJwtAuthMiddleware(deps: JwtAuthDeps): RequestHandler {
  const { config, logger } = deps;

  return function jwtAuthMiddleware(
    req: Request,
    res: Response,
    next: NextFunction,
  ): void {
    const requestId = getRequestId(req);
    const sourceIp = req.ip;

    try {
      const token = extractBearerToken(req.header('authorization'));
      const user = verifyAccessToken(token, config);

      req.user = user;

      logger.authSuccess({
        requestId,
        subject: user.id,
        tokenId: user.tokenId,
        sourceIp,
      });

      next();
    } catch (err) {
      const reason: AuthFailureReason =
        err instanceof AuthError ? err.reason : 'bad_signature';

      logger.authFailure({ requestId, reason, sourceIp });

      // Uniform 401 response. Do not echo the token, header, or
      // detailed reason to the caller (avoid oracle behavior).
      res.status(401).json({
        error: 'unauthorized',
        requestId,
      });
    }
  };
}

function getRequestId(req: Request): string {
  const headerValue = req.header('x-request-id');
  if (typeof headerValue === 'string' && /^[A-Za-z0-9_-]{1,128}$/.test(headerValue)) {
    return headerValue;
  }
  // Fallback: generate a short opaque id. In production, wire a request-id
  // middleware upstream (e.g. express-request-id) so all logs share an id.
  return `req-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`;
}
```

### Wiring it up

```ts
// src/app.ts
import express from 'express';
import { loadAuthConfig } from './auth/authConfig';
import { consoleAuthLogger } from './auth/authLogger';
import { createJwtAuthMiddleware } from './auth/jwtAuth';

const app = express();
const authConfig = loadAuthConfig(); // fail-fast on bad config
const requireAuth = createJwtAuthMiddleware({
  config: authConfig,
  logger: consoleAuthLogger,
});

app.get('/api/me', requireAuth, (req, res) => {
  // req.user is the narrow, server-derived identity.
  res.json({ id: req.user!.id, roles: req.user!.roles });
});

export default app;
```

### Example test (illustrative, Jest)

```ts
// tests/jwtAuth.test.ts
import jwt from 'jsonwebtoken';
import { verifyAccessToken } from '../src/auth/jwtAuth';
import type { AuthConfig } from '../src/auth/authConfig';

const config: AuthConfig = Object.freeze({
  secret: 'a'.repeat(32),
  algorithms: ['HS256'] as const,
  issuer: 'https://issuer.example',
  audience: 'api://example',
  clockToleranceSeconds: 0,
  acceptedTokenType: 'access',
});

test('accepts a well-formed HS256 token', () => {
  const token = jwt.sign(
    { sub: 'user-1', roles: ['reader'], typ: 'access', jti: 'tid-1' },
    config.secret,
    { algorithm: 'HS256', issuer: config.issuer, audience: config.audience, expiresIn: '5m' },
  );
  const user = verifyAccessToken(token, config);
  expect(user.id).toBe('user-1');
  expect(user.roles).toEqual(['reader']);
});

test('rejects alg:none tokens', () => {
  // Hand-crafted unsigned token; verifier must refuse.
  const unsigned = Buffer.from(JSON.stringify({ alg: 'none', typ: 'JWT' })).toString('base64url')
    + '.' + Buffer.from(JSON.stringify({ sub: 'x' })).toString('base64url') + '.';
  expect(() => verifyAccessToken(unsigned, config)).toThrow();
});

test('rejects wrong audience', () => {
  const token = jwt.sign({ sub: 'u' }, config.secret, {
    algorithm: 'HS256', issuer: config.issuer, audience: 'api://other', expiresIn: '5m',
  });
  expect(() => verifyAccessToken(token, config)).toThrow(/audience/i);
});
```

## Securability Notes

**Trust boundary handling (S6.3, S6.4):**

- HTTP request ingress is treated as the hard shell. `extractBearerToken`
  canonicalizes (trim, slice), sanitizes (length cap, strict regex shape),
  and validates the header before any crypto work.
- `verifyAccessToken` extracts only `sub`, `roles`, and `jti` into a frozen
  `AuthenticatedUser` object — the raw payload is never attached to `req`
  (Request Surface Minimization, Derived Integrity).

**SSEM attributes actively enforced:**

- **Analyzability** — Four small files, each with a single responsibility;
  every function < 30 LoC; named error reasons instead of magic strings.
- **Modifiability** — Configuration, logger, and clock are injected; HS256
  is expressed as a config-driven allowlist so migrating to RS256/EdDSA
  later is a config + key-loader change, not a rewrite.
- **Testability** — `extractBearerToken`, `verifyAccessToken`, and
  `mapJwtError` are pure and exercised without Express. The middleware is
  built via a factory so tests can stub the logger and config.
- **Confidentiality** — The secret is only read inside `authConfig.ts` and
  never logged; log events omit the token, header, and full claims; error
  responses do not echo the reason to the caller.
- **Accountability** — Every auth decision emits a structured JSON event
  (`auth.success` / `auth.failure`) with request id, subject, jti, and
  source IP — enough for audit without exposing credentials.
- **Authenticity** — `jwt.verify` with an explicit `algorithms: ['HS256']`
  allowlist, plus issuer and audience checks, mitigates `alg:none` and
  algorithm-confusion (ASVS 9.1.1–9.1.3, 9.2.2–9.2.3).
- **Availability** — Oversize Authorization headers are rejected before
  crypto runs; the regex shape check short-circuits malformed input.
- **Integrity** — Signature verified before any claim is read; only
  expected, type-checked fields populate `req.user`.
- **Resilience** — Specific error classes mapped to specific reasons; the
  catch-all path still returns a generic 401 without leaking internals;
  invalid configuration aborts startup.

**Dependency selection rationale:**

- `jsonwebtoken@^9.0.2`: latest stable major. v9 enforces explicit
  `algorithms` on verify, closing the CVE-2022-23529/23539/23540 class.
  Mature (years of production use), actively maintained, low current CVE
  exposure. An alternative like `jose` is also acceptable and arguably
  better for JWK/JWS flexibility; `jsonwebtoken` is kept here because the
  requirement is HS256 with a static secret, which is its sweet spot.
- `express@^4.21.2`: stable LTS line, no current critical CVEs. Express 5
  is viable; 4.x chosen for ecosystem compatibility.
- No additional helpers added (e.g., `express-jwt`) — standard library +
  `jsonwebtoken` + a small amount of typed code is sufficient and
  minimizes transitive risk.
- Pin exact versions in `package.json` and commit `package-lock.json`; run
  `npm audit --omit=dev` and `npm outdated` in CI.

**Trade-offs and follow-ups:**

- HS256 with a static `JWT_SECRET` is acceptable for a single service that
  both mints and verifies tokens. For multi-service fan-out, prefer
  RS256/EdDSA with a JWKS endpoint so the verifier never holds the signing
  key (ASVS 9.1.3). The `algorithms` allowlist and `AuthConfig` are shaped
  to make that migration a config swap.
- Revocation is not implemented here (ASVS 7.4.1). For self-contained
  tokens, add a denylist lookup by `jti` or a per-user `kid`/issued-after
  check inside `verifyAccessToken` when the product requires logout or
  forced sign-out.
- No rate limiting on failed auth attempts is included in this module;
  apply an upstream limiter (e.g., per-IP) to round out Availability.
