# PRD: Merchant Payouts API v2 — Securability-Enhanced

> Enhancement applied: OWASP ASVS 5.0 coverage and FIASSE/SSEM annotations.
> Source PRD preserved verbatim under each feature; new requirements are explicitly tagged with their ASVS reference.

## Context

We operate a multi-sided marketplace. Merchants sell goods to consumers; we collect payment from consumers and remit net proceeds (gross sales minus fees and refunds) to merchants on a weekly cadence. This PRD covers v2 of the Merchant Payouts API, which lets merchants programmatically read payout history and trigger on-demand payouts to their bank account.

Volume: ~40k active merchants, ~$120M/month in payouts, ~$1.5B/year. Subject to PCI-DSS (we tokenize, but issuance and reconciliation touch the regulated zone) and varying state money-transmitter regulations.

---

## ASVS Level Decision

**Chosen Level**: 3

**Rationale**: This API moves money — ~$120M/month in merchant payouts with direct bank-account destination control — and explicitly sits in PCI-DSS scope plus money-transmitter regulatory regimes. Compromise of any feature here causes severe material impact: direct financial loss to merchants, reportable regulatory incidents, and SOC 2 audit findings. Level 1 (internal/low-sensitivity) and Level 2 (typical production) are both insufficient: a successful attack on `POST /v2/payouts` or `PUT /v2/payouts/schedule` is an immediate financial-fraud event, and reconciliation/listing endpoints leak PCI-adjacent data (bank account fingerprints, gross sales, fees). Attackers targeting payment platforms are well-resourced and motivated, which matches ASVS's L3 threat-actor profile.

**Feature-Level Escalations**: None — every feature in this PRD is treated at L3 baseline. Read-only endpoints (F-01, F-02) inherit the same level because their data feeds reconciliation and could be abused for merchant-account enumeration or data exfiltration.

---

## Feature ↔ ASVS Coverage Matrix

Every feature × every applicable requirement at L3 (which includes L1 and L2). Coverage is judged against the original PRD text only; "Missing" means the original PRD does not state or imply the control.

