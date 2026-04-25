# PRD: Customer Self-Service Portal — Account Recovery (Securability-Enhanced)

## Context

We're adding self-service account recovery to our customer portal (B2C SaaS, ~250k MAU). The portal already has username/password login and email-based sign-up. This PRD covers the account-recovery workflow: forgot password, account-lockout recovery, and recovery-code issuance for users with 2FA enabled.

The portal handles personal data: names, email addresses, billing addresses, order history. No payment instruments are stored in our system (handled by an external PSP). User population is EU + US, so GDPR applies.

---

## ASVS Level Decision

**Chosen Level**: 2

**Rationale**: This is a B2C production system at meaningful scale (~250k MAU) holding authenticated user identities, PII (names, addresses), and order history protected under GDPR. Account recovery is a high-value attack target because compromise of recovery yields full account takeover, which has direct material impact (privacy breach, regulator exposure, support cost). Level 1 is insufficient because it does not require MFA-aware recovery, breached-password screening, structured security event logs, or anti-automation controls — all of which are load-bearing for a recovery workflow. Level 3 is not justified: there are no payment instruments, no health data, and no government-grade identity assurance requirement.

**Feature-Level Escalations**:
- **F-04 (Support-agent recovery)**: Treat as L3-equivalent for identity-proofing and audit. This bypass route is the most attractive social-engineering target in the system, so identity proofing strength and tamper-evident logging must meet ASVS 6.4.4 (proofing equivalent to enrollment) and 16.3.2/16.4.2 (full audit, log integrity).

---

## Feature ↔ ASVS Coverage Matrix

| Feature | ASVS Section | Requirement ID | Level | Coverage | PRD Change Needed |
|---------|--------------|----------------|-------|----------|-------------------|
| F-01 | V2.2 (Input Validation) | 2.2.1, 2.2.2 | 2 | Partial | Specify server-side validation/canonicalization of email input |
| F-01 | V6.2 (Password Security) | 6.2.1, 6.2.2, 6.2.3, 6.2.5, 6.2.7, 6.2.12 | 2 | Missing | Define password policy on reset, including breach-list screening |
| F-01 | V6.3 (General Auth) | 6.3.1, 6.3.7, 6.3.8 | 2 | Missing | Add anti-automation, post-reset notification, enumeration resistance |
| F-01 | V6.4 (Recovery Lifecycle) | 6.4.1, 6.4.2, 6.4.3 | 2 | Missing | Add token lifetime, single-use, no security questions, MFA-aware reset |
| F-01 | V7.4 (Session Termination) | 7.4.3 | 2 | Missing | Terminate other sessions on successful password reset |
| F-01 | V11.4 (Hashing) | 11.4.2 | 2 | Missing | Specify approved KDF (Argon2id/bcrypt) for stored passwords |
| F-01 | V12.1 (TLS) | 12.1.1 | 1 | Covered (assumed) | Make TLS 1.2+ requirement explicit |
| F-01 | V16.3 (Security Events) | 16.3.1, 16.3.3 | 2 | Missing | Log all reset-flow events with structured metadata |
| F-01 | V16.5 (Error Handling) | 16.5.1 | 2 | Missing | Generic error responses on reset failures |
| F-02 | V6.1 (Auth Documentation) | 6.1.1 | 1 | Partial | Document lockout vs. anti-automation interaction; prevent malicious lockout |
| F-02 | V6.3 (General Auth) | 6.3.1, 6.3.5, 6.3.8 | 2 | Missing | Notify on suspicious lockouts; uniform messaging |
| F-02 | V6.4 (Recovery) | 6.4.1, 6.4.3 | 2 | Missing | Single-use unlock token; MFA must still be enforced after unlock |
| F-02 | V16.3 (Security Events) | 16.3.1, 16.3.3 | 2 | Missing | Log lockout, unlock-request, unlock-redemption events |
| F-03 | V6.5 (MFA) | 6.5.1, 6.5.2, 6.5.3, 6.5.4, 6.5.6 | 2 | Partial | Specify entropy, single-use enforcement, hashed storage, revocation |
| F-03 | V6.4 (Recovery) | 6.4.1 | 2 | Partial | Define expiration / regeneration policy for recovery codes |
| F-03 | V11.4 (Hashing) | 11.4.2 | 2 | Missing | Hash recovery codes with approved KDF |
| F-03 | V14.3 (Client-side Data) | 14.3.3 | 2 | Missing | Forbid persisting recovery codes in browser storage |
| F-03 | V16.3 (Security Events) | 16.3.1, 16.3.3 | 2 | Missing | Log code generation, redemption, regeneration |
| F-04 | V6.4 (Recovery) | 6.4.3, 6.4.4 (treated as 6.4.6 for L3) | 2 → 3 | Missing | Define identity-proofing standard equivalent to enrollment; agent cannot set password |
| F-04 | V6.3 (General Auth) | 6.3.4, 6.3.7 | 2 | Missing | Document this as a distinct auth pathway with consistent strength; notify user |
| F-04 | V8.2/V8.3 (Authorization) | 8.2.1, 8.3.1 | 1 | Missing | Restrict bypass capability to a named role; enforce server-side |
| F-04 | V16.3 (Security Events) | 16.3.1, 16.3.2, 16.3.3 | 2 | Missing | Audit every agent-initiated bypass with agent ID + reason |
| F-04 | V16.4 (Log Protection) | 16.4.1, 16.4.2, 16.4.3 | 2 | Missing | Bypass audit log must be append-only and shipped off-host |
| F-04 | V16.5 (Error Handling) | 16.5.1 | 2 | Missing | Generic user-facing error if proofing fails; full detail only in audit log |

