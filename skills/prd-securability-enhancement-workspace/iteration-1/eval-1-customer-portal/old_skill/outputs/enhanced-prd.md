# Enhanced PRD: Customer Self-Service Portal — Account Recovery (Securability Augmented)

> Source PRD: `customer-portal-prd.md`. This document preserves the original feature scope and adds explicit, testable security requirements aligned to OWASP ASVS 5.0 and engineered using FIASSE/SSEM principles.

## Context (unchanged)

Self-service account recovery for a B2C SaaS customer portal (~250k MAU). Existing: username/password login, email-based sign-up. This PRD covers forgot-password, account-lockout recovery, recovery codes for 2FA users, and support-agent-mediated recovery. The portal stores PII (names, emails, billing addresses, order history). No payment instruments are stored locally (handled by external PSP).

---

## 1. ASVS Level Decision

**Selected baseline: ASVS Level 2.**

Rationale:

- The portal is a customer-facing production B2C system processing authenticated user sessions and PII for ~250k MAU — exactly the profile ASVS calls out for L2.
- ASVS L1 is insufficient: L1 is appropriate for low-risk or prototype systems. Account recovery is the most attacked surface of any auth system; L1 controls do not require MFA, breached-password checks, lifetime-limited recovery tokens, or structured security event logging — all of which are needed here.
- ASVS L3 is not required: no high-impact financial transactions are performed in-system (payments are at the PSP), no regulated health/classified data, and the user base is general consumer.
- **Targeted L3 escalations** for two specific controls because account recovery is the canonical takeover vector:
  - **V6.3.7 (L3) — notify user on credential resets / email changes**: applied to F-01, F-04 (cheap, high signal).
  - **V6.3.8 (L3) — no user enumeration on recovery flows**: applied to F-01 and F-02 (already a community baseline expectation).
- GDPR applies to EU users; relevant controls are folded into V14 (data classification) and V16 (logging hygiene), not into a separate level escalation.

---

## 2. Feature-ASVS Coverage Matrix

Coverage status: **C**=Covered, **P**=Partial, **M**=Missing, **N/A**=Not Applicable.