| Feature | ASVS Section | Requirement ID | Level | Coverage | PRD Change Needed |
|---------|--------------|----------------|-------|----------|-------------------|
| F-01    | V2.2         | 2.2.1, 2.2.2   | 1     | Missing  | Add input validation rules for `from`/`to` query params (ISO date, max window, server-side enforcement) |
| F-01    | V2.4         | 2.4.1          | 2     | Missing  | Add per-merchant and per-IP rate limits to prevent bulk history scraping |
| F-01    | V4.1         | 4.1.1          | 1     | Missing  | Specify `application/json; charset=utf-8` response Content-Type |
| F-01    | V4.1         | 4.1.3          | 2     | Missing  | Forbid client-controllable forwarded headers from changing identity (X-Forwarded-For, X-User-ID) |
| F-01    | V4.1         | 4.1.4          | 3     | Missing  | Reject methods other than GET/OPTIONS on this path |
| F-01    | V6           | (auth context) | 1–3   | Missing  | API-key auth is named but not specified; replace/augment with strong API auth (see cross-cutting) |
| F-01    | V8.2         | 8.2.1, 8.2.2   | 1     | Partial  | Implicit (merchant sees own payouts) — make tenant scoping an explicit, server-enforced requirement |
| F-01    | V8.2         | 8.2.3          | 2     | Missing  | Field-level access for sensitive fields (bank account fingerprint) explicitly defined |
| F-01    | V8.4         | 8.4.1          | 2     | Missing  | Cross-tenant isolation explicit (no payout from another merchant ever returnable) |
| F-01    | V12.1        | 12.1.1         | 1     | Missing  | Specify TLS 1.2+/1.3 only on the API edge |
| F-01    | V12.2        | 12.2.1, 12.2.2 | 1     | Missing  | HTTPS-only with publicly trusted certs, no fallback to HTTP |
| F-01    | V13.4        | 13.4.2         | 2     | Missing  | Disable debug/stack traces in prod responses |
| F-01    | V14.1        | 14.1.1, 14.1.2 | 2     | Missing  | Classify payout list fields (esp. bank fingerprint, amounts) into protection levels |
| F-01    | V14.2        | 14.2.1, 14.2.4 | 1–2   | Missing  | Sensitive data not in URL/query; minimize response payload |
| F-01    | V14.2        | 14.2.6         | 3     | Missing  | Mask bank account fingerprint by default; full value only on explicit consent |
| F-01    | V16.2        | 16.2.1, 16.2.5 | 2     | Missing  | Structured logs with metadata; never log raw bank fingerprints or PAN-derived data |
| F-01    | V16.3        | 16.3.1, 16.3.2 | 2     | Missing  | Log auth and authorization decisions for list calls |
| F-02    | V2.2         | 2.2.1          | 1     | Missing  | Validate `payout_id` shape (opaque, server-issued, length-bounded) |
| F-02    | V4.1         | 4.1.1, 4.1.4   | 1, 3  | Missing  | Content-Type and method allowlist as F-01 |
| F-02    | V8.2         | 8.2.1, 8.2.2   | 1     | Missing  | Enforce server-side ownership check on every detail fetch (BOLA mitigation) |
| F-02    | V8.2         | 8.2.3          | 2     | Missing  | Field-level read scoping: line-item breakdown fields restricted by role/permission |
| F-02    | V8.4         | 8.4.1          | 2     | Missing  | Cross-tenant access to a known payout_id must return same response as not-found |
| F-02    | V14.2        | 14.2.6         | 3     | Missing  | Mask bank fingerprint and any PAN-derived tokens |
| F-02    | V16.3        | 16.3.2         | 3     | Missing  | Log every access to payout detail (sensitive-data access audit) |
| F-03    | V2.2         | 2.2.1, 2.2.3   | 1, 2  | Missing  | Validate amount (positive, currency-precision-correct, ≤ available balance), currency (ISO 4217 allowlist), bank_account_id (server-owned reference); reject inconsistent combos |
| F-03    | V2.3         | 2.3.1, 2.3.2   | 1, 2  | Partial  | "Verify available balance" is named; expand to enforce sequential workflow, per-merchant velocity limits, and explicit business-logic limits |
| F-03    | V2.3         | 2.3.3          | 2     | Missing  | Atomic transaction: balance debit and payout creation succeed/fail together |
| F-03    | V2.3         | 2.3.4          | 2     | Missing  | Locking to prevent double-spend / concurrent on-demand payouts of the same balance |
| F-03    | V2.3         | 2.3.5          | 3     | Missing  | High-value payouts above a documented threshold require multi-party / step-up approval |
| F-03    | V2.4         | 2.4.1, 2.4.2   | 2, 3  | Missing  | Anti-automation: cap on-demand payouts per merchant per window; reject implausibly fast successive submissions |
| F-03    | V4.1         | 4.1.1, 4.1.4   | 1, 3  | Missing  | Content-Type, method allowlist |
| F-03    | V6.5         | 6.5.x          | 2     | Missing  | Step-up authentication / re-auth required to trigger on-demand payout |
| F-03    | V8.2         | 8.2.1, 8.2.2   | 1     | Partial  | Original PRD requires "previously verified" bank account; make ownership and verification status checks explicit and server-enforced |
| F-03    | V8.3         | 8.3.1          | 1     | Missing  | All authorization decisions enforced server-side; no client-supplied trust signals |
| F-03    | V11          | 11.x           | 1–3   | Missing  | Idempotency key (UUID/CSPRNG, 128-bit entropy) to prevent replayed/double-charge submissions |
| F-03    | V14.2        | 14.2.6         | 3     | Missing  | Bank fingerprint never returned in full from this endpoint |
| F-03    | V16.3        | 16.3.1, 16.3.3 | 2     | Missing  | Log every payout creation attempt (success/failure), step-up outcome, and rejected attempts (limits, validation, ownership) |
| F-03    | V16.5        | 16.5.3         | 2     | Missing  | Fail-closed: validation failure must never result in a created payout |
| F-04    | V2.2         | 2.2.1, 2.2.3   | 1, 2  | Missing  | Validate cadence (`weekly`/`biweekly`/`daily` allowlist), day_of_week (0–6 or named-day allowlist); reject inconsistent combos (e.g., daily + day_of_week) |
| F-04    | V2.3         | 2.3.2          | 2     | Missing  | Cadence-change frequency limits to prevent timing-attack abuse |
| F-04    | V2.4         | 2.4.1          | 2     | Missing  | Rate-limit cadence updates per merchant |
| F-04    | V6.5         | 6.5.x          | 2     | Missing  | Step-up authentication required to change payout schedule (impacts financial flow) |
| F-04    | V8.2         | 8.2.1          | 1     | Missing  | Server-side authorization that the caller is the merchant owner |
| F-04    | V8.3         | 8.3.2          | 3     | Missing  | Schedule changes apply immediately and are reflected in the next scheduling decision |
| F-04    | V14.1        | 14.1.2         | 2     | Missing  | Schedule change is "sensitive operation" — define notification/audit obligations |
| F-04    | V16.3        | 16.3.1, 16.3.3 | 2     | Missing  | Log every schedule change with prior+new value, actor, IP, UA, and step-up outcome |
| F-05    | V9.1         | 9.1.1, 9.1.2   | 1     | Partial  | Original PRD says merchant verifies signature; specify the signing scheme, allowed algorithms, and a no-`alg:none` rule |
| F-05    | V9.2         | 9.2.1, 9.2.3   | 1, 2  | Missing  | Signed webhook payloads include timestamp/expiry and an audience/endpoint binding |
| F-05    | V11.5        | 11.5.1         | 2     | Missing  | Webhook signature is generated with CSPRNG-backed key material and ≥128-bit entropy |
| F-05    | V11.4        | 11.4.1, 11.4.3 | 1, 2  | Missing  | Use approved hash (e.g., HMAC-SHA-256) — never MD5/SHA-1 — for the signature |
| F-05    | V12.2        | 12.2.1, 12.2.2 | 1     | Missing  | Outbound webhook delivery uses HTTPS with publicly trusted certs, no fallback |
| F-05    | V12.3        | 12.3.2         | 2     | Missing  | Validate the merchant's TLS certificate chain on outbound delivery |
| F-05    | V13.2        | 13.2.4, 13.2.5 | 2     | Partial  | Allowlist of merchant webhook URLs (host/scheme/port pattern) to prevent SSRF / internal-network abuse |
| F-05    | V13.2        | 13.2.6         | 3     | Partial  | The 60-second SLA is named; add explicit timeout, retry, and back-off policy to prevent cascading failures |
| F-05    | V14.2        | 14.2.4         | 2     | Missing  | Webhook payloads must minimize sensitive data; never include raw bank fingerprints or PAN-derived data |
| F-05    | V16.3        | 16.3.1, 16.3.3 | 2     | Missing  | Log every webhook send, signature failure on retry, and merchant-side delivery-failure pattern |
| F-05    | V16.5        | 16.5.2         | 2     | Missing  | Circuit-breaker on per-merchant webhook endpoint that's repeatedly failing |