---

## Enhanced Feature Specifications

### Feature F-01: Forgot Password (Self-Service Reset via Email)

**Actor**: Unauthenticated user claiming an account
**Data**: Email address (PII), reset token (server-owned credential), password (credential), user account record
**Trust Boundaries**: browser → public API; API → email provider (SendGrid); API → credential store; API → session store

**ASVS Mapping**: V2.2.1, V2.2.2, V6.2.1, V6.2.2, V6.2.5, V6.2.7, V6.2.12, V6.3.1, V6.3.7, V6.3.8, V6.4.1, V6.4.2, V6.4.3, V7.4.3, V11.4.2, V12.1.1, V16.3.1, V16.3.3, V16.5.1

**Updated Requirements**:
- A user can request a password reset by submitting an email address at `/account/forgot-password`. The submitted email is canonicalized (lowercased, trimmed) and validated against a strict format on the server before any lookup (V2.2.1, V2.2.2).
- The system always returns the same generic success response — same body, same status code, same approximate timing — whether or not the email matches an account, to prevent enumeration (V6.3.8).
- Reset tokens are generated using a CSPRNG with at least 128 bits of entropy, are single-use, and expire 15 minutes after issuance. Tokens are stored only as a salted hash; the raw token never persists server-side after delivery (V6.4.1).
- The reset link is delivered only to the email address on file; no client-supplied "send to" address is honored (Derived Integrity).
- Knowledge-based / "secret question" challenges are not used anywhere in this flow (V6.4.2).
- If the user has MFA enabled, completing a password reset does **not** disable, bypass, or skip MFA. The user must still complete MFA after setting a new password (V6.4.3).
- New passwords are accepted at any composition, must be 8–128 characters (≥15 recommended), and are screened against a known-breached-password list and the documented context-specific word list. The user's current password is not required for reset-flow (the token proves possession of the email) (V6.2.1, V6.2.5, V6.2.7, V6.2.12).
- Stored passwords are hashed using an approved password-hashing KDF (Argon2id preferred, bcrypt acceptable) with parameters tuned to current OWASP guidance (V11.4.2).
- Reset requests are anti-automated: rate-limited per email address, per source IP, and per CAPTCHA-challenged threshold. Limits must not enable malicious lockout of the legitimate account (V6.3.1, V6.1.1).
- All reset-flow events (request, token-issuance, token-redemption-success, token-redemption-failure, password-change) are logged as structured security events including UTC timestamp, account ID (or hashed email if no account exists), source IP, user agent, and outcome (V16.3.1, V16.3.3, V16.2.1).
- On successful password change, the user is notified at the email on file, and all other active sessions for that account are terminated (V6.3.7, V7.4.3).
- Error responses to the user are generic; no stack traces, internal IDs, or token state are returned. Detailed failure cause is logged only (V16.5.1).
- All endpoints in this flow are served over TLS 1.2+ with HTTP→HTTPS redirect and HSTS (V12.1.1).

