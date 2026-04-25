# Enhanced PRD: Merchant Payouts API v2 (FIASSE/SSEM + ASVS)

This document supersedes the original PRD for v2 of the Merchant Payouts API. It preserves the v1 feature intent and layers explicit ASVS coverage and FIASSE/SSEM securability guidance per feature, plus cross-cutting requirements that apply across the whole API surface.

---

## 1. ASVS Level Decision

**Selected baseline: ASVS Level 3** for all features that move money or expose payout history. ASVS Level 2 applies to read-only endpoints that are clearly non-sensitive (none in this PRD — every endpoint touches payout data).

### Rationale

- **Money movement at scale.** ~$1.5B/year of merchant payouts; an authorization, integrity, or business-logic flaw is a direct financial-loss event for both us and merchants. ASVS L2 is the typical "production web/API" baseline; L3 is mandated when the system has elevated attacker interest, sensitive data, and high-impact operations. All three apply here.
- **Regulated zone.** PCI-DSS in scope (issuance and reconciliation touch the regulated zone even though we tokenize); state money-transmitter regulations apply; SOC 2 audit pressure was explicitly called out by the requesting team. PCI's expectations on logging integrity, key management, and TLS hygiene align with L3 cryptographic and logging requirements.
- **Bank-account-level blast radius.** The destination of a payout is a bank account; misdirected funds are not easily clawed back. This pushes integrity, accountability, and business-logic protections to L3 (multi-user approval for high-value flows, immediate authorization revocation, per-message signatures).
- **Webhook attack surface.** F-05 sends signed webhooks to merchant-controlled URLs. SSRF, webhook spoofing, and replay are real threats; L3 is appropriate for the signing and outbound-allowlist requirements.

### Lower levels — why insufficient

- **L1** is for prototypes or low-risk internal systems; financial-grade APIs are not in scope.
- **L2** would cover most authentication, authorization, and logging baselines but would not require: per-message digital signatures (4.1.5), all authorization decisions logged on sensitive-data access (16.3.2 L3), HSM-backed key management (13.3.1 L3 / 13.3.3), multi-user approval for high-value transfers (2.3.5), or immediate revocation enforcement (8.3.2). All of these are directly material to a merchant-payouts API.

### Per-feature level escalation

| Feature | Baseline | Escalations |
| --- | --- | --- |
| F-01 List payouts | L2 | L3 for sensitive-data-access logging (16.3.2) |
| F-02 Get payout detail | L2 | L3 for field-level minimization (14.2.6) and sensitive-data-access logging (16.3.2) |
| F-03 Trigger on-demand payout | **L3** | High-value flow: 2.3.5 multi-user approval over a configured threshold; 4.1.5 per-message signing; 8.3.2/8.3.3 immediate revocation and originating-subject auth |
| F-04 Update payout schedule | L2 | L3 for 8.3.2 immediate revocation effect |
| F-05 Webhook on payout state change | **L3** | 4.1.5 per-message signing; 13.2.4/13.2.5 outbound allowlists for SSRF resistance; 11.5.1 CSPRNG nonces |

---

## 2. Feature-ASVS Coverage Matrix

Coverage statuses: **Covered** (PRD already satisfies intent), **Partial** (intent partly covered; clarify acceptance criteria), **Missing** (must be added), **N/A** (justified).