---

## Enhanced Feature Specifications

### Feature F-01: List Payouts

**Actor**: Authenticated merchant (machine-to-machine via API credential)
**Data**: Payout records (PCI-adjacent: amount, currency, scheduled date, status, **destination bank account fingerprint**); date-range query parameters
**Trust Boundaries**: merchant client → public API edge; API → payouts datastore; API → log/audit pipeline

**ASVS Mapping**: V2.2.1, V2.2.2, V2.4.1, V4.1.1, V4.1.3, V4.1.4, V8.2.1, V8.2.2, V8.2.3, V8.4.1, V12.1.1, V12.2.1, V12.2.2, V13.4.2, V14.1.1, V14.2.1, V14.2.4, V14.2.6, V16.2.1, V16.2.5, V16.3.1, V16.3.2

**Updated Requirements**:
- **R-01.1** (original) Merchants call `GET /v2/payouts?from=YYYY-MM-DD&to=YYYY-MM-DD` with their API credential. The response lists payouts in the window (ID, amount, currency, scheduled date, status, **masked** destination bank account fingerprint).
- **R-01.2** (V2.2.1, V2.2.2) `from` and `to` are validated server-side as ISO-8601 dates; window must be ≤ 90 days; `from` ≤ `to`; client-side validation is not relied upon.
- **R-01.3** (V8.2.1, V8.2.2, V8.4.1) Authorization is enforced server-side: only payouts owned by the authenticated merchant are returned. A merchant attempting to query data scoped to another merchant receives the same response shape and timing as a merchant with no payouts in the window.
- **R-01.4** (V8.2.3, V14.2.6) The bank account fingerprint is masked by default (e.g., last-4 digits or hashed token reference). The full fingerprint is never returned by this endpoint.
- **R-01.5** (V14.2.1) `from`, `to`, and any account identifiers are sent in the URL query *only* as non-sensitive scoping data. API credentials, session tokens, or signing material must never appear in the URL or query string.
- **R-01.6** (V2.4.1) The endpoint is rate-limited per merchant credential and per source IP (e.g., 60 req/min per credential, with documented bursting rules).
- **R-01.7** (V4.1.1) Every response includes `Content-Type: application/json; charset=utf-8`.
- **R-01.8** (V4.1.3) Inbound `X-Forwarded-*` and similar intermediary-set headers cannot override authentication or merchant identity at the application tier.
- **R-01.9** (V4.1.4) The path accepts only `GET` and `OPTIONS`; all other HTTP methods return `405 Method Not Allowed`.
- **R-01.10** (V12.1.1, V12.2.1, V12.2.2) The endpoint is served only over TLS 1.2+ (TLS 1.3 preferred) with publicly trusted certificates. There is no HTTP fallback.
- **R-01.11** (V13.4.2, V16.5.1) Production responses never include stack traces, internal paths, query strings, or framework version banners. Errors return a stable `error_code` plus a request correlation ID.
- **R-01.12** (V14.1.1, V14.1.2) Bank account fingerprint and gross-amount fields are classified at the highest applicable internal protection level; this classification is documented and drives logging and storage controls.
- **R-01.13** (V16.2.1, V16.2.5, V16.3.1, V16.3.2) Every list call is logged with: timestamp (UTC), merchant ID, request ID, source IP, user-agent, requested window, count returned, and outcome. Bank fingerprints are never written to logs in cleartext; if logged at all, they are hashed or last-4-only.

**Acceptance Criteria**:
- Submitting `from=2025-01-01&to=2026-01-01` (>90-day window) returns HTTP 400 with `error_code=window_too_large`; no payouts are returned.
- Authenticated merchant A querying with merchant B's identifier in any header or parameter receives only A's payouts; the response shape and `200`/empty-array behavior is identical to A having no payouts in that window.
- Response `Content-Type` header is exactly `application/json; charset=utf-8` and matches body framing.
- `POST`, `PUT`, `DELETE`, `PATCH`, `TRACE` against `/v2/payouts` (when intended-as-list) return `405`.
- TLS endpoint refuses TLS 1.0 / 1.1 / SSLv3 handshakes; `curl --tlsv1.1` fails to negotiate.
- Bank account field in every list response shows only the masked form; full fingerprint never appears.
- A 200-line audit log query for a single merchant's list calls returns structured records with all required fields and no raw bank fingerprints.
- Sustained traffic above the documented per-credential rate begins receiving `429 Too Many Requests` with a `Retry-After` header within one minute.

**Securability Notes**: F-01 is the primary data-exfiltration target on this API — it can leak banking metadata across the merchant tenant boundary. The load-bearing concerns are *server-enforced tenant scoping* (BOLA prevention) and *response minimization* (FIASSE S6.4 trust-boundary discipline; never let a client-supplied identifier widen the result set). Logging here is in tension with privacy: every access must be auditable (SSEM Accountability), but raw bank fingerprints must never enter the log pipeline (Confidentiality). Centralize the masking and tenant-scoping logic in a single module so that future fields and tenancy changes propagate without scattering policy across handlers (Modifiability, Analyzability).