**Acceptance Criteria**:
- Submitting a reset request for `nobody@example.com` (no account) returns the same response body, HTTP status, and response time (within ±50 ms of the median for valid accounts) as a request for an existing account.
- A reset token presented more than 15 minutes after issuance is rejected with a generic failure response and a `reset.token.expired` security log entry.
- A reset token redeemed once cannot be redeemed again; a second redemption attempt returns the same generic failure response and logs `reset.token.replay`.
- More than 5 reset requests for the same email in any 10-minute window result in HTTP 429 plus a `reset.ratelimit.email` log entry; the legitimate user can still log in normally during the throttle (no malicious lockout).
- Submitting `password123` (in the breached list) is rejected with a clear policy message; the rejection is logged as `reset.password.policy_failed` without logging the candidate password.
- After a successful reset for an account with TOTP MFA enabled, the next login still requires the TOTP code; this is verified by an automated test.
- After a successful reset, all other active sessions for the user receive a 401 on their next request and are not allowed to refresh.
- A confirmation email is sent to the on-file address within 60 seconds of a successful password change; the email content does not include the new password or token.
- The audit pipeline contains queryable structured events for every step of the flow, keyed by user ID, with UTC timestamps.

**Securability Notes**: This feature crosses an unauthenticated trust boundary, so the load-bearing concerns are input canonicalization, anti-automation, and uniform response shape (FIASSE S6.3 trust boundary, S6.4 derived integrity — never trust a client-supplied "deliver to" address). The reset token is server-owned state; the only client-supplied value that should ever be trusted is the opaque token bytes themselves. Centralize token issuance, hashing, expiry, and redemption in one module so policy (lifetime, entropy, KDF parameters) can evolve without touching call sites (SSEM Modifiability). Every step must be observable in the audit pipeline (SSEM Accountability, FIASSE Transparency) — abuse detection downstream depends on this.

---

### Feature F-02: Account Lockout Recovery

**Actor**: Unauthenticated user whose account has been locked after failed login attempts
**Data**: Email address (PII), unlock token (server-owned credential), account lock state
**Trust Boundaries**: browser → public API; API → email provider; API → credential store

**ASVS Mapping**: V2.2.1, V6.1.1, V6.3.1, V6.3.5, V6.3.7, V6.3.8, V6.4.1, V6.4.3, V16.3.1, V16.3.3, V16.5.1

**Updated Requirements**:
- After 5 failed login attempts within a 10-minute rolling window, the account enters a "soft-locked" state. The lock applies to authentication, not to lookup, so it cannot be used to determine which emails belong to real accounts (V6.3.8).
- A locked-account user is shown the same uniform message as any failed login; a "Request unlock email" affordance is offered only after the user has authenticated successfully far enough to have demonstrated knowledge of the email (or via the same forgot-password entry point). The system response is identical for locked vs. non-locked accounts to prevent enumeration (V6.3.8).
- The unlock email is sent only to the email address on file. It contains a single-use, time-limited unlock token (15-minute lifetime, ≥128 bits of entropy, stored as a salted hash) (V6.4.1).
- Clicking the unlock link clears the lockout counter. It does **not** authenticate the user; the user must still complete the normal login flow, including MFA if enabled (V6.4.3).
- Anti-automation: unlock-email requests are rate-limited per account and per source IP. The rate limit is tuned so that an attacker cannot keep a victim's account perpetually locked (V6.1.1, V6.3.1).
- Repeated lockouts within a short window or lockouts originating from anomalous IPs/devices trigger a notification to the user describing the time, source, and that no action is required if it was them (V6.3.5, V6.3.7).
- All events (failed login, lockout, unlock-request, unlock-redeem-success, unlock-redeem-failure) are emitted as structured security log entries (V16.3.1, V16.3.3).
- Generic error responses are returned for all unlock-flow failures; cause detail is logged only (V16.5.1).