| Feature | ASVS Section | Requirement | Level | Coverage | PRD Change Needed |
| --- | --- | --- | --- | --- | --- |
| F-01 | V2.2 Input Validation | 2.2.1, 2.2.2 | 1 | Missing | Validate `from`/`to` (ISO-8601, max window, no future dates, from <= to) at trusted layer |
| F-01 | V6.1 Auth Documentation | 6.1.1 | 1 | Missing | Document API-key auth strength, rate limits, anti-automation |
| F-01 | V8.2 Authz | 8.2.1, 8.2.2 | 1 | Partial | Make object-scope explicit: API key resolves to merchant_id; results must be filtered by that merchant_id only |
| F-01 | V8.4 Multi-tenant | 8.4.1 | 2 | Missing | Cross-tenant isolation requirement |
| F-01 | V11.5 Random Values | 11.5.1 | 2 | Missing | Pagination cursors generated with CSPRNG (>=128 bits) |
| F-01 | V12.2 HTTPS | 12.2.1, 12.2.2 | 1 | Partial | Make TLS-only and publicly trusted cert explicit |
| F-01 | V14.2 Data Protection | 14.2.1, 14.2.6 | 1/3 | Missing | No sensitive query strings; minimize bank-account info to fingerprint only |
| F-01 | V16.2 General Logging | 16.2.1, 16.2.5 | 2 | Missing | Structured access log per request; redact PAN-equivalents and full account numbers |
| F-01 | V16.3 Security Events | 16.3.2 (L3) | 3 | Missing | Log read access to payout history (without logging the data itself) |
| F-02 | V2.2 Input Validation | 2.2.1 | 1 | Missing | Validate `payout_id` format/length; reject malformed IDs |
| F-02 | V8.2 Authz | 8.2.2, 8.2.3 | 1/2 | Missing | BOLA control: payout_id must belong to the calling merchant; field-level minimization |
| F-02 | V14.2 Data Protection | 14.2.4, 14.2.6 | 2/3 | Missing | Mask bank info; only return last-4 + bank_name; full data only on explicit fingerprint endpoint |
| F-02 | V16.3 Security Events | 16.3.2 (L3) | 3 | Missing | Log every detail-view access (who, when, payout_id) |
| F-03 | V2.2 Input Validation | 2.2.1, 2.2.3 | 1/2 | Partial | "Verify available balance" present; missing schema validation, currency allowlist, amount range, idempotency-key validation |
| F-03 | V2.3 Business Logic | 2.3.1, 2.3.2, 2.3.3, 2.3.4 | 1/2 | Partial | Add explicit business limits (per-day/per-merchant max), DB-transactional rollback, locking against double-spend |
| F-03 | V2.3 Business Logic | 2.3.5 | 3 | Missing | Multi-user / multi-factor approval over configurable threshold |
| F-03 | V4.1 Web Service | 4.1.5 | 3 | Missing | Per-message digital signature on POST body (or signed-request envelope) for highly sensitive transactions |
| F-03 | V6.1/V6.7 | 6.1.1 | 1 | Missing | Strong-auth path required for on-demand: at minimum API key + signed request; step-up MFA for amounts above threshold |
| F-03 | V8.2 Authz | 8.2.1, 8.2.2 | 1 | Missing | Caller must own both source merchant balance and destination_bank_account_id; explicit BOLA on bank account |
| F-03 | V8.3 Authz | 8.3.2 | 3 | Missing | Permission/key revocation must apply within seconds; cached entitlements expire <= 60s |
| F-03 | V11.5 Random Values | 11.5.1 | 2 | Missing | Idempotency keys/payout IDs use CSPRNG with >=128 bits entropy |
| F-03 | V13.3 Secret Management | 13.3.1, 13.3.3 | 2/3 | Missing | API-signing keys and merchant secrets stored in HSM-backed vault; never in source/build artifacts |
| F-03 | V14.2 Data Protection | 14.2.6 | 3 | Missing | Response must mask destination bank info (last-4 only) |
| F-03 | V16.3 Security Events | 16.3.1, 16.3.2, 16.3.3 | 2/3 | Missing | Log auth, authorization decision, business-limit hits, signature verification result, idempotency replays |
| F-04 | V2.2 Input Validation | 2.2.1, 2.2.3 | 1/2 | Missing | Allowlist cadence values (`weekly|biweekly|daily`), validate day_of_week against cadence (e.g., daily ignores it) |
| F-04 | V8.2/V8.3 Authz | 8.2.1, 8.3.2 | 1/3 | Missing | Only authorized merchant principals (not delegated read-only keys) may change schedule; permission changes apply immediately |
| F-04 | V11.5 / V16.3 | 16.3.3 | 2 | Missing | Log every schedule change with before/after values for audit |
| F-05 | V2.2 Input Validation | 2.2.1 | 1 | Missing | Validate merchant-supplied webhook URL: HTTPS-only, public DNS, no internal/private/loopback ranges, no userinfo |
| F-05 | V4.1 Web Service | 4.1.5 | 3 | Partial | "verify signature" stated, but algorithm, timestamp, replay window, and key rotation not specified |
| F-05 | V11.2 / V11.4 Crypto | 11.2.1, 11.4.1 | 2 | Missing | Use vetted HMAC-SHA-256 (or asymmetric Ed25519) over canonical body + timestamp; no MD5/SHA-1 |
| F-05 | V11.5 Random Values | 11.5.1 | 2 | Missing | Per-event nonce / event_id from CSPRNG, included in signature |
| F-05 | V13.2 Backend Comm | 13.2.4, 13.2.5 | 2 | Missing | Outbound webhook target enforced through SSRF-resistant egress allowlist |
| F-05 | V13.3 Secret Management | 13.3.1, 13.3.4 | 2/3 | Missing | Merchant signing secrets stored in vault, supports rotation with overlap window |
| F-05 | V16.3 / V16.5 | 16.3.4, 16.5.2 | 2 | Missing | Log delivery failures; circuit-break against unhealthy endpoints; bounded retry with exponential backoff |
| All  | V12.1 / V12.2 | 12.1.1, 12.1.2, 12.2.1, 12.2.2 | 1/2 | Missing | TLS 1.2+ only, recommended ciphers, publicly trusted certs, no plaintext fallback |
| All  | V14.1 Data Classification | 14.1.1, 14.1.2 | 2 | Missing | Classify bank account number, account_id, full payout amount + merchant identity as Sensitive; document handling |
| All  | V16.1 / V16.4 | 16.1.1, 16.4.2, 16.4.3 | 2 | Missing | Log inventory; logs append-only, shipped to isolated log store; logs free of PAN-equivalents and full bank numbers |
| All  | V13.1 / V13.4 | 13.4.2, 13.4.5, 13.4.6 | 2/3 | Missing | Disable debug, hide internal docs/monitoring endpoints, suppress version banners |