---

### Feature F-02: Get Payout Detail

**Actor**: Authenticated merchant
**Data**: Single payout record with full line-item breakdown (gross sales, fees, refunds, adjustments, net amount, **source order IDs and amounts**, destination bank fingerprint)
**Trust Boundaries**: merchant client → public API edge; API → payouts datastore; API → orders datastore; API → log/audit pipeline

**ASVS Mapping**: V2.2.1, V4.1.1, V4.1.4, V8.2.1, V8.2.2, V8.2.3, V8.4.1, V12.1.1, V12.2.1, V13.4.2, V14.2.6, V16.3.2, V16.5.1

**Updated Requirements**:
- **R-02.1** (original) Merchants call `GET /v2/payouts/{payout_id}` and receive the line-item breakdown.
- **R-02.2** (V2.2.1) `payout_id` is validated as an opaque, server-issued identifier with a fixed shape (length-bounded, charset-restricted). Sequentially numeric or guessable IDs are not used.
- **R-02.3** (V8.2.1, V8.2.2, V8.4.1) Server-side ownership check on every fetch: the authenticated merchant must own the requested payout. A merchant requesting another merchant's `payout_id` receives `404 Not Found` with the same response shape and timing characteristics as a non-existent ID.
- **R-02.4** (V8.2.3) Field-level access: if internal/admin views ever exist, they must be selected by an explicit role/permission; merchants only see merchant-facing fields.
- **R-02.5** (V14.2.6) Bank account fingerprint is masked. Source-order PAN-derived tokens or internal references are not included in the response.
- **R-02.6** (V16.3.2) Every detail fetch is logged with merchant ID, payout_id, request ID, source IP, user-agent, outcome, and reason on denial. The line-item *content* itself is not logged.
- **R-02.7** (V4.1.1, V4.1.4, V12.1.1, V12.2.1, V13.4.2, V16.5.1) HTTP, TLS, error-handling, and information-disclosure requirements per cross-cutting controls.

**Acceptance Criteria**:
- Requesting another merchant's known payout_id returns HTTP 404 with the same body schema and timing distribution (within tolerance) as a request for a fabricated, never-existed ID.
- Requesting `/v2/payouts/'; DROP TABLE...` (or any input failing the opaque-ID shape check) returns 400 with `error_code=invalid_payout_id`; no DB query is issued.
- The response body for a valid call contains a masked `bank_account` field and no full bank fingerprint, account number, or routing number.
- The audit log for a single payout_id over a 24-hour window enumerates every access, including denials, with caller identity preserved.

**Securability Notes**: F-02 is the canonical IDOR/BOLA target — the URL contains the resource identifier and the temptation is to skip the per-call ownership check on the assumption "they have a valid token". Treat the `payout_id` as an *untrusted client claim about a server-owned resource* (FIASSE S6.4.1.1, Derived Integrity): authorize on each request, never cache the trust decision across requests. Identical 404 responses for "not yours" and "doesn't exist" close the enumeration side-channel (Confidentiality). All access is auditable so abuse patterns (e.g., scripted ID-walking) can be detected (Accountability).

---

### Feature F-03: Trigger On-Demand Payout

**Actor**: Authenticated merchant
**Data**: `amount`, `currency`, `destination_bank_account_id` (input); merchant balance state, payout record, audit trail (server-owned state); destination bank account verification status
**Trust Boundaries**: merchant client → public API edge (writes that move money); API → balance/ledger datastore; API → bank-account datastore; API → payment-rails service; API → audit pipeline

**ASVS Mapping**: V2.2.1, V2.2.2, V2.2.3, V2.3.1, V2.3.2, V2.3.3, V2.3.4, V2.3.5, V2.4.1, V2.4.2, V4.1.1, V4.1.4, V6.5.1–6.5.5, V8.2.1, V8.2.2, V8.3.1, V8.3.3, V11.4.1, V11.5.1, V12.1.1, V12.2.1, V14.2.6, V16.3.1, V16.3.3, V16.5.3