**Acceptance Criteria**:
- After 5 failed logins in 10 minutes for a single account, the 6th login attempt returns the standard "invalid credentials" response (not "account locked"), and the account is flagged locked in storage.
- An attacker submitting unlock requests for `nobody@example.com` and a real account receives identical responses (body, status, timing within ±50 ms).
- An unlock token is rejected after 15 minutes or after first redemption; both rejections log the corresponding event.
- An unlock cannot be used as authentication: redeeming an unlock token leaves the user unauthenticated, and login must follow.
- An account with TOTP MFA enabled still requires TOTP after a successful unlock; verified by automated test.
- More than 5 unlock-email requests for the same account within 10 minutes returns 429; the legitimate user is still able to log in if they remember their password (no DoS by lockout-loop).
- A user receives a notification email when their account is locked and again when it is unlocked.
- Each lockout, unlock-request, and unlock-redemption produces an indexed structured log entry queryable by user ID and by source IP.

**Securability Notes**: The load-bearing failure mode here is *malicious lockout* — attackers using the lockout mechanism as a denial-of-service. Tune rate limits and lockout windows so that an unauthenticated party cannot deny service to a legitimate user (SSEM Availability, Resilience). Treat the unlock token like a recovery token: server-owned state, opaque, single-use (FIASSE S6.4 derived integrity). Unlock must never authenticate — keep the recovery and authentication paths cleanly separated so MFA cannot be skipped (SSEM Authenticity, FIASSE S2 separation of concerns). Lockout, unlock-request, and unlock-redeem events feed abuse detection downstream (SSEM Accountability).

---

### Feature F-03: Recovery Codes for 2FA Users

**Actor**: Authenticated user managing their 2FA settings; later, a user logging in who has lost their TOTP device
**Data**: Recovery code set (10 codes, treated as authentication factors), 2FA settings, account record
**Trust Boundaries**: browser → public API (authenticated session); API → credential store; user-controlled storage of codes (out of system)

**ASVS Mapping**: V6.4.1, V6.4.3, V6.5.1, V6.5.2, V6.5.3, V6.5.4, V6.5.6, V11.4.2, V14.3.3, V16.3.1, V16.3.3

**Updated Requirements**:
- Recovery codes are generated only after the user re-authenticates (re-entering password and a valid TOTP). Generation invalidates any previous unused recovery codes for that account (V6.5.1, V6.5.6).
- Each code is generated using a CSPRNG, has at least 112 bits of entropy (or is hashed with an approved KDF if shorter), and is presented to the user exactly once at the moment of generation. The system never re-displays codes after this point (V6.5.2, V6.5.3, V6.5.4).
- Codes are stored at rest only as outputs of an approved password-hashing KDF (Argon2id preferred, bcrypt acceptable) with a per-code random salt (V6.5.2, V11.4.2).
- A recovery code substitutes for the second factor only — the user must still enter their password before the recovery code is accepted (V6.4.3).
- Each code is single-use; on successful redemption the code is marked consumed and cannot be used again (V6.5.1).
- After successful login via a recovery code, the user is forced into a flow that requires them to enroll a new TOTP factor or generate a new recovery-code set before regaining full access. The remaining unused recovery codes remain valid until the user explicitly regenerates the set (V6.5.6).
- The user can revoke (regenerate) their recovery codes at any time from authenticated account settings; regeneration invalidates the prior set (V6.5.6).
- Recovery codes must not be persisted in browser storage by the application (no `localStorage`, `sessionStorage`, `IndexedDB`, or cookies). The download/print/copy affordance is the user's only persistence mechanism (V14.3.3).
- All recovery-code events (generation, individual redemption, regeneration, exhaustion-warning when ≤2 codes remain) are emitted as structured security log entries; the codes themselves are never logged (V16.3.1, V16.3.3, V16.2.5).
- The user receives an email notification on generation, regeneration, and any successful login via recovery code (V6.3.7).