**Gap summary:** 0 features are fully covered by the original PRD. F-01/F-02 are partially covered for transport but missing object-level authorization, sensitive-data-access logging, and field minimization. F-03 has the largest gap surface (high-value money movement). F-05 is partially covered (signature mentioned) but underspecified for replay, SSRF, and key rotation.

---

## 3. Enhanced Feature Specifications

### Feature F-01: List payouts

**Endpoint**: `GET /v2/payouts?from=YYYY-MM-DD&to=YYYY-MM-DD&cursor=...&limit=...`

**Actor**: Authenticated merchant (API key bound to a single `merchant_id`).

**Data touched**: Payout records (ID, amount, currency, scheduled date, status, **fingerprint** of destination bank account — never full account number or routing number).

**Trust boundaries crossed**: Public Internet -> API gateway -> Payouts service -> Payouts datastore.

**ASVS Mapping**: V2.2.1, V2.2.2, V6.1.1, V8.2.1, V8.2.2, V8.4.1, V11.5.1, V12.2.1, V12.2.2, V13.4.2, V14.2.1, V14.2.6, V16.2.1, V16.2.5, V16.3.2, V16.4.2.

**Updated Requirements**:

1. The endpoint MUST require a valid API key resolving to exactly one `merchant_id`. Results MUST be filtered server-side by that `merchant_id`; the client cannot supply or override `merchant_id`. (8.2.1, 8.2.2)
2. Cross-tenant isolation MUST be enforced at the data layer (parameterized queries scoped by `merchant_id`); a unit + integration test MUST assert that calls with merchant A's key cannot retrieve payouts owned by merchant B. (8.4.1)
3. Inputs MUST be schema-validated at the trusted service layer: `from`/`to` are ISO-8601 dates, `from <= to`, window <= 366 days, neither is in the future. Reject malformed input with HTTP 400 and a generic error code (no stack traces). (2.2.1, 2.2.2, 16.5.1)
4. Pagination cursors MUST be opaque, server-signed, and generated from a CSPRNG with >= 128 bits of entropy; cursors MUST NOT be tamperable to read another merchant's data. (11.5.1)
5. Responses MUST NOT include bank-account numbers, routing numbers, or any data classified as Sensitive beyond the agreed tokenized fingerprint and last-4. (14.2.6)
6. The API MUST be served over TLS 1.2+ with publicly trusted certificates; HTTP MUST NOT redirect to HTTPS for this API endpoint (clients must connect using HTTPS directly). (12.1.1, 12.2.1, 12.2.2, 4.1.2)
7. Rate-limiting and anti-automation policy MUST be documented and enforced (e.g., per-key per-minute quota; lockout on signature/key failures with bounded backoff). (6.1.1)
8. Each request MUST emit a structured access-log entry (UTC timestamp, request_id, merchant_id, key_id, IP, user agent, path, response code, byte count). Sensitive payload bodies MUST NOT appear in logs. (16.2.1, 16.2.5)
9. Sensitive-data-access events (a successful list response containing one or more payouts) MUST be logged at the audit channel WITHOUT logging the records themselves. (16.3.2 L3)

**Acceptance Criteria (testable)**:
- A payout owned by merchant B cannot be returned to merchant A under any combination of `cursor`, `from`, `to` (red-team test).
- Malformed `from`/`to` returns 400 with generic body; no stack trace; access log records the rejection.
- p99 latency under 800ms (carry-over).
- All responses set `Cache-Control: no-store`. (14.3.2)
- Logs contain no full bank-account numbers (lint rule + sample audit).

**Securability Notes**: This endpoint's primary risk is broken object-level authorization (BOLA) — every other concern is downstream of "wrong merchant_id". Treat the API key -> merchant_id resolution as the trust boundary and never accept a `merchant_id` from the caller. Confidentiality demands minimum-necessary fields in responses (fingerprint, not PAN/account); Accountability demands a sensitive-data-access audit trail that is itself a high-value asset. Analyzability and Testability are served by parameterizing the merchant scope at a single chokepoint (one query builder, one filter helper) so future maintainers cannot accidentally bypass it.

---

### Feature F-02: Get payout detail

**Endpoint**: `GET /v2/payouts/{payout_id}`

**Actor**: Authenticated merchant.

**Data touched**: Single payout record + line-item breakdown (gross sales, fees, refunds, adjustments, net amount, source order IDs). Source order IDs may transitively expose customer-side data and MUST be access-controlled.