**Updated Requirements**:
- **R-03.1** (original, strengthened) Merchants call `POST /v2/payouts` with `{amount, currency, destination_bank_account_id, idempotency_key}`. The server verifies available balance, creates a payout, and returns its ID. The destination must be a bank account the merchant previously verified via micro-deposit and which is currently in `verified` status.
- **R-03.2** (V2.2.1, V2.2.2, V2.2.3) Schema validation, server-side: `amount` is a positive integer in minor units, ≤ documented per-merchant per-day cap, ≤ available balance; `currency` is on a configured ISO 4217 allowlist matching the merchant's settlement profile; `destination_bank_account_id` matches an opaque, server-issued shape. Inconsistent combinations (e.g., currency mismatch with destination account) are rejected.
- **R-03.3** (V8.2.1, V8.2.2, V8.3.1) Server-side authorization: the authenticated merchant must own both the balance and the destination bank account; ownership and verification status are re-checked on every request and are never trusted from client-supplied state.
- **R-03.4** (V11.5.1, idempotency) Every request must include an `Idempotency-Key` header (UUIDv4 or 128-bit CSPRNG token). The server stores the key with the resulting payout ID for at least 24 hours; a duplicate key with an identical payload returns the original payout ID; a duplicate key with a *different* payload returns `409 Conflict` and is logged as an anomaly.
- **R-03.5** (V2.3.1, V2.3.3, V2.3.4) The balance-debit and payout-creation are performed atomically within a single transaction (or compensating-saga with documented rollback). Concurrent on-demand payouts against the same merchant balance are serialized via a per-merchant lock to prevent double-spend.
- **R-03.6** (V2.3.2, V2.4.1) Documented per-merchant velocity limits: e.g., max N on-demand payouts per 24h, max cumulative amount per 24h. Limits are enforced server-side and produce `429` with `error_code=velocity_limit_exceeded`.
- **R-03.7** (V2.3.5, V6.5.x) On-demand payouts above a documented high-value threshold (e.g., ≥ $50,000 or ≥ 50% of trailing-30-day average) require either step-up authentication (re-auth within a short window) or multi-party approval, per documented policy.
- **R-03.8** (V2.4.2) Implausibly fast successive submissions from the same merchant credential are rejected (e.g., < 1s between consecutive POSTs is flagged as automation).
- **R-03.9** (V14.2.6) The response includes only the payout ID, status, and masked destination reference. The full bank account fingerprint is never returned by this endpoint.
- **R-03.10** (V16.3.1, V16.3.3, V16.5.3) Every request — accepted, rejected, rate-limited, validation-failed, ownership-denied, idempotency-conflict, and step-up-required — is logged with merchant ID, request ID, idempotency key (hashed), amount, currency, destination ref (masked), source IP, UA, decision, and decision reason. A validation or authorization failure must not, under any code path, result in a created payout (fail-closed).
- **R-03.11** (V4.1.1, V4.1.4, V12.1.1, V12.2.1) HTTP, TLS, and method-allowlist requirements per cross-cutting controls. `POST` only; idempotency is enforced via header, not via duplicate-suppression in retries.

**Acceptance Criteria**:
- Submitting `amount=-100` or `amount=0` returns 400 with `error_code=invalid_amount`; no balance debit; no payout record; one `payout_create_rejected` audit log line.
- Submitting `currency=XYZ` (not on allowlist) returns 400; no payout; one rejected audit log line.
- Submitting against a `destination_bank_account_id` that the merchant does not own returns the same `404`/`403` shape and timing as one that does not exist; no payout; logged as `payout_create_denied: ownership`.
- Submitting against an unverified bank account returns 422 with `error_code=destination_not_verified`; logged.
- Two concurrent requests with the same `Idempotency-Key` and identical payloads result in exactly one created payout; both responses return the same payout ID.
- Two requests with the same `Idempotency-Key` and *different* payloads: first returns 201 with payout ID; second returns 409 `idempotency_conflict`; both audited; no second payout created.
- 100 concurrent requests against a merchant with $X balance and $X payout amount each result in exactly one successful payout; the rest receive `409 Conflict` or `422 insufficient_balance`; total debited is exactly $X.
- An on-demand payout at or above the documented high-value threshold without a valid step-up token returns 401 `step_up_required`; with step-up satisfied, succeeds.
- Audit log query by `merchant_id` over a 1h window returns one structured record per request, including decision, reason, masked destination, and idempotency-key hash.

**Securability Notes**: F-03 is the highest-impact endpoint in the system: it directly moves money. The dominant FIASSE concern is *Derived Integrity* (S6.4.1.1) — `amount`, `destination_bank_account_id`, and (worst of all) "available balance" must never be trusted from client-supplied or client-cached state. Every authorization, balance-check, and verification-status decision is re-derived server-side per request. Idempotency is not just an availability feature; it is a *security* control against double-charging on retries (Integrity, Resilience). Atomicity (V2.3.3) and per-merchant locking (V2.3.4) prevent the classic race-condition exploit where parallel POSTs each see "balance OK" before either has debited. Step-up authentication on high-value transactions (V2.3.5, V6.5) is the primary control against compromised API credentials being used for one-shot maximum-extraction attacks. All decision points must be observable in the audit pipeline so that abnormal patterns (rapid-succession denials, idempotency conflicts, step-up failures) can drive monitoring (SSEM Accountability, FIASSE Transparency). Because this endpoint is in PCI-DSS and money-transmitter scope, the audit log is itself a regulated artifact — keep it write-once and out-of-band per V16.4.

---

### Feature F-04: Update Payout Schedule

**Actor**: Authenticated merchant
**Data**: `cadence` (`weekly` / `biweekly` / `daily`), `day_of_week`; merchant scheduling profile
**Trust Boundaries**: merchant client → public API edge; API → merchant-config datastore; API → audit pipeline

**ASVS Mapping**: V2.2.1, V2.2.3, V2.3.2, V2.4.1, V4.1.1, V4.1.4, V6.5.x, V8.2.1, V8.3.2, V12.1.1, V14.1.2, V16.3.1, V16.3.3