**Acceptance Criteria**:
- Generating recovery codes from an authenticated session that has not re-authenticated within the last 5 minutes returns 401/403 and is logged.
- A unit/integration test confirms that retrieving a stored recovery code from the database returns a hash, not plaintext, and that two identical-input generations produce different stored values (proving per-code salt).
- Redeeming a recovery code as a sole factor (no password) is rejected with a generic auth failure.
- A recovery code redeemed once is rejected on a second redemption; both successful and failed redemptions are logged.
- Regenerating recovery codes invalidates 100% of the previous set; verified by attempting to redeem each prior code.
- After login via a recovery code, the user is routed to a "re-enroll second factor" page; remaining recovery codes are still usable until they regenerate.
- Browser DevTools inspection confirms the recovery codes are not present in `localStorage`, `sessionStorage`, `IndexedDB`, or cookies after generation.
- The user receives an email within 60 seconds of generation, regeneration, and any successful recovery-code login.
- A `recovery_codes.lowwatermark` event is logged when a redemption leaves ≤2 codes remaining.

**Securability Notes**: Recovery codes are authentication factors, so the SSEM Confidentiality and Integrity properties of the *stored* form dominate the design — store hashed (FIASSE S6.4 server-owned state), never log them, never re-display them (FIASSE S2 transparency must not leak secrets). Treat regeneration as factor-lifecycle: new set always invalidates old (SSEM Modifiability lets us strengthen the policy later — e.g., shorten code lifetime — without changing call sites). The "logged in via recovery code → must re-enroll" loop closes a common gap where a user keeps using codes indefinitely after losing their TOTP, which slowly drains MFA strength to zero (SSEM Resilience).

---

### Feature F-04: Recovery via Support Agent (Identity-Proofed Bypass)

**Actor**: Support agent (privileged internal role) acting on behalf of a customer who has failed all automated recovery
**Data**: Customer account record, on-file PII (used as proofing data), agent identity, audit record
**Trust Boundaries**: support-tool UI → internal admin API; admin API → credential store; admin API → email provider; admin API → audit log pipeline

**ASVS Mapping**: V6.1.3, V6.3.4, V6.3.7, V6.4.3, V6.4.6 (treated as enforced even at L2 here), V8.2.1, V8.2.2, V8.3.1, V11.1.1, V16.3.1, V16.3.2, V16.3.3, V16.4.1, V16.4.2, V16.4.3, V16.5.1