| Feature | ASVS § | Req ID  | Lvl | Coverage | PRD Change Needed                                                                  |
| :------ | :----- | :------ | :-: | :------: | :--------------------------------------------------------------------------------- |
| F-01    | V6.4   | 6.4.1   |  1  |    M     | Reset tokens must be CSPRNG, single-use, short-lived                                |
| F-01    | V6.4   | 6.4.2   |  1  |    M     | No knowledge-based "secret questions" on the reset path                             |
| F-01    | V6.4   | 6.4.3   |  2  |    M     | Reset must not bypass MFA when MFA is enabled                                       |
| F-01    | V6.5   | 6.5.5   |  2  |    M     | Reset link lifetime ≤10 minutes                                                     |
| F-01    | V6.6   | 6.6.2   |  2  |    M     | Reset token bound to the original request (not reusable for another)                |
| F-01    | V6.6   | 6.6.3   |  2  |    M     | Rate-limit reset issuance per email/IP/device                                        |
| F-01    | V6.3   | 6.3.1   |  1  |    M     | Anti-automation on the request endpoint                                              |
| F-01    | V6.3   | 6.3.7   |  3  |    M     | Notify user (email on file) when password is reset                                  |
| F-01    | V6.3   | 6.3.8   |  3  |    M     | Response must not leak whether the email is registered                              |
| F-01    | V6.2   | 6.2.4   |  1  |    M     | New password checked against top-3000 weak list                                      |
| F-01    | V6.2   | 6.2.12  |  2  |    M     | New password checked against breached-password set                                   |
| F-01    | V7.2   | 7.2.4   |  1  |    M     | Issue new session token after reset; invalidate all prior sessions                  |
| F-01    | V14.x  | 14.1.1  |  2  |    M     | Reset-link emails classified; PII handling documented                               |
| F-02    | V6.1   | 6.1.1   |  1  |    P     | "5/10min" lockout exists; document lockout policy and unlock control                |
| F-02    | V6.3   | 6.3.1   |  1  |    P     | Lockout is a brute-force control; specify counter scope and reset behavior          |
| F-02    | V6.3   | 6.3.8   |  3  |    M     | Locked-account message must not enumerate valid accounts                             |
| F-02    | V6.4   | 6.4.1   |  1  |    M     | Unlock token: CSPRNG, short-lived, single-use                                       |
| F-02    | V6.5   | 6.5.5   |  2  |    M     | Unlock link lifetime ≤10 minutes                                                    |
| F-02    | V6.6   | 6.6.3   |  2  |    M     | Rate-limit unlock-email issuance                                                    |
| F-02    | V6.1   | 6.1.1   |  1  |    M     | Documented protection against malicious lockout (DoS via repeated bad attempts)     |
| F-03    | V6.5   | 6.5.1   |  2  |    M     | Recovery codes must be single-use                                                   |
| F-03    | V6.5   | 6.5.2   |  2  |    M     | Stored codes hashed with approved password-hash + 32-bit salt (or ≥112 bits entropy) |
| F-03    | V6.5   | 6.5.3   |  2  |    M     | Codes generated via CSPRNG                                                           |
| F-03    | V6.5   | 6.5.4   |  2  |    M     | Each code ≥20 bits entropy                                                           |
| F-03    | V6.5   | 6.5.6   |  3  |    M     | Codes can be revoked / regenerated (revocation supersedes prior set)                |
| F-03    | V6.6   | 6.6.3   |  2  |    M     | Rate-limit code-redemption attempts                                                  |
| F-03    | V14.x  | 14.1.1  |  2  |    M     | Code material classified as "high sensitivity"                                       |
| F-04    | V6.4   | 6.4.3   |  2  |    M     | Support flow must not silently bypass MFA                                            |
| F-04    | V8.2   | 8.2.1   |  1  |    M     | Only authorized agents can trigger emergency reset; function-level access control   |
| F-04    | V6.3   | 6.3.7   |  3  |    M     | Notify user when an agent triggers an emergency reset                               |
| F-04    | V16.3  | 16.3.1  |  2  |    P     | Auth events must be logged; specify agent identity + ticket ID in log               |
| F-04    | V16.3  | 16.3.2  |  2  |    M     | Log every agent-initiated recovery action (auditable)                                |
| F-04    | V2.3   | 2.3.5   |  3  |   N/A    | Multi-user approval not required at L2 baseline; flagged in open gaps               |
| All     | V6.3   | 6.3.1   |  1  |    M     | Cross-flow rate limiting / anti-automation                                          |
| All     | V6.3   | 6.3.4   |  2  |    M     | Recovery is an alternate auth pathway — must be documented and consistent           |
| All     | V14.1  | 14.1.1/2|  2  |    M     | Data classification of recovery artifacts (links, codes, ticket data)               |
| All     | V14.x  | 14.x.x  |  2  |    M     | TLS in transit; HSTS                                                                 |
| All     | V16.1  | 16.1.1  |  2  |    M     | Security log inventory entry for the recovery surface                                |
| All     | V16.2  | 16.2.1-5|  2  |    M     | Structured logs with who/what/when, no secrets in logs                               |
| All     | V16.3  | 16.3.1-3|  2  |    M     | Log auth attempts, recovery events, anti-automation triggers                         |
| All     | V16.4  | 16.4.1-3|  2  |    M     | Log injection encoded; logs shipped to immutable, isolated store                     |
| All     | V11.1  | 11.1.1-2|  2  |    M     | Document key/secret handling for tokens, code hashes, signing keys                   |

---

## 3. Enhanced Feature Specifications

### Feature F-01: Forgot Password

**User story (unchanged)**: A user who does not remember their password can click "Forgot password?", enter their email, receive a reset link, and set a new password.

**ASVS Mapping**: V6.2.4, V6.2.12, V6.3.1, V6.3.7, V6.3.8, V6.4.1, V6.4.2, V6.4.3, V6.5.5, V6.6.2, V6.6.3, V7.2.4, V14.1.1.

**Updated Requirements**:

1. **Token generation**: The reset token MUST be generated by a CSPRNG and contain ≥128 bits of entropy. Tokens MUST be single-use and bound server-side to a single (user_id, request_id, issued_at) tuple.
2. **Token lifetime**: Reset links MUST expire ≤10 minutes after issuance. Expired tokens MUST be rejected with the same response shape as invalid tokens.
3. **Token storage**: Only a hash of the token (SHA-256 or stronger) is persisted server-side. The plaintext token exists only in the email body and the user's URL.
4. **Uniform response (no enumeration)**: For any submitted email — registered, unregistered, malformed, or locked — the API MUST return HTTP 200 within a bounded time envelope and a generic message ("If that email is registered you will receive a reset link"). Response time variance between "user exists" and "user does not exist" MUST be ≤50 ms (enforced by deferring email send to an async worker after a constant-time response).
5. **Rate limiting**: Issuance is rate-limited at three layers:
   - Per email address: ≤3 reset requests per 15 minutes.
   - Per source IP: ≤10 reset requests per 15 minutes (with allowance for shared NATs documented).
   - Global: circuit-break SendGrid send-rate above documented threshold.
6. **No knowledge-based fallback**: There MUST NOT be any "security question" / "memorable date" challenge anywhere on the reset path.
7. **MFA preservation**: If the user has 2FA enabled, the reset flow MUST require a successful 2FA challenge (TOTP or recovery code) on the new-password page **before** the password change is committed. Resetting the password alone MUST NOT log the user in or remove the 2FA factor.
8. **Password quality at reset**: The new password MUST be:
   - ≥8 characters (15+ recommended in copy);
   - Checked against a top-3000-weak list and a breached-password set (e.g., HIBP k-anonymity API);
   - Accepted as-typed (no truncation, case folding, or composition rules).
9. **Session hygiene**: On successful reset, the system MUST (a) invalidate **all** existing sessions and refresh tokens for the user, and (b) issue a new session token for the current browser only after the user authenticates with the new password (i.e., reset does not auto-login).
10. **User notification**: A notification email ("Your password was reset on {time} from {coarse_location}") MUST be sent to the on-file address on every successful reset, with a link to a self-service "this wasn't me" workflow.
11. **Logging**: Issue, redeem, expire, and reuse-attempt events MUST be logged as structured security events (see cross-cutting V16 requirements).

**Acceptance Criteria (testable)**:

- AC-01.1: A token issued at T expires by T+10min; redemption at T+10min+1s returns the generic invalid-token response.
- AC-01.2: A token, once redeemed, cannot be redeemed again; second redemption returns the generic invalid-token response and emits a `recovery.reset.token_reuse_attempt` log event.
- AC-01.3: For 100 trial submissions split 50/50 between a known email and a known-unregistered email, the 95th-percentile response-time delta is ≤50 ms and the response body is byte-identical.
- AC-01.4: Submitting a 4th reset request for the same email within 15 minutes returns a 429 (or the same generic 200 with no email sent) and emits an anti-automation log event.
- AC-01.5: Attempting to set the new password to "Password1!" (in the top-3000 list) is rejected with a clear message; attempting to set a known-breached password is rejected with a distinct, generic "this password has appeared in a known breach" message.
- AC-01.6: For a user with 2FA enabled, completing the reset link without providing a valid TOTP/recovery code does not change the password and does not log the user in.
- AC-01.7: After a successful reset, all of the user's prior session cookies/refresh tokens fail authorization on the next request (verified across two browsers).
- AC-01.8: On every successful reset, a "your password was reset" email arrives at the on-file address within 60 s.

**Securability Notes**: This is the highest-risk feature in the PRD; account-recovery flows are the dominant takeover vector once login is hardened. The trust boundary is the `/recovery/request` and `/recovery/confirm` endpoints — strict validation lives there, while interior flow is kept simple (single state machine: REQUESTED → REDEEMED | EXPIRED). **Confidentiality** drives token-hash-at-rest, no-enumeration response symmetry, and minimal logging of identifying material (log user_id, never the email body or token). **Accountability** drives structured logging of every state transition, tied to user_id and request_id. **Integrity** drives the explicit MFA-preservation rule — without it, a password reset becomes an MFA bypass. **Resilience** drives async email dispatch (so SendGrid latency cannot widen the timing oracle) and the three-layer rate limit. Avoid hand-rolling token generation or hashing; reuse the platform's auth primitives so the reset path stays modifiable as crypto guidance evolves.