**Trust boundaries crossed**: Same as F-01.

**ASVS Mapping**: V2.2.1, V8.2.2, V8.2.3, V11.5.1, V12.2.1, V14.2.4, V14.2.6, V16.2.1, V16.3.2.

**Updated Requirements**:

1. `payout_id` MUST be a server-generated opaque ID with >= 128 bits of entropy from a CSPRNG; it MUST NOT be a sequential integer. (11.5.1) Format/length MUST be validated before any DB lookup. (2.2.1)
2. Authorization MUST verify that `payout_id` belongs to the calling merchant before returning any field. A miss MUST return `404` (not `403`) to avoid disclosing existence. (8.2.2)
3. Field-level minimization (BOPLA): only fields the merchant role is entitled to read are returned. Internal-only fields (e.g., processor reference numbers, internal risk scores, merchant cost basis, FX margin) MUST NOT appear in the response. (8.2.3, 14.2.6)
4. Bank account information MUST be masked to last-4 + bank name + fingerprint. The full number MUST NEVER be returned by this endpoint. (14.2.6)
5. Source-order references MUST themselves be authorized: a merchant may only see their own orders.
6. Each successful detail view MUST emit an audit log entry: timestamp, merchant_id, key_id, payout_id viewed, IP, request_id. The data itself MUST NOT be logged. (16.3.2 L3, 16.2.5)
7. `Cache-Control: no-store` on responses. (14.3.2)

**Acceptance Criteria (testable)**:
- Probing for a known-good `payout_id` belonging to another merchant returns 404 with a body indistinguishable from a true not-found.
- Schema test asserts the response contains no internal-only fields and bank info is truncated to last-4.
- Access to the detail endpoint generates exactly one audit-log line per request (no double-logging, no missing events under load).

**Securability Notes**: Authenticity (the caller is who they claim to be) plus Confidentiality (don't leak fields the caller isn't entitled to) drive the design here; the same BOLA chokepoint as F-01 applies, plus a BOPLA control on the response shape. Choose an opaque ID format from day one — once merchants integrate, changing ID format is expensive (Modifiability). Accountability (who looked at what) is mandatory for SOC 2 and PCI; the audit channel MUST be tamper-evident and separated from app logs (16.4.2/16.4.3).

---

### Feature F-03: Trigger on-demand payout

**Endpoint**: `POST /v2/payouts` with body `{amount, currency, destination_bank_account_id, idempotency_key}`

**Actor**: Authenticated merchant principal authorized for payout initiation. Read-only API keys MUST NOT be allowed to call this endpoint.

**Data touched**: Merchant balance, bank-account record, payout record, ledger.

**Trust boundaries crossed**: Public Internet -> API gateway -> Payouts service -> Ledger -> Banking partner. This is the hardest trust boundary in the API surface.

**ASVS Mapping**: V2.2.1, V2.2.3, V2.3.1, V2.3.2, V2.3.3, V2.3.4, V2.3.5, V4.1.5, V6.1.1, V8.2.1, V8.2.2, V8.3.1, V8.3.2, V8.3.3, V11.2.1, V11.5.1, V13.3.1, V13.3.3, V13.3.4, V14.2.6, V16.3.1, V16.3.2, V16.3.3, V16.5.1, V16.5.2, V16.5.3.

**Updated Requirements**:

1. **Strong authentication & request integrity.** Requests MUST carry both an API key and a per-message digital signature (HMAC-SHA-256 with merchant secret over canonical headers + body + timestamp, OR asymmetric signing with merchant-registered public key). The server MUST reject requests where the signature is invalid, the timestamp is outside a 5-minute window, or the request is replayed (nonce/idempotency_key seen). (4.1.5, 9.1.1, 11.2.1, 11.4.1)
2. **Idempotency.** `idempotency_key` MUST be required, validated as opaque string of bounded length, and de-duplicated for at least 24 hours. A replay of an identical request returns the original payout's response; a replay of a key with different body returns 409. (2.3.1)
3. **Schema validation.** `amount` is a positive integer in minor units; `currency` is from a documented allowlist (e.g., USD, EUR); `destination_bank_account_id` matches expected format. Validate at trusted layer; reject extra fields (no mass-assignment). (2.2.1, 2.2.3)
4. **Authorization (BOLA on two objects).** Server MUST verify (a) the calling merchant owns the available balance being drawn from, and (b) the calling merchant owns `destination_bank_account_id` AND that account is in `verified` state (per the bank-verification PRD). (8.2.1, 8.2.2)
5. **Originating-subject authorization.** Downstream calls (ledger, banking partner) MUST carry the originating merchant's identity (or a server-issued, audience-restricted token derived from it), not a god-mode service token. (8.3.3)
6. **Immediate revocation.** When a merchant API key or role is revoked, in-flight authorization caches MUST expire within 60 seconds. (8.3.2)
7. **Business-logic limits.** Documented per-merchant daily, weekly, and per-transaction caps MUST be enforced server-side. Hits MUST be logged and surfaced as a distinct error code, not a generic 500. (2.1.3, 2.3.2)
8. **Multi-user/MFA approval for high-value flows.** Payouts above a configurable threshold (default proposed: $50,000 USD or per-merchant override) MUST require a second approval channel: either (a) approver-merchant-user separate from initiator, or (b) step-up MFA challenge tied to the merchant's principal. (2.3.5)
9. **Transactional integrity.** Balance debit, payout-record insert, and ledger entry MUST commit atomically. If any step fails, the entire operation MUST roll back and emit a security-event log; partial state MUST NOT be observable via F-01 or F-02. (2.3.3)
10. **Concurrency / double-spend protection.** Pessimistic or optimistic locking on the merchant's payout balance MUST prevent double-debit when two requests race. (2.3.4)
11. **Secrets management.** API-signing secrets and any HMAC keys MUST be stored in an HSM-backed secrets vault; never in source, env files committed to repo, or unprotected build artifacts. Rotation MUST be supported with overlap window. (13.3.1, 13.3.3, 13.3.4)
12. **Response minimization.** The response MUST NOT echo the full destination bank-account number; return last-4 + fingerprint + payout_id + status. (14.2.6)
13. **Logging.** Every attempt (success and failure) MUST log: timestamp, merchant_id, key_id, idempotency_key, amount, currency, masked destination, decision (allow/deny/limit-hit/threshold-step-up), signature-verification result, and outcome. The amount may be logged; the destination MUST be masked. (16.3.1, 16.3.2, 16.3.3, 16.2.5)
14. **Failure handling.** On downstream banking-partner outage, the API MUST queue the payout in `pending` state and return a clear status; it MUST NOT silently drop, double-submit, or fail-open. Generic error responses with no stack-trace leakage. (16.5.1, 16.5.2, 16.5.3)
15. **CSPRNG.** All payout IDs and server-issued tokens use CSPRNG with >= 128 bits entropy. (11.5.1)

**Acceptance Criteria (testable)**:
- Replaying an identical signed request returns the same payout_id without creating a new payout (idempotency test).
- A request signed with a stale timestamp (> 5 min) is rejected with a security-event log line.
- Two concurrent requests against the same balance result in exactly one debit (race test under load).
- A payout to a `destination_bank_account_id` owned by a different merchant is rejected with 403/404 and audited.
- A revoked key cannot initiate a payout 60 seconds after revocation.
- Amount above threshold without step-up returns `402` (or documented code) and logs the deferred approval requirement.
- Balance, payout, and ledger rows commit atomically under simulated downstream failure.

**Securability Notes**: F-03 is the highest-value flow in the entire system; treat it as the canonical "hard shell" trust boundary in FIASSE terms (S2.6 transparency + S3.2.3 reliability). Three SSEM attributes dominate: **Integrity** (atomic balance/payout/ledger updates and locking; this is what prevents double-spend and partial-state leakage), **Authenticity** (per-message signatures plus CSPRNG-strong idempotency keys; this is what makes the request provably from this merchant and not a replay), and **Accountability** (every decision, including threshold-step-up and limit-hit, is logged with enough metadata for SOC 2 and PCI investigations). Confidentiality demands response and log minimization on bank-account data. Resilience demands the system fail closed on banking-partner outages — never fail open on "verify available balance." Modifiability matters because thresholds and caps will change — express them as configuration, not code, and isolate signature verification and authorization checks behind narrow interfaces so they can be evolved without rewriting the payout flow.

---

### Feature F-04: Update payout schedule

**Endpoint**: `PUT /v2/payouts/schedule` with body `{cadence, day_of_week}`

**Actor**: Authenticated merchant principal with schedule-write permission.

**Data touched**: Merchant payout-schedule configuration.

**Trust boundaries crossed**: Same as F-01, plus a write to merchant configuration.

**ASVS Mapping**: V2.2.1, V2.2.3, V8.2.1, V8.3.1, V8.3.2, V11.5.1, V16.3.1, V16.3.3.

**Updated Requirements**:

1. Inputs MUST be validated against allowlists: `cadence in {weekly, biweekly, daily}`; `day_of_week in {monday..sunday}` and required only when cadence != `daily`. Reject extras. (2.2.1, 2.2.3)
2. The endpoint MUST require a key with explicit schedule-write permission; read-only keys MUST be rejected. (8.2.1)
3. Authorization MUST be enforced at the trusted service layer; client-side controls do not count. (8.3.1)
4. Permission changes (e.g., revoking schedule-write from a key) MUST take effect within seconds; if cached, the cache TTL MUST be <= 60s. (8.3.2)
5. Every schedule change MUST emit an audit-log entry capturing: timestamp, merchant_id, key_id, IP, request_id, before-value, after-value. (16.3.3)
6. The successful response MUST echo the new schedule and the effective-from date; no internal scheduling-engine identifiers MUST leak. (14.2.6)
7. A scheduled-change rate limit MUST exist (e.g., max N changes per merchant per day) to prevent griefing or oscillation. (2.3.2)