**Updated Requirements**:
- **R-04.1** (original) Merchants call `PUT /v2/payouts/schedule` with `{cadence, day_of_week}` to change automatic cadence between `weekly`, `biweekly`, or `daily`.
- **R-04.2** (V2.2.1) `cadence` validated against a strict allowlist `{weekly, biweekly, daily}`. `day_of_week` validated as an integer 0–6 or a named-day allowlist.
- **R-04.3** (V2.2.3) Inconsistent combinations rejected: e.g., `cadence=daily` with a `day_of_week` set returns 400 with `error_code=inconsistent_schedule`.
- **R-04.4** (V8.2.1) Server-side authorization: caller must be the merchant whose schedule is being changed.
- **R-04.5** (V6.5.x) Step-up authentication required to change cadence (this is a financially material change; without step-up, an attacker holding a stolen API key could redirect timing of large payouts).
- **R-04.6** (V2.3.2, V2.4.1) Cadence-change rate limits (e.g., max 5 changes per merchant per 30 days) are enforced; excess returns 429 with `error_code=schedule_change_throttled`.
- **R-04.7** (V8.3.2) Schedule change applies immediately to subsequent scheduling decisions; the prior schedule does not "carry over" beyond the in-flight payout already queued at the moment of change.
- **R-04.8** (V14.1.2, V16.3.1, V16.3.3) Every schedule change is logged with prior value, new value, merchant ID, source IP, UA, request ID, step-up outcome, and decision. An out-of-band notification is sent to the merchant's registered security/admin contact for every successful change.
- **R-04.9** (V4.1.1, V4.1.4, V12.1.1) HTTP, TLS, and method-allowlist per cross-cutting controls; `PUT` only.

**Acceptance Criteria**:
- `cadence=fortnightly` or other non-allowlist value returns 400 `error_code=invalid_cadence`; no change; logged.
- `cadence=daily, day_of_week=3` returns 400 `error_code=inconsistent_schedule`; no change.
- A request without a valid step-up token returns 401 `step_up_required`; with step-up, succeeds.
- Six successive cadence changes within a 30-day window: the 6th is rejected with 429.
- After a successful change, an audit log line is created with prior and new cadence and the merchant receives an email/notification reflecting the change within a documented SLA.
- The next scheduled payout decision after the change uses the new cadence.

**Securability Notes**: F-04 looks low-risk but is a stealthy money-flow control: an attacker can slip large auto-payouts through by switching cadence to `daily` ahead of a planned exfiltration. Step-up authentication (V6.5) and out-of-band notification on change are the primary mitigations — both ensure the legitimate merchant has a chance to detect and respond (SSEM Accountability, Authenticity). Treat any schedule write as a sensitive financial-flow event with the same audit treatment as F-03.

---

### Feature F-05: Webhook on Payout State Change

**Actor**: Our system (sender); merchant-operated webhook endpoint (receiver)
**Data**: Payout state transition payload (payout ID, prior/new state, timestamp, merchant ID); webhook signing key
**Trust Boundaries**: API → outbound HTTP to merchant-operated URL (egress to potentially-untrusted networks); API → secret store; merchant verification logic

**ASVS Mapping**: V9.1.1, V9.1.2, V9.2.1, V9.2.3, V11.4.1, V11.4.3, V11.5.1, V12.2.1, V12.2.2, V12.3.2, V13.2.4, V13.2.5, V13.2.6, V13.3.x, V14.2.4, V16.3.1, V16.3.3, V16.5.2

**Updated Requirements**:
- **R-05.1** (original, strengthened) On every payout state transition (`queued → processing → paid → failed`), we POST a JSON payload to the merchant's configured webhook URL. The payload is signed; the merchant *must* verify the signature before acting on it.
- **R-05.2** (V9.1.1, V9.1.2, V11.4.1, V11.4.3) The signing scheme is documented (e.g., HMAC-SHA-256 over the canonical payload + timestamp). Allowed algorithms are on a server-controlled allowlist; `alg:none` and weak hashes (MD5, SHA-1) are forbidden. The scheme is published in our public docs so merchants can implement verification correctly.
- **R-05.3** (V9.2.1, V9.2.3) The signed payload includes a timestamp and an explicit recipient/audience binding (e.g., the merchant ID). Receiving systems are instructed to reject payloads where the timestamp is outside a documented tolerance window (default ±5 minutes) and where the audience does not match the configured merchant.
- **R-05.4** (V11.5.1, V13.3.x) Per-merchant signing keys are generated by a CSPRNG, ≥128-bit entropy, stored in our secrets manager (HSM-backed for the L3 case), rotated on a documented schedule, and rotatable on demand without downtime (publish overlapping `kid` values).
- **R-05.5** (V12.2.1, V12.2.2, V12.3.2) Outbound delivery is HTTPS-only with no fallback. We validate the merchant endpoint's TLS certificate chain against trusted public CAs; self-signed or expired certs cause delivery failure (logged), not silent acceptance.
- **R-05.6** (V13.2.4, V13.2.5) Merchant webhook URLs are subject to a configuration-time allowlist policy (https only; no `localhost`, RFC 1918 / link-local / loopback / metadata-service hosts; no internal-only TLDs; URL parsed and re-validated on send to prevent late-binding SSRF). DNS rebinding is mitigated via pin-and-validate of resolved IP at connect time.
- **R-05.7** (V13.2.6) Per-call timeout (e.g., connect 5s, read 10s); retry policy uses exponential back-off with jitter; max retry count and retry-window are documented; a per-merchant circuit-breaker disables delivery after N consecutive failures and re-enables on health-check or manual re-arm.
- **R-05.8** (V14.2.4) Webhook payloads contain only the minimum data needed for state-change handling (payout ID, prior/new state, timestamp, merchant ID, idempotency-key hash). No full bank fingerprints, no PAN-derived tokens, no line-item financial detail.
- **R-05.9** (V16.3.1, V16.3.3) Every send attempt, signature generation, retry, success, failure, circuit-breaker trip, and configuration change to a webhook URL is logged with structured metadata.
- **R-05.10** (V16.5.2) A failing merchant endpoint must not degrade the rest of the API's availability; failures are isolated per-merchant via the circuit-breaker pattern (R-05.7).
- **R-05.11** (original) State-change webhooks deliver within 60 seconds of the state transition for healthy endpoints; the SLA is suspended for endpoints in circuit-broken state.