---

### Feature F-02: Account Lockout Recovery

**User story (unchanged)**: After 5 failed login attempts in 10 minutes the account is locked. The user can request an unlock email; clicking the link unlocks the account.

**ASVS Mapping**: V6.1.1, V6.3.1, V6.3.8, V6.4.1, V6.5.5, V6.6.3.

**Updated Requirements**:

1. **Lockout policy (documented)**: The lockout policy is: 5 failed password verifications within a rolling 10-minute window per (user_id) **and** per (source IP × user_id) trigger a soft-lock. Soft-lock duration: 15 minutes auto-expire **or** explicit unlock via email link.
2. **Counter behaviour**: A successful authentication resets the per-(user_id) counter. Failed attempts against unknown usernames are rate-limited per-IP only and MUST NOT enumerate users (response and timing identical to wrong-password-on-known-user).
3. **No-enumeration on locked state**: The login response for a locked account MUST be indistinguishable from a generic "invalid credentials" response. The "your account is locked" UI message is shown **only** after the user clicks "Get unlock email" and successfully redeems the unlock link, OR via in-app notification once they re-authenticate. (Trade-off accepted: slightly lower UX clarity on locked accounts, in exchange for no enumeration.)
4. **Unlock token**: CSPRNG-generated, ≥128 bits entropy, single-use, server-side hash-at-rest, lifetime ≤10 minutes, bound to (user_id, lockout_event_id).
5. **Rate-limited issuance**: Unlock-email issuance follows the same 3-per-15-minutes per-email and 10-per-15-minutes per-IP envelope as F-01.
6. **Malicious-lockout protection**: The system MUST NOT permanently lock an account based on failed attempts alone. Auto-expire after 15 minutes is mandatory. Repeated lockout cycles for the same user (>3 in 24h) MUST raise a `recovery.lockout.suspected_targeted_attack` log event for SOC review and MAY apply a longer cooldown, but MUST NOT deny the legitimate user the unlock-email path.
7. **MFA-aware**: For 2FA users, redeeming the unlock link clears the lockout but does NOT bypass the next 2FA challenge.
8. **Logging**: Lock, unlock-issue, unlock-redeem, auto-expire, and suspected-attack events all emit structured security log entries.

**Acceptance Criteria (testable)**:

- AC-02.1: After 5 failed password attempts in 10 minutes for a known user, the 6th valid login attempt fails with a generic invalid-credentials response (not a lockout-specific message).
- AC-02.2: 5 failed attempts against a non-existent username return responses byte-identical (and within 50 ms p95) to 5 failed attempts against a known user with a wrong password.
- AC-02.3: A lockout auto-expires 15 minutes after the most recent failed attempt, and the user can log in normally without using the unlock link.
- AC-02.4: An unlock token issued at T cannot be redeemed at T+10min+1s.
- AC-02.5: An unlock token cannot be redeemed twice; second redemption emits `recovery.unlock.token_reuse_attempt`.
- AC-02.6: Triggering 4 unlock-email requests for the same email in 15 minutes results in only 3 emails and a logged anti-automation event.
- AC-02.7: For a 2FA-enabled user, redeeming the unlock link does not log them in until they complete a TOTP or recovery-code challenge.

**Securability Notes**: Lockout is itself an attacker primitive (DoS via known emails) — so the design must balance brute-force defense (the original intent) against malicious lockout. **Resilience** therefore drives auto-expire as the primary recovery path; the unlock email is a faster opt-in, not a gate. **Authenticity** is preserved by ensuring unlock does not bypass MFA. **Analyzability** is improved by emitting distinct event types for lockout-issued, unlock-redeemed, and auto-expired so SOC can graph attack patterns. The lockout counter belongs in the same trust-boundary module as the login endpoint — do not let downstream services maintain their own ad-hoc counters.