**Acceptance Criteria (testable)**:
- `PUT` with `cadence: "hourly"` returns 400 and a security-event log line.
- A read-only key receives 403; a schedule-write key succeeds; the audit log captures both.
- Changing schedule then immediately revoking the key blocks subsequent changes within 60s.
- Audit log line has both old and new schedule values.

**Securability Notes**: Lower stakes than F-03, but Accountability still matters: schedule changes affect when money moves and are a likely "first pivot" for an attacker who has phished a merchant API key. Modifiability favors keeping cadence options as enum + config rather than free-form. Testability is well-served by a small surface area — keep the validation, authorization, and audit-emission steps each as their own pure function so each can be tested without spinning up the whole service.

---

### Feature F-05: Webhook on payout state change

**Direction**: Outbound POST from us to merchant-configured URL.

**Actor**: Our system as caller; merchant as receiver.

**Data touched**: Payout state transition payload (payout_id, old_state, new_state, timestamp, event_id).

**Trust boundaries crossed**: Egress from our network to a merchant-supplied URL on the public Internet — this is an SSRF attack surface. The merchant-supplied URL is *untrusted input* until validated.

**ASVS Mapping**: V2.2.1, V4.1.5, V11.2.1, V11.4.1, V11.5.1, V12.2.1, V12.2.2, V13.2.4, V13.2.5, V13.3.1, V13.3.4, V16.3.4, V16.5.2.

**Updated Requirements**:

1. **URL validation.** Merchant-supplied webhook URLs MUST be validated at registration AND at send-time: scheme is `https`, host resolves to a public IP (no RFC1918, link-local, loopback, or metadata-service ranges), no `userinfo` component, hostname/port survive DNS rebinding (resolve-then-pin). (2.2.1, 13.2.4, 13.2.5)
2. **Egress allowlist / SSRF guard.** Outbound webhook traffic MUST go through a dedicated egress proxy that re-validates the destination IP against a deny-list of internal ranges. (13.2.4, 13.2.5)
3. **TLS only.** Outbound MUST use TLS 1.2+; certificate validation MUST be enabled; no insecure fallback. (12.2.1, 12.3.2)
4. **Per-message signing.** Each webhook MUST include a `Signature` header containing HMAC-SHA-256 (or asymmetric Ed25519) over a canonical string composed of timestamp + event_id + raw body. The signing algorithm and key id MUST be sent in the header so merchants can rotate. (4.1.5, 11.2.1, 11.4.1)
5. **Replay resistance.** A `Timestamp` header MUST be sent and included in the signed string; merchants are documented to reject events outside a 5-minute window. A `event_id` (>= 128 bits CSPRNG) MUST be unique per delivery and included in the signed string for receiver-side de-duplication. (11.5.1)
6. **Key management.** Per-merchant signing secrets MUST be stored in an HSM-backed secret store, never in code or merchant-visible configuration UI in cleartext after creation. Rotation MUST be supported with an overlap window so the merchant can verify with either key during a documented cutover. (13.3.1, 13.3.4)
7. **Delivery semantics.** At-least-once delivery within 60 seconds of state change (carry-over). Retries MUST use exponential backoff, bounded count, and bounded total duration; circuit-break on repeated failures to a given URL. (16.5.2, 13.1.3)
8. **Sensitive-data minimization.** The webhook body MUST contain payout_id, state transition, timestamp, and event_id — NOT bank-account numbers, full amounts beyond what merchants need (configurable), or PII. (14.2.6)
9. **Logging.** Every delivery attempt MUST log: timestamp, merchant_id, event_id, target host (not full URL with secrets), HTTP status, signature_key_id, attempt_number, latency. Failures MUST be logged at audit level. (16.3.4)
10. **Documented merchant-side verification.** The PRD MUST commit to publishing a "verify your webhook" guide that includes timestamp window, signing algorithm, canonical-string format, and replay-handling guidance, so merchants can implement F-05's promise correctly. (6.1.3, 14.1.2)

**Acceptance Criteria (testable)**:
- Registering a webhook URL of `http://10.0.0.5/x` is rejected with 400; same for `https://localhost`, `https://169.254.169.254` (cloud metadata), and `https://attacker@evil.tld`.
- An attacker controlling DNS for a registered host cannot, via DNS rebinding, cause the egress to hit an internal IP at send-time (verified with a DNS-rebinding test harness).
- Tampered webhook body fails signature verification on the merchant side using the documented algorithm (verified with reference client).
- A repeated event_id is recognized as a duplicate by the reference client.
- A webhook target returning 5xx for 5 consecutive deliveries triggers circuit-break and an internal alert.
- 99.95% of state changes deliver a webhook within 60s (carry-over SLO).