**Acceptance Criteria**:
- A webhook delivered to a test endpoint can be verified using the published HMAC-SHA-256 scheme; replaying the same payload after a 6-minute delay is rejected by the documented receiver-side tolerance.
- Configuring a webhook URL of `http://...`, `https://localhost/...`, `https://10.x.x.x/...`, or `https://169.254.169.254/...` is rejected with `error_code=webhook_url_disallowed`; the disallowed URL never reaches the outbound HTTP client.
- DNS that resolves to a public IP at config time and to an internal IP at send time triggers the late-binding check and the request is dropped + logged as `webhook_target_invalid`.
- A merchant endpoint returning 5xx for N consecutive sends triggers the per-merchant circuit breaker; subsequent state changes for that merchant are queued/skipped per documented policy and other merchants' deliveries are unaffected.
- Rotating a merchant signing key allows the merchant to verify with either the old or new `kid` for the documented overlap window; after that, only the new key verifies.
- Audit log shows one structured record per send attempt, with merchant ID, payout ID, attempt number, outcome, latency, and `kid` used.

**Securability Notes**: F-05 is an *outbound* trust boundary — the merchant URL is effectively user-supplied and is the SSRF vector if not constrained (FIASSE S6.3 trust-boundary discipline; "treat the URL as adversarial input"). The signature scheme must be specified concretely; "the merchant verifies the signature" is a phrase, not a control — without an algorithm allowlist and `alg:none` rejection, attackers can substitute a weaker scheme (V9.1.2). Outbound failure handling (V13.2.6, V16.5.2) is a *security* concern as much as availability: an unbounded retry loop against a slow/hostile endpoint is a self-inflicted DoS. Key rotation, audience binding, and timestamp tolerance combine to make replay and forgery materially harder (Authenticity, Integrity). Centralize the signing, URL-validation, and retry/circuit-breaker logic in one outbound-delivery module so policy can evolve once (Modifiability).

---

## Cross-Cutting Securability Requirements

These apply to every feature in this PRD. They are stated once here to avoid repetition; each feature's ASVS mapping references them implicitly.

### Authentication and Identity (V6, V8.3, V13.2)
- **CC-01** (V13.2.1, V8.3.1) Replace static "API key" auth with short-lived bearer tokens (e.g., OAuth2 client credentials with rotating client secrets, or signed-request scheme with per-request nonce). API keys, if retained for backward compat, are scoped per merchant, rotatable, and revocable in real time.
- **CC-02** (V8.3.3) Where this API calls downstream services on behalf of a merchant, the merchant's identity (not a service account) governs downstream authorization decisions.

### Step-Up Authentication for Sensitive Operations (V6.5)
- **CC-03** Operations that change money flow (F-03 on-demand payout above threshold, F-04 schedule change, webhook URL change, signing-key rotation) require step-up authentication via a second factor or a re-authentication step within a documented short window (e.g., ≤ 5 min).

### Logging and Audit (V16.1, V16.2, V16.3, V16.4)
- **CC-04** (V16.1.1) A documented logging inventory exists covering every endpoint in this PRD: what events are logged, format, destination, retention, access controls.
- **CC-05** (V16.2.1, V16.2.2) Every log entry uses a common structured format and UTC timestamps; entries include who, when, where (IP, UA), what (action + resource), and outcome.
- **CC-06** (V16.2.5) Sensitive payment data (full bank fingerprint, account/routing numbers, PAN-derived tokens) is never written to logs in cleartext; if logged at all, it is hashed or last-4-only.
- **CC-07** (V16.3.1, V16.3.2, V16.3.3) Authentication outcomes, authorization denials, validation rejections, rate-limit trips, anti-automation rejections, and step-up outcomes are all logged.
- **CC-08** (V16.4.1, V16.4.2, V16.4.3) Logs are encoded against log-injection, are write-once / tamper-evident, and are streamed to a logically separate system that does not share an attack surface with the production API.

### Secrets and Key Management (V13.3, V11)
- **CC-09** (V13.3.1, V13.3.2) All API signing keys, webhook signing keys, downstream service credentials, and database credentials live in a secrets manager (HSM-backed for the L3 path). No secrets in source, build artifacts, or env-var dumps.
- **CC-10** (V13.3.4) All secrets have a documented rotation schedule and on-demand rotation capability.

### TLS and Transport (V12)
- **CC-11** (V12.1.1, V12.2.1, V12.2.2, V12.3.1) TLS 1.2 minimum (1.3 preferred) on all inbound and outbound paths, publicly trusted certificates externally, internal mTLS or equivalent strong service auth between internal services.

### Rate Limiting and Anti-Automation (V2.4)
- **CC-12** (V2.4.1) Every endpoint has a documented per-credential and per-IP rate limit. Excess returns `429 Too Many Requests` with `Retry-After`. Limits and current consumption are observable in logs and metrics.