---

### Feature F-03: Recovery Codes for 2FA Users

**User story (unchanged)**: 2FA users can generate a one-time set of 10 recovery codes from account settings. If the 2FA device is lost, a recovery code can be used in place of TOTP at login. Used codes are invalidated.

**ASVS Mapping**: V6.5.1, V6.5.2, V6.5.3, V6.5.4, V6.5.6, V6.6.3, V14.1.1.

**Updated Requirements**:

1. **Generation**: Codes MUST be generated by a CSPRNG. Each code MUST contain ≥20 bits of entropy (e.g., 10 alphanumeric chars from a 32-char alphabet ≈ 50 bits, recommended). Set size: 10 codes.
2. **Storage**: Codes MUST be hashed with an approved password-hashing algorithm (Argon2id preferred; bcrypt cost ≥12 acceptable) using a per-code 32-bit (or larger) random salt. Plaintext codes are presented to the user **once** at generation time and never persisted plaintext server-side.
3. **Display**: Plaintext codes are shown **once** with a "save these now — they will not be shown again" warning, plus a download-as-text-file option. The page MUST set `Cache-Control: no-store` and use `autocomplete="off"` on any field re-displaying them.
4. **Single-use enforcement**: A redeemed code is marked redeemed atomically (DB row update with a `redeemed_at` timestamp under a transaction or compare-and-set). Concurrent redemption of the same code MUST result in exactly one success.
5. **Set replacement**: Generating a new set MUST invalidate **all** prior codes atomically before any new code is shown.
6. **Revocation**: The user can manually revoke their current set (e.g., from a "Lost my codes" link) without generating a new one; this leaves the account with TOTP-only recovery and MUST emit a security log event.
7. **Rate limiting on redemption**: Recovery-code submission at login is rate-limited to 5 attempts per 15 minutes per (user_id + IP). Exceeding this triggers the same lockout flow as F-02.
8. **No code logging**: Plaintext codes MUST NEVER appear in any log, error message, exception trace, analytics event, or third-party telemetry. Hashed codes MAY appear in audit logs only as a salted hash prefix (first 8 hex chars) for correlation.
9. **Notification**: Generation, regeneration, and revocation events MUST trigger a notification email to the on-file address.
10. **Classification**: Recovery code material is classified "high sensitivity / authenticator" in the data classification register (V14.1.1).

**Acceptance Criteria (testable)**:

- AC-03.1: Generated codes pass a chi-squared randomness check across a sample of 10,000 codes (no bias detectable at α=0.01).
- AC-03.2: A code redeemed once cannot be redeemed again, even if submitted within the same TCP request burst (concurrency test with 50 parallel submissions of the same code yields exactly one success).
- AC-03.3: Generating a new set of codes immediately invalidates all 10 prior codes (verified by attempting to redeem an old code post-generation).
- AC-03.4: Stored code records contain a hash and salt; database dump inspection reveals no plaintext codes anywhere (codes table, audit log, error log, mail-queue table).
- AC-03.5: Submitting 6 incorrect codes in 15 minutes triggers lockout per F-02.
- AC-03.6: Generation, regeneration, and revocation each trigger a notification email and a corresponding `recovery.codes.{generated|regenerated|revoked}` log event.
- AC-03.7: Inspection of application logs after a full redeem flow shows no occurrence of any plaintext code value.

**Securability Notes**: Recovery codes are bearer authenticators — they substitute for the second factor entirely. **Confidentiality** therefore dominates: hash-at-rest with proper KDF, never log plaintext, present-once UX. **Integrity** drives atomic single-use enforcement; a TOCTOU race here means the same code authenticates twice. **Authenticity** drives the "regenerate invalidates prior set" rule — without it, a leaked old set remains live. **Modifiability** matters because crypto best practice changes: storing the hash algorithm identifier alongside the hash (e.g., `argon2id$...`) lets you rotate KDFs without a forced re-issuance.

---

### Feature F-04: Recovery via Support Agent

**User story (unchanged)**: If automated recovery fails, the user contacts support. A support agent verifies the user's identity (verbal challenge against on-file data) and triggers a one-time bypass that sends an emergency reset link to the email on file.