**Securability Notes**: Two distinct trust boundaries collide here: (a) the merchant-controlled URL is *untrusted*, exposing us to SSRF, and (b) we are issuing *trusted* signed messages, so the signing key and algorithm choice define merchant-side Authenticity. Confidentiality argues for minimal payload (don't put bank info in webhooks); Resilience argues for bounded retries and circuit-breaking (a slow merchant endpoint should never tip over our payout-delivery pipeline); Accountability argues for delivery-attempt logging that doesn't include the signing material. From a Modifiability perspective, the signing algorithm and key MUST be pluggable and rotatable from day one — a future SHA-256-to-Ed25519 migration without a rotation channel is a six-month project we can avoid by designing for crypto-agility now (S2.1, S2.2; ASVS 11.2.2).

---

## 4. Cross-Cutting Securability Requirements

These apply to the entire API surface and SHOULD be implemented once at the platform / gateway / SDK layer rather than per feature.

### CC-01: Transport security
- TLS 1.2+ only on all external endpoints; recommended cipher suites only; no plaintext fallback. Internal service-to-service hops use TLS as well (ASVS 12.1.1, 12.1.2, 12.2.1, 12.2.2, 12.3.1, 12.3.3).
- Public endpoints use publicly trusted certificates; internal certs come from a controlled internal CA with explicit trust pinning per consumer service (12.3.4).
- HTTP requests to the API surface are NOT auto-redirected to HTTPS for API (non-browser) endpoints — they are rejected, so misconfigured clients fail loudly rather than silently leaking the first request (4.1.2).

### CC-02: Authentication & authorization platform
- API keys are issued, stored hashed, scoped to a single `merchant_id`, scoped to a permission set (read, schedule-write, payout-initiate), and individually revocable.
- Authorization decisions are enforced at the trusted service layer, never at the gateway alone (8.3.1).
- For high-value flows (F-03), step-up MFA / second-factor MUST be available; the documentation MUST specify the strength of authentication required per endpoint (6.1.3).
- Permission changes MUST propagate within 60 seconds (8.3.2), with mitigations and alerting documented when caches make this impossible.

### CC-03: Input validation
- All HTTP inputs are schema-validated at the trusted service layer using positive validation (allowlists, regexes, enums, ranges) (2.2.1, 2.2.2).
- Mass-assignment is prevented by explicit DTOs / serializers; unknown fields are rejected, not silently ignored.
- Output encoding for any user-controlled string echoed in responses (1.2.x).
- Database access uses parameterized queries / ORM; no string concatenation (1.2.4).

### CC-04: Cryptographic agility
- A documented cryptographic inventory MUST list every place HMAC, signature, hash, or random generation occurs, with algorithm, key id, and storage location (11.1.1, 11.1.2).
- The system MUST be designed so signing algorithms, key sizes, and KDF parameters can be reconfigured without code changes (11.2.2).
- Only approved algorithms (AES-GCM for symmetric, ECDSA/Ed25519/RSA-3072+ for asymmetric, SHA-256+ for hashing); MD5 and SHA-1 are forbidden for security purposes (11.3.2, 11.4.1).
- All randomness from CSPRNG with >=128 bits entropy (11.5.1).

### CC-05: Secret management
- All secrets (API-signing keys, webhook HMAC secrets, banking-partner credentials, DB credentials) live in an HSM-backed vault with least-privilege access (13.3.1, 13.3.2, 13.3.3).
- Secrets are NEVER committed to source, baked into images, or logged. Pre-commit and CI scanning MUST enforce this (13.3.1).
- Secrets have documented rotation schedules (13.3.4).

### CC-06: Logging and audit
- A logging inventory MUST exist documenting: what is logged at each layer, where it is stored, who can read it, retention period (16.1.1).
- Log entries MUST include UTC timestamp, request_id, merchant_id, key_id, action, decision (16.2.1, 16.2.2).
- Sensitive data MUST be redacted/masked according to the data-classification doc; full bank account numbers and PAN-equivalents MUST NEVER appear in logs (16.2.5).
- Logs MUST be append-only, shipped to an isolated, access-controlled log store, and protected against tampering (16.4.2, 16.4.3).
- Log entries MUST be encoded to prevent log injection (16.4.1).
- Audit-grade events: authentication, authorization decisions (allow and deny on sensitive endpoints — F-02/F-03 deny logging is L3), business-limit hits, signature-verification failures, security-control failures (16.3.1, 16.3.2 L3, 16.3.3, 16.3.4).

### CC-07: Error handling
- All endpoints return generic error messages on unexpected/security-sensitive errors; no stack traces, no internal hostnames, no SQL fragments (16.5.1).
- A last-resort handler MUST log unhandled exceptions before returning 500 (16.5.4).
- The system MUST fail closed on validation, signature, authorization, or downstream-dependency errors. No fail-open paths in the payout pipeline (16.5.3).
- Circuit breakers and bounded retries protect against downstream resource exhaustion (16.5.2, 13.1.3).

### CC-08: Data classification & protection
- A data-classification document MUST exist enumerating, at minimum: bank-account number (Highly Sensitive — never returned, never logged), bank-account fingerprint + last-4 (Sensitive — masked, audit-logged on access), payout amount + merchant_id (Sensitive — minimum-necessary in responses), idempotency keys (Internal — not loggable beyond hash), API keys (Highly Sensitive — stored hashed, never logged) (14.1.1, 14.1.2).
- Per-classification rules govern encryption, retention, logging, and access (14.1.2, 14.2.4).

### CC-09: Configuration hardening
- Production has debug/dev modes disabled (13.4.2).
- Internal docs, monitoring endpoints, and admin interfaces are not publicly reachable (13.4.5, 8.4.2).
- Server version banners are suppressed (13.4.6).
- TRACE method is disabled (13.4.4).

### CC-10: Multi-tenant isolation
- Every data-access path MUST be scoped by `merchant_id` enforced at the data layer, not just at the application layer (8.4.1).
- Automated test suite MUST include cross-tenant probe tests for every endpoint (a "merchant-A-key cannot see merchant-B-data" assertion).

### CC-11: Securability quality gates (FIASSE/SSEM)
- **Analyzability**: SSEM scoring (target >=7/9 attributes >=7) is a required artifact at design review; codebase metrics (cyclomatic complexity, duplication, unit size) tracked and trended.
- **Modifiability**: Authorization, signature-verification, and rate-limiting are isolated as small modules with narrow interfaces; pluggable algorithms by config.
- **Testability**: Each trust-boundary check (auth, authz, validation, signature) is a pure function with unit tests; integration tests cover the cross-tenant, race, and replay scenarios listed per feature.
- **Resilience**: Each downstream dependency (datastore, banking partner, merchant webhook target) has a documented failure mode, timeout, retry policy, and circuit breaker (13.1.3).

---

## 5. Open Gaps and Assumptions

### Open gaps the team MUST resolve before implementation

1. **High-value approval threshold (F-03).** The PRD assumes a configurable threshold for multi-user / step-up approval (proposed default $50,000). Product + Risk MUST agree on the threshold, the approval channel (second user vs. step-up MFA on the same user), and the carve-out for very large merchants whose normal payouts exceed it.
2. **Idempotency window (F-03).** Proposed 24h; if Risk wants longer (e.g., 7 days for chargeback alignment), the storage cost and replay semantics need confirmation.
3. **Webhook retry budget (F-05).** Need a precise retry policy (max attempts, max wall-clock duration, backoff curve, dead-letter destination). Current SLO is "deliver within 60s"; a 60s SLO bounds the retry budget.
4. **Signature algorithm choice (F-03 inbound, F-05 outbound).** HMAC-SHA-256 is the default proposal; if the team wants asymmetric (Ed25519) for stronger non-repudiation in webhooks, the merchant-onboarding flow must include public-key registration.
5. **Logging retention period (CC-06).** PCI requires 1 year minimum (90 days online, 1 year accessible); SOC 2 may extend this. Confirm with Compliance and document in the logging inventory.
6. **Authorization cache TTL (CC-02).** Proposed 60s; some teams prefer 5s for revocation responsiveness, at higher load on the authz service. Operations input needed.
7. **Out-of-scope dependencies.** Bank account verification (separate PRD) and merchant onboarding (separate flow) define the integrity of `destination_bank_account_id` and `merchant_id` ownership — F-02/F-03 *assume* those PRDs enforce verification and ownership integrity. If they do not, F-03 has an unaddressed authorization gap.

### Assumptions

- The PCI-tokenization vendor for card data is out of scope for this PRD; we are not handling raw PAN in any of these endpoints. Bank account numbers (ACH-side) ARE in scope and treated as Highly Sensitive in CC-08.
- Merchants integrate via API key + signed request; we do not currently support OAuth2 client credentials. If product wants OAuth2 in v2, it changes V9 (Self-contained Tokens) coverage materially.
- Logs ship to an isolated SIEM-friendly store; we are not building alerting/correlation in this PRD (out of scope per ASVS 16.3 note).
- Webhook signing keys are merchant-specific; we are not running a shared secret across merchants.

### Ratified non-functional requirements (from original PRD, retained)

- p99 latency under 800ms for list/detail endpoints (F-01, F-02). All securability controls MUST fit within this envelope.
- 99.95% availability for the API surface. Resilience requirements (CC-07, F-05 retry policy) support this.
- Webhook delivery within 60 seconds of state change.

---

*Generated by the FIASSE/SSEM PRD Securability Enhancement skill. ASVS references are to ASVS 5.0; FIASSE references are to the FIASSE RFC sections noted in the plugin's `data/fiasse/` corpus.*