### Error Handling (V16.5, V13.4)
- **CC-13** (V16.5.1, V13.4.2, V13.4.6) Production responses never include stack traces, internal paths, query strings, framework versions, or internal hostnames. Errors return `{error_code, message, request_id}` only.
- **CC-14** (V16.5.3) Validation, authorization, or balance-check failures are fail-closed: under no error path does a payout get created, a schedule get changed, or a webhook get sent.
- **CC-15** (V16.5.2) Downstream service failures (ledger, banking rails, secrets manager) are handled with circuit-breakers and graceful degradation; the API returns deterministic error codes rather than partial state.

### Configuration and Information Disclosure (V13.1, V13.4)
- **CC-16** (V13.1.1) All external services this API depends on (ledger, payment rails, secrets manager, log pipeline, email/notification) are documented with authentication mechanism, timeout, retry policy, and failure mode.
- **CC-17** (V13.4.2, V13.4.4, V13.4.5) Debug modes, `TRACE` HTTP method, and internal monitoring endpoints are disabled or unreachable from the public edge in production.

### Data Classification and Minimization (V14.1, V14.2)
- **CC-18** (V14.1.1, V14.1.2) Data classes — bank fingerprints, amounts, merchant identifiers, payout state, line-item detail — are classified with documented protection requirements (encryption at rest, masking rules, retention, who can read in logs).
- **CC-19** (V14.2.6) Responses return the minimum sensitive data required; bank fingerprints, account numbers, and PAN-derived tokens are masked by default and never returned in full.
- **CC-20** (V14.2.7) Retention policies for payout records, audit logs, and webhook delivery records are defined and enforced via automated lifecycle policies.

### Dependency and Supply Chain (V14 / V15-adjacent)
- **CC-21** Cryptographic primitives (HMAC-SHA-256, AES-GCM where applicable, TLS libraries) come from vetted, maintained libraries; no homebrew crypto. Library versions are tracked and patched on a documented cadence.

---

## Open Gaps and Assumptions

The following items were not resolvable from the input PRD and must be confirmed by product/engineering/security before implementation:

1. **Authentication mechanism details** — The PRD says "API key". CC-01 above proposes upgrading; product needs to confirm whether to deprecate API keys outright, run them in parallel with OAuth2 client credentials, or require signed-request envelopes. The decision affects F-01 through F-05.
2. **Step-up authentication mechanism** — The PRD has no second-factor or re-auth for sensitive ops. CC-03 prescribes it, but the actual factor (TOTP, hardware key, signed challenge from an admin console, etc.) must be chosen and matched to the merchant onboarding model.
3. **High-value threshold for F-03 multi-party approval** — V2.3.5 requires a documented threshold for step-up/multi-party. Suggested $50,000 or 50% of trailing-30-day average is illustrative; product must set the actual threshold.
4. **Velocity limits for F-03 and F-04** — Specific per-merchant limits (N payouts/24h, $X/24h, M schedule changes/30d) need product-supplied numbers.
5. **Idempotency window** — R-03.4 suggests 24h idempotency-key retention; payments-rails behavior may dictate longer (some processors require 7-day windows).
6. **Webhook signature scheme details** — Final choice (HMAC-SHA-256 vs Ed25519, header layout, canonicalization rules, `kid` rotation overlap window) is engineering's call but must be published before go-live.
7. **PCI-DSS scoping confirmation** — The PRD says "we tokenize, but issuance and reconciliation touch the regulated zone". Final classification of which exact fields fall in scope drives V14.1 and V16.2 controls (logging restrictions in particular).
8. **State money-transmitter regulations** — These vary by state and may impose additional logging, retention, or reporting requirements beyond ASVS L3. Legal/compliance must enumerate these and feed them into CC-04 and CC-20.
9. **Out-of-band notification channel** for F-04 (R-04.8) — Email is assumed; if SMS or in-app push is preferred, control specs change.
10. **Webhook URL change flow** — Not described in the PRD. CC-03 above implies it requires step-up; the actual UX/API surface for this needs its own feature spec or must be added here.
11. **Merchant role model inside an account** — The PRD describes "merchant" as a single actor, but most marketplaces have multiple users per merchant (owner, finance, support). Authorization decisions in F-02, F-03, F-04 may need a per-user role layer that this PRD does not currently surface.
12. **Bank-account change flow** — Out of scope per the PRD ("covered by separate PRD"), but F-03 depends on its security guarantees (verification status, ownership, micro-deposit confirmation). Confirm that the bank-account-verification PRD has equivalent ASVS L3 treatment.
13. **Test environment and test-data policy** — Not stated. PCI scoping typically forbids real card/bank data in non-prod; this should be added to V13/V15 cross-cutting requirements.

---

## Original Acceptance Criteria (preserved + extended)

From the original PRD:

- p99 latency under 800ms for list/detail endpoints. *(Retained.)*
- 99.95% availability for the API surface. *(Retained — see CC-15 for graceful-degradation expectations during downstream failures.)*
- All payout state changes deliver a webhook within 60 seconds. *(Retained for healthy endpoints; SLA is suspended for circuit-broken endpoints — see R-05.7, R-05.11.)*

Added by this enhancement:

- All endpoints meet ASVS 5.0 Level 3 verification criteria as mapped in the coverage matrix above.
- All audit log requirements (CC-04 through CC-08) are demonstrably exercised in pre-prod load tests.
- A red-team / pen-test pass against F-03 specifically validates: BOLA on `destination_bank_account_id`, race-condition double-spend on concurrent `POST /v2/payouts`, idempotency replay attack, and step-up bypass attempts.