**ASVS Mapping**: V6.3.7, V6.4.3, V8.1.1, V8.2.1, V16.3.1, V16.3.2, V16.3.3.

**Updated Requirements**:

1. **Verification script (documented)**: A documented identity-verification script (knowledge factors only the legitimate user would have — recent order ID + last 4 of billing zip + email-on-file confirmation, never SSN/full DOB) MUST be followed. The script and its acceptance criteria MUST be version-controlled and reviewed quarterly. Knowledge-based questions ("what was your favorite teacher") are NOT permitted (V6.4.2).
2. **Restricted authorization**: The "trigger emergency reset" function MUST only be callable by accounts in the `support.recovery_admin` role. Function-level access is enforced server-side; the agent UI MUST NOT be the sole gate.
3. **No silent MFA bypass**: The emergency action MUST send a reset link to the email on file (NOT to an attacker-supplied address) AND MUST require the user to complete their existing 2FA challenge on the new-password page if 2FA was enabled. If the user has lost both password and 2FA, the agent MUST NOT be able to clear MFA in a single action — clearing MFA is a separate, logged action that triggers a 24-hour cooling-off period during which the account cannot be logged into until the user confirms the change via a separate email-on-file confirmation.
4. **Two-channel confirmation for high-risk overrides**: When both password reset AND MFA reset are requested in the same support interaction, the system MUST require a second support agent (or a supervisor role) to approve before the action commits. The approving agent MUST be a different identity than the initiating agent.
5. **User notification**: The user MUST receive an email (and SMS, if a verified phone is on file) on any support-initiated recovery action, including agent identifier (anonymized to "Support Agent #ID") and ticket reference.
6. **Audit trail**: Every support-initiated recovery event MUST be logged with: timestamp (UTC), agent_id, supervisor_id (if any), ticket_id, action_type, target_user_id, source IP of agent terminal, and outcome. These records MUST be retained ≥1 year and stored in the immutable security log store (see V16.4).
7. **Rate / volume limits**: A single agent MUST NOT be able to trigger >10 emergency resets per 24-hour rolling window without supervisor approval.
8. **No password choosing**: Agents MUST NOT be able to set or view the user's new password (V6.4.6 alignment, even though that requirement is L3 — applied here as a hardening because of the elevated-privilege nature of the function).

**Acceptance Criteria (testable)**:

- AC-04.1: An agent without the `support.recovery_admin` role attempting to call the emergency-reset endpoint receives 403 and an authorization-failure log event is emitted.
- AC-04.2: An emergency-reset always dispatches the email to the address currently on file; submitting a different target address in the request body is ignored (server uses on-file address only).
- AC-04.3: For a 2FA-enabled user, the emergency-reset link does not bypass MFA on the new-password page.
- AC-04.4: A combined password+MFA reset cannot complete with a single agent's action — the audit log shows two distinct authenticated agent identities before commit.
- AC-04.5: Every emergency reset emits a structured log entry with all fields listed in requirement 6, and these entries appear in the SIEM within 5 minutes.
- AC-04.6: A single agent's 11th emergency reset within 24h is blocked pending supervisor approval; an alert is raised.
- AC-04.7: The user receives a notification email (and SMS where applicable) within 60 s of any support-initiated action.
- AC-04.8: The agent UI never displays a "set new password" field for the target user (manual code review + functional test).

**Securability Notes**: This is the only flow with a privileged human in the loop, which makes it the highest-trust and highest-risk path simultaneously. **Accountability** is the dominant SSEM concern — every step needs an attributable, tamper-resistant audit record because the social-engineering attack surface is large. **Authenticity** drives the "agent cannot redirect the email" rule and the supervisor co-sign on combined password+MFA resets, which mirrors the FIASSE trust-boundary discipline (the agent is *inside* the system but is still subject to strict validation at this control). **Confidentiality**: the documented script MUST avoid SSN/full DOB to prevent agents from accumulating or being phished out of high-value PII. **Modifiability**: the verification script will need to evolve as fraud patterns shift, so it lives in version control with a change-review process — not in a wiki page that drifts.