**Updated Requirements**:
- The support-agent recovery pathway is documented as a distinct, named authentication pathway with the same strength as primary authentication: the resulting reset link must still satisfy F-01's MFA-aware reset rules (V6.1.3, V6.3.4).
- The agent's ability to trigger an emergency reset is gated behind a named `account.recovery.bypass` permission. This permission is granted only to a documented support-tier role, enforced server-side, and not granted by default to all support staff (V8.2.1, V8.3.1).
- Identity proofing must be performed at strength equivalent to original enrollment. The verbal challenge alone is insufficient: the agent must collect at least two independent proofing signals from a documented list (e.g., recent order number + billing ZIP + last-4 of an on-file phone number) and record which signals were used. Knowledge-based questions like "favorite pet" are explicitly forbidden (V6.4.4 / treated equivalent to V6.4.6, V6.4.2).
- The agent **cannot set or choose** the user's password. The only action available is "send emergency reset link to the email on file." The link goes to the on-file email address only — never to an agent-supplied address (V6.4.6, FIASSE Derived Integrity).
- The emergency reset link itself is identical in security properties to F-01's reset token (single-use, ≥128-bit entropy, 15-minute lifetime, stored as salted hash, MFA-preserving) (V6.4.1, V6.4.3).
- Every bypass action requires the agent to record a structured reason (free-text + dropdown category) before the link is dispatched. The action is rate-limited per agent and globally; an alert fires on threshold breach (V6.3.1, V16.3.3).
- Each bypass produces an immutable audit record containing: agent ID, agent session ID, target user ID, UTC timestamp, proofing signals attested, reason category, free-text reason, source IP, and outcome. The audit record is shipped to a logically separate, append-only log store (V16.3.1, V16.3.2, V16.3.3, V16.4.1, V16.4.2, V16.4.3).
- The customer is notified at the on-file email (and at any registered secondary contact) every time an agent-initiated bypass is triggered, including the timestamp and a "this wasn't me — contact us" link (V6.3.7).
- If proofing fails, the user-facing message ("we couldn't verify your identity, please try again later") and the agent-facing message reveal nothing about which proofing signals failed; full detail goes only to the audit log (V16.5.1).
- Periodic review: the bypass audit log is sampled and reviewed by a second function (e.g., security or compliance) at a documented cadence to detect agent abuse.

**Acceptance Criteria**:
- An agent without the `account.recovery.bypass` permission attempting the bypass endpoint receives 403 and an entry in the audit log; verified by automated authorization test.
- An agent attempting to send the reset link to an agent-supplied "alternate" email is blocked at the API; the address is server-derived from the user record, not from the request body. Verified by an integration test that injects an `alt_email` field and confirms it is ignored.
- The bypass endpoint rejects requests that do not include at least two proofing-signal attestations from the documented list.
- A successful bypass produces exactly one audit record containing all required fields; verified by an end-to-end test that diffs the audit pipeline against expectations.
- The audit pipeline is append-only: an attempt to modify or delete a bypass record from the application database fails (verified by a destructive-action test against a non-prod copy).
- The customer receives the "support-initiated reset" notification email within 60 seconds of bypass.
- An agent triggering more than the documented per-agent threshold of bypasses in a 24-hour window is rate-limited and an alert is dispatched to the security on-call channel.
- After a bypass, the customer's MFA settings are unchanged; the next login still requires MFA.
- Failed-proofing audit entries contain the failure reason; the user-facing and agent-facing UI strings are identical regardless of which signal failed.

**Securability Notes**: This is the system's most attractive social-engineering surface and warrants L3-grade audit and authorization treatment even though the rest of the product is L2. The two non-negotiables are (a) the agent cannot choose the destination of the reset link or the new password — both are server-owned state per FIASSE S6.4 derived integrity, which removes the "talk the agent into typing my address" attack — and (b) the audit log is tamper-evident and reviewed (SSEM Accountability, Integrity; FIASSE Transparency). Centralize the bypass policy (proofing-signal list, rate limits, allowed reason categories) in configuration rather than code so it can evolve as fraud patterns shift (SSEM Modifiability). Notifying the customer on every bypass turns the user into part of the detection loop (SSEM Accountability + Resilience) — most insider-abuse patterns are caught first by the customer.

---

## Cross-Cutting Securability Requirements