---

## 4. Cross-Cutting Securability Requirements

These apply to **all** four features and to the recovery surface as a whole.

### 4.1 Anti-Automation & Rate Limiting (ASVS V6.3.1, V2.4.1, V6.6.3)

- A central rate-limiting middleware MUST front all four recovery endpoints (`/recovery/request`, `/recovery/confirm`, `/recovery/unlock-request`, `/recovery/unlock-confirm`, `/recovery/code-redeem`, `/support/emergency-reset`).
- Default envelopes (per-email, per-IP, global) are configurable without code change.
- Triggered limits MUST emit `anti_automation.triggered` events with the limit type and identifier.
- AC-X.1: Load test of 100 req/s sustained against `/recovery/request` from a single IP shows ≥99% rejected after the configured threshold and the application latency on legitimate endpoints unaffected (>p95 latency degradation <10%).

### 4.2 Authentication-Pathway Consistency (ASVS V6.3.4)

- The four recovery features MUST be enumerated in the authentication architecture document (V6.1.1, V6.3.4) alongside the existing username/password and 2FA login paths.
- No "shadow" recovery path may exist (e.g., legacy admin-only endpoint, staff-only "impersonate" feature). Any such existing path MUST be inventoried and either removed or formally added to this PRD before launch.

### 4.3 Transport & Cookie Security (ASVS V14.x, V7.2)

- All recovery endpoints MUST be HTTPS-only with HSTS (max-age ≥31536000, includeSubDomains).
- Session cookies MUST be `Secure`, `HttpOnly`, `SameSite=Lax` (or `Strict` where compatible).
- Reset, unlock, and emergency-reset URLs MUST NOT include identifying personal data in the path or query (only the opaque token).

### 4.4 Data Classification & Privacy (ASVS V14.1, GDPR)

- The data-classification register MUST list: reset tokens, unlock tokens, recovery codes (hashed), notification emails, and support-tool audit records, each with retention, encryption-at-rest, and access-control rules.
- For EU users, the DPIA already on file MUST be updated to cover the recovery surface; lawful basis is "performance of contract" for the user's own recovery and "legitimate interest" for fraud-detection logging.
- Account deletion MUST cascade to all recovery artifacts (tokens, hashed codes, lockout records) within the documented SLA, except where retention is required for fraud investigation (and that retention is documented and time-bounded).

### 4.5 Security Logging (ASVS V16.1–V16.4)

- A logging-inventory entry MUST exist for the recovery domain, listing each event type, fields, destination, retention, and access controls (V16.1.1).
- Required event types (non-exhaustive): `recovery.reset.{requested|issued|redeemed|expired|reuse_attempt}`, `recovery.unlock.{requested|issued|redeemed|expired|reuse_attempt}`, `recovery.codes.{generated|regenerated|redeemed|revoked}`, `recovery.lockout.{triggered|auto_expired|suspected_targeted_attack}`, `recovery.support.{verified|reset_initiated|mfa_cleared|approved|denied}`, `auth.notification.sent`, `anti_automation.triggered`, `authz.denied`.
- All entries MUST include: ISO-8601 UTC timestamp, request_id, user_id (where applicable), source_ip, user_agent, event_type, outcome.
- All entries MUST be encoded to prevent log injection (V16.4.1) — no untrusted strings concatenated into log lines.
- No plaintext token, recovery code, password, or full email body MAY appear in any log. Email addresses MAY be hashed or partially masked (`a***@example.com`) as documented in the inventory.
- Logs MUST be shipped to a logically separate, append-only store within 5 minutes of emission (V16.4.3); access to the store MUST be role-restricted.

### 4.6 Cryptographic Hygiene (ASVS V11.1)

- The cryptographic inventory MUST list: token hash function (SHA-256 baseline), recovery-code KDF (Argon2id with documented parameters), HMAC keys for any token signing, and TLS certificate(s) used by the recovery endpoints.
- All keys are managed via the existing KMS; no hard-coded keys, no environment-only keys.
- Algorithm identifiers MUST be stored alongside hashes/MACs to enable algorithm migration (PQC readiness, V11.1.4 — flagged for future).

### 4.7 Email Delivery Integrity (SendGrid integration)

- Recovery emails MUST be sent from a domain protected by SPF, DKIM, and DMARC `p=reject` to reduce phishing susceptibility.
- The "from" address MUST be a no-reply address dedicated to recovery (e.g., `recovery@<brand>.com`), not shared with marketing.
- The email body MUST clearly state "If you did not request this, do nothing — the link will expire in 10 minutes" and link to a self-service "this wasn't me" workflow.

### 4.8 Latency Budget (Constraint Compliance)

- The original constraint "MUST NOT introduce more than 200 ms of latency to the login flow" is preserved. The login fast-path performs only a counter check and a constant-time generic response when the account is in a locked state; heavy work (email send, anomaly scoring) is deferred to async workers. AC-X.2: 95th-percentile login latency post-rollout MUST remain within 200 ms of pre-rollout baseline measured over a representative 24-hour traffic sample.

---

## 5. Open Gaps and Assumptions

### Assumptions

- **A1**: The portal already has structured logging infrastructure and a SIEM destination; this PRD adds events to it but does not require greenfield logging design.
- **A2**: A KMS exists for key management.
- **A3**: SendGrid is the only outbound email channel and SPF/DKIM/DMARC are configurable on the sender domain.
- **A4**: A documented data-classification register exists; this PRD updates it.
- **A5**: A support tooling system exists where role-based access (`support.recovery_admin`, supervisor) can be enforced.
- **A6**: The existing 2FA implementation is TOTP-based; passkey/WebAuthn migration is out of scope for this PRD.

### Open Gaps (require product/security decision before implementation)

- **G1 — SMS notification channel for F-04**: Requirement 5 asks for SMS notifications when a verified phone is on file, but the portal does not currently store/verify phone numbers. Decision needed: collect phone? omit SMS? defer to a follow-up PRD?
- **G2 — Multi-user approval threshold (ASVS 2.3.5, V6.4.6)**: At L2 baseline, multi-user approval is not required. We have applied it specifically to the combined password+MFA reset case. If product/security wants to broaden it (e.g., to all emergency resets above N/day), specify the trigger and approver role.
- **G3 — Lockout-counter scope**: The original PRD says "5 failed attempts within 10 minutes per account." We have proposed per-(user_id) AND per-(source_ip × user_id) for a defense-in-depth distinction. Confirm scope, and whether successful authentication from a different IP should reset the counter for *all* IPs.
- **G4 — Enumeration vs UX trade-off on F-02**: The recommendation hides "your account is locked" from the login response (no enumeration). Product may choose to relax this (e.g., show locked-state message only after a CAPTCHA challenge succeeds). This is a defensible variant; document the chosen position in V6.1.1.
- **G5 — User-side recovery for completely-lost-credentials**: If a user loses password, 2FA device, AND access to the email on file, F-04 still requires email-on-file delivery, which they cannot receive. Today, the implicit answer is "create a new account / lose order history." Product needs to decide whether a documented identity-proofing escalation (e.g., government-ID upload to a vetted KYC vendor) is in scope.
- **G6 — Adaptive risk signals (V8.2.4, L3)**: We have not required adaptive risk-based step-up because this is L3. If the threat model later includes targeted account takeover (high-value B2B sub-tenants?), L3 escalation for V6.3.5 / V8.2.4 should be considered.
- **G7 — Bot detection layer**: V2.4 anti-automation may need a CAPTCHA / proof-of-work layer beyond simple rate limits if attacker volume is high. Out of scope for v1; flagged for follow-up.

### Acceptance (revised from original)

- Users can recover access in under 5 minutes for the common case (preserved).
- Support team's recovery-related tickets drop by 30% within 90 days of launch (preserved).
- **Added**: Zero successful account takeovers via the recovery surface in the first 90 days, measured by SOC review of recovery-related security log events.
- **Added**: Zero P0/P1 security findings on the recovery surface in pre-launch ASVS L2 verification.
- **Added**: 95th-percentile login latency unchanged (within 200 ms baseline).