- **TLS everywhere**: All recovery endpoints (public and internal-admin) are served over TLS 1.2+ with HSTS; HTTP→HTTPS redirect is enforced at the edge. (ASVS V12.1.1)
- **Centralized recovery-token module**: Token generation, hashing, expiry, redemption, and invalidation for forgot-password, account-unlock, and emergency-reset tokens are implemented in a single module so policy is changed once and applied consistently. (FIASSE S2 modifiability; ASVS V6.4.1)
- **Centralized password-hashing module**: All password (and recovery-code) hashing goes through one wrapper around the approved KDF (Argon2id preferred, bcrypt fallback) with parameters under configuration. (ASVS V11.4.2)
- **Structured security logging**: All recovery-flow events use a single structured-log format (JSON, UTC, schema-versioned) and are shipped to a logically separate log store with append-only semantics. Sensitive values (raw tokens, candidate passwords, recovery codes) are never logged; emails are logged hashed where the user is unauthenticated. (ASVS V16.2.1–16.2.5, V16.3.1–16.3.4, V16.4.1–16.4.3)
- **Anti-automation baseline**: All recovery endpoints sit behind a shared rate-limiting / CAPTCHA-challenge layer with documented thresholds per email, per IP, per ASN, and globally. Thresholds are tuned so an attacker cannot induce malicious lockout. (ASVS V6.1.1, V6.3.1)
- **Generic error responses**: All recovery endpoints emit one of a fixed set of generic responses to the user; detailed cause is in the audit log only. No stack traces or internal IDs surface in HTTP responses. (ASVS V16.5.1)
- **Email channel via SendGrid**: Outgoing recovery and notification emails use a documented set of templates; the API key is held in the secrets manager, rotated on a documented schedule, and never logged. The "from" address is configured to authenticate (SPF/DKIM/DMARC). (ASVS V13.1.4)
- **Session termination on credential change**: A successful password reset or recovery-code regeneration terminates all other active sessions for the account; the current session may continue. (ASVS V7.4.3)
- **User notification on recovery actions**: Each of password-reset-completed, account-unlocked, recovery-codes-generated, recovery-code-redeemed, and agent-initiated-bypass triggers an email to the on-file address with timestamp, source IP, user agent, and a "this wasn't me" link. (ASVS V6.3.7)
- **No knowledge-based auth**: "Secret questions" / "favorite pet" / KBA challenges are forbidden across every recovery path including support agents. (ASVS V6.4.2)
- **Privacy alignment (GDPR)**: Logged email addresses for unauthenticated recovery attempts are stored hashed; PII is retained only as long as needed for fraud detection; recovery-flow logs are listed in the data inventory. (ASVS V16.2.5; GDPR data-minimization)

---

## Open Gaps and Assumptions

- **Threat model for support-agent abuse not yet documented.** F-04's controls assume insider threat is in scope; confirm with security and produce a written threat model before implementation.
- **MFA enrollment population unknown.** F-01 and F-02 requirements depend on how many users have MFA enabled; if MFA is mandatory the recovery flows can be tightened further (e.g., always require step-up).
- **Lockout window and threshold are inherited from the existing login flow.** Confirm the current 5-attempts-in-10-minutes threshold has been tuned against actual brute-force telemetry and against malicious-lockout DoS.
- **Email is the only delivery channel.** ASVS V6.3.6 (L3) discourages email as an authentication factor. For a future iteration, consider adding an authenticated in-app "recovery initiated" indicator, or an out-of-band push, especially for high-value accounts.
- **Agent identity proofing list not yet defined.** The "two of N proofing signals" list is referenced but the specific signals (and which combinations are acceptable) need to be drafted with support and fraud teams before F-04 ships.
- **Audit log retention period for bypass records not specified.** Default to a documented retention aligned with fraud-investigation needs and GDPR; confirm before launch.
- **Concurrency / race conditions on token redemption not specified.** Implementation must use a database-level uniqueness or atomic-update pattern so a token cannot be redeemed twice in parallel; confirm during design.
- **Latency budget (200 ms login overhead) interacts with breached-password screening.** If the breach check is synchronous and remote, it may exceed the budget; assume a local breached-password store (e.g., bloom filter) and confirm with infra.
- **Localization of notification emails for EU users** (GDPR, language requirements) — confirm template coverage before launch.
