# Enhanced PRD: Internal Performance Review Browser

> Source: `hr-tool-prd.md` (draft)
> Enhancement framework: OWASP ASVS 5.0 + FIASSE / SSEM
> Scope of enhancement: ASVS level decision, feature-level coverage matrix, tightened requirements and acceptance criteria, cross-cutting controls, open gaps.

## Context (preserved from source)

Internal-only tool for HR staff to view and comment on employee performance reviews. Hosted on the corporate intranet behind SSO. Used by ~80 HR staff across 4 regions. Performance review data includes manager comments, ratings, compensation notes, and free-text peer feedback.

---

## ASVS Level Decision

**Chosen Level**: 2

**Rationale**: Although this is an internal-only tool behind SSO with a small population (~80 staff), the data class is unambiguously sensitive personnel data: ratings, manager comments, compensation notes, and free-text peer feedback. A breach or misuse would cause material impact (employee privacy harm, legal/HR exposure, potential discrimination claims, regulatory exposure under GDPR/state privacy laws given multi-region use). Level 1 is insufficient because it does not require field-level authorization, audit logging of authorization decisions, sensitive-data classification, or rate/limit controls — all of which directly govern HR-data risk. Level 3 is not warranted because the population is bounded, the system is non-public, and there is no payment, identity-issuance, or safety-critical surface; Level 3's adaptive/contextual auth and constant-time crypto controls would be over-scoped. Most internal HR-data products land at Level 2.

**Feature-Level Escalations**:
- **F-03 (Region report CSV export)**: Treat as a *high-value bulk-extraction* surface. Apply the L3 controls from V14.2.6 (minimum-data exposure / masking) and V16.3.2 (log every authorization decision, not just failures), because a single CSV export removes data from the application's controlled surface and is the most likely abuse vector.
- **F-04 (Bulk reviewer reassignment)**: Treat as an *administrative high-value workflow*. Apply L3 V2.3.5 (multi-user approval for high-value flows) and V8.4.2 (administrative interface hardening) because a single click silently changes ownership of many sensitive records.

---

## Feature ↔ ASVS Coverage Matrix

| Feature | ASVS Section | Requirement ID | Level | Coverage | PRD Change Needed |
|---------|--------------|----------------|-------|----------|-------------------|
| F-01 | V8.1 | 8.1.1, 8.1.2 | 1, 2 | Missing | Document who can view which reviews and which fields are restricted (e.g., compensation note may be HR-Comp-only). |
| F-01 | V8.2 | 8.2.1, 8.2.2, 8.2.3 | 1, 1, 2 | Missing | Add server-side function-, object-, and field-level authorization on review access (no IDOR via `employeeId`). |
| F-01 | V8.3 | 8.3.1, 8.3.2 | 1, 3 | Missing | Enforce authorization at the trusted service layer; immediately reflect role/region changes (revocation latency bound). |
| F-01 | V8.4 | 8.4.1 | 2 | Missing | Cross-region scoping: an HR user in Region A cannot view Region B reviews unless explicitly granted. |
| F-01 | V7.1 | 7.1.1, 7.1.3 | 2 | Partial | SSO is mentioned but session lifetime, idle timeout, SSO-coordinated logout, and re-auth rules are undefined. |
| F-01 | V7.3 | 7.3.1, 7.3.2 | 2 | Missing | Define inactivity timeout and absolute session lifetime appropriate for sensitive HR data. |
| F-01 | V14.1 | 14.1.1, 14.1.2 | 2 | Missing | Classify review fields (rating, manager comment, compensation note, peer feedback) into protection levels with documented controls. |
| F-01 | V14.2 | 14.2.1, 14.2.4 | 1, 2 | Missing | Sensitive identifiers must not appear in URLs/query strings; enforce classification-level controls in transit and at rest. |
| F-01 | V14.3 | 14.3.1, 14.3.2 | 1, 2 | Missing | Set `Cache-Control: no-store` on review pages; clear authenticated data on logout. |
| F-01 | V12.1 | 12.1.1 | 1 | Partial | Intranet hosting implied but TLS posture not stated; require modern TLS for all transport including intra-corporate. |
| F-01 | V16.3 | 16.3.1, 16.3.2 | 2, 2/3 | Missing | Log all auth events and (escalated to L3 for this app) all authorization decisions including reads of sensitive review records. |
| F-01 | V16.5 | 16.5.1, 16.5.3 | 2 | Missing | Generic error messaging; fail-closed on authorization errors. |
| F-02 | V8.2 | 8.2.1, 8.2.3 | 1, 2 | Missing | Only HR staff with commentary permission can post; "private to HR" must be enforced server-side, not by UI. |
| F-02 | V2.2 | 2.2.1, 2.2.2 | 1, 1 | Missing | Validate commentary text (length cap, allowed characters/Unicode policy) at a trusted service layer. |
| F-02 | V13.1 / V13.2 | 13.1.1 / 13.4.x | 2 | N/A for output rendering — see V11.x output encoding below | Free-text commentary must be safely rendered (output encoding, not stripping). |
| F-02 | V14.2 | 14.2.4 | 2 | Missing | Treat HR commentary as the highest sensitivity tier (it editorializes about a person and is intended HR-only). |
| F-02 | V16.3 | 16.3.1, 16.3.3 | 2 | Missing | Log every commentary create/edit/delete with author, target employee, timestamp, and commentary ID (not the body). |
| F-02 | V2.3 | 2.3.3 | 2 | Missing | Commentary write must be transactional — partial writes (e.g., visible without author bound) must not persist. |
| F-03 | V8.2 | 8.2.1, 8.2.2 | 1 | Missing | Export entitlement is a *separate* permission from read; not all HR users should be able to bulk-export. |
| F-03 | V8.4 | 8.4.1 | 2 | Missing | Region scoping is enforced server-side on the export query, not client-selected. |
| F-03 | V2.3 | 2.3.2 | 2 | Missing | Per-user and global rate limits on export volume per cycle. |
| F-03 | V14.2 | 14.2.4, 14.2.6 | 2, 3 (escalated) | Missing | Minimum-necessary fields in export; compensation note included only if user has the comp entitlement; otherwise omitted or masked. |
| F-03 | V14.2 | 14.2.7 | 3 (escalated) | Missing | Define retention/destruction expectation for generated CSV artifacts (server-side temp files, download logs). |
| F-03 | V16.3 | 16.3.1, 16.3.2 | 2, escalated to L3 | Missing | Every export request, regardless of outcome, is logged with requester, region scope, row count, fields included, and download completion. |
| F-03 | V13.4 | 13.4.5 | 2 | Missing | Internal report endpoints not exposed to anonymous routes; never reachable without SSO. |
| F-04 | V8.2 | 8.2.1 | 1 | Missing | Bulk-reassign restricted to "HR admin" role explicitly, enforced server-side. |
| F-04 | V8.4 | 8.4.2 | 3 (escalated) | Missing | Administrative workflow guarded by step-up auth (SSO re-prompt or MFA challenge). |
| F-04 | V2.3 | 2.3.1, 2.3.3, 2.3.5 | 1, 2, 3 (escalated) | Missing | Reassignment is sequential, transactional (all-or-nothing), and requires multi-user (4-eyes) approval before commit. |
| F-04 | V2.2 | 2.2.1, 2.2.3 | 1, 2 | Missing | Validate that source manager exists, target manager is an active reviewer, source ≠ target, and both are within the admin's scope. |
| F-04 | V16.3 | 16.3.1, 16.3.2, 16.3.3 | 2 | Missing | Log the request, the approver, the resulting review-ID set affected, and the before/after manager values. |
| F-04 | FIASSE S6.4.1.2 (Derived Integrity) | — | — | Missing | The set of "pending reviews to reassign" must be derived server-side from the source manager ID; never accept a client-supplied list of review IDs as the operation target. |
| Cross-cutting | V13.1 | 13.1.1 | 2 | Missing | Document SSO/IdP integration, log pipeline, storage, and external dependencies. |
| Cross-cutting | V13.2 | 13.2.1, 13.2.2 | 2 | Missing | Service accounts to backing DB use least privilege and rotated credentials, not shared admin. |
| Cross-cutting | V14.1 | 14.1.1, 14.1.2 | 2 | Missing | Single data-classification table covering all review fields. |
| Cross-cutting | V16.1, V16.2, V16.4 | 16.1.1, 16.2.x, 16.4.x | 2 | Missing | Centralized, structured, tamper-resistant audit pipeline. |

> Coverage classification reminder: *Covered* = PRD already satisfies; *Partial* = mentioned but under-specified; *Missing* = absent and must be added; *N/A* = not applicable with rationale.

---

## Enhanced Feature Specifications

### Feature F-01: View Employee Performance Review

**Actor**: Authenticated HR staff (via corporate SSO), scoped to one or more regions and to one or more review-content roles (e.g., HR-General, HR-Comp).
**Data**: Employee identifier (PII), name (PII), manager comment (HR-confidential free text), rating (HR-confidential), compensation note (HR-Comp restricted), peer feedback (HR-confidential free text, may contain third-party identifiers).
**Trust Boundaries**: browser → application server (corporate intranet, still a trust boundary); application server → SSO/IdP; application server → review datastore.

**ASVS Mapping**: V7.1.1, V7.1.3, V7.3.1, V7.3.2, V8.1.1, V8.1.2, V8.2.1, V8.2.2, V8.2.3, V8.3.1, V8.3.2, V8.4.1, V12.1.1, V14.1.1, V14.1.2, V14.2.1, V14.2.4, V14.3.1, V14.3.2, V16.3.1, V16.3.2, V16.5.1, V16.5.3.

**Updated Requirements**:
- HR staff can search by employee name or employee ID and open a review history page (original, retained).
- All review access is mediated by a server-side authorization check that evaluates: (a) the caller's HR role, (b) the caller's region scope, and (c) any field-level entitlements (e.g., compensation note requires HR-Comp role) (V8.2.1, V8.2.2, V8.2.3, V8.4.1).
- Authorization is enforced at the trusted service layer behind the API; UI hiding is presentation only, not a control (V8.3.1).
- Role and region changes propagate to authorization decisions within a defined bound (target: <= 5 minutes for cache-driven enforcement; immediate for the next request when no cache is involved) (V8.3.2).
- Sensitive identifiers (employee ID) and free-text content must not appear in URLs, query strings, or referrer headers; use POST bodies, header fields, or opaque path tokens (V14.2.1).
- Response includes `Cache-Control: no-store` and `Pragma: no-cache`; `Clear-Site-Data` on logout (V14.3.1, V14.3.2).
- All transport (browser↔server, server↔IdP, server↔datastore) uses TLS 1.2+ with TLS 1.3 preferred (V12.1.1).
- SSO session inactivity timeout, absolute session lifetime, and SSO-coordinated logout/re-auth behavior are documented and enforced (V7.1.1, V7.1.3, V7.3.1, V7.3.2). Initial proposal: 30-minute idle, 8-hour absolute, hard re-auth daily.
- Every successful authentication, every authorization decision (allow/deny) on a review-record read, and every field-level redaction event is logged (V16.3.1, V16.3.2 — escalated to L3 for this feature because reads of HR data are themselves sensitive).
- Authorization or backend errors return a generic message and HTTP 403/500 as appropriate; the system fails closed (no review data is rendered if any access check fails) (V16.5.1, V16.5.3).
- A documented data-classification table covers each review field and its protection level (V14.1.1, V14.1.2).

**Acceptance Criteria**:
- Calling the review-fetch API with an `employeeId` outside the caller's region scope returns HTTP 403, no review body, and writes an `authz.deny` log entry with caller ID, target employee ID, region, and decision reason. (V8.2.2, V8.4.1, V16.3.2)
- A user without the HR-Comp entitlement requesting the same employee's review receives the review payload with the `compensationNote` field omitted from the response (not blanked, not the string "redacted" — absent) and a `field.redaction` log entry. (V8.2.3, V14.2.4, V16.3.2)
- Tampering the request to add a `compensationNote` field selector or `regionOverride` parameter does not change the server's decision; the parameter is ignored and a `request.surplus_param` log entry is written. (V8.3.1, FIASSE S6.4.1.1 Request Surface Minimization)
- After 30 minutes of inactivity, the next API call returns HTTP 401 with a re-auth prompt; after 8 hours of session age, re-auth is forced regardless of activity. (V7.3.1, V7.3.2)
- A response body containing review data carries `Cache-Control: no-store`; an automated header check in CI confirms this on every review endpoint. (V14.3.2)
- Logout triggers a request that clears review-related items from `localStorage`/`sessionStorage` and emits `Clear-Site-Data: "cache","storage"`. (V14.3.1)
- An employee ID never appears in `req.url` or query string; a route-level test asserts that hitting `/reviews?employeeId=...` returns 400. (V14.2.1)
- A pen-test-style probe replacing the URL path's employee identifier with another ID outside scope produces 403 + `authz.deny` log, not 404 (404 leaks existence). (V8.2.2)
- An IdP role change for a test user revokes access on the next request within 5 minutes, verified by an integration test that mutates the role mid-session. (V8.3.2)

**Securability Notes**: This is the central read surface for the system; its load-bearing securable qualities are **Confidentiality** (field-level access discipline so a generalist HR user cannot read compensation notes) and **Accountability** (every read of sensitive data must be reconstructable from the audit trail). Treat the corporate intranet as a trust boundary, not a perimeter — apply server-side authorization, input validation, and TLS as if the request originated from the public internet. Apply the **Request Surface Minimization Principle (FIASSE S6.4.1.1)**: pull only the explicit parameters you need from the request, ignore everything else; this neutralizes parameter-injection attempts and produces clean audit signal. **Modifiability** matters here: centralize authorization in a single policy module (one decision point, one log emitter) so role/region/field rules can evolve without touching every endpoint.

---

### Feature F-02: Add HR Commentary

**Actor**: Authenticated HR staff with the "HR Commentary" entitlement.
**Data**: Free-text commentary (HR-confidential, may include third-party PII), author identity, target employee identifier, target review identifier, timestamp.
**Trust Boundaries**: browser → application server; application server → review datastore (write); application server → audit log pipeline.

**ASVS Mapping**: V2.2.1, V2.2.2, V2.3.3, V8.2.1, V8.2.3, V8.3.1, V11.x output encoding via secure rendering (see Cross-Cutting), V14.1.2, V14.2.4, V16.3.1, V16.3.3, V16.4.1, V16.5.1.

**Updated Requirements**:
- HR staff with the commentary entitlement can attach a private commentary note to a specific review; entitlement is checked server-side on every write (V8.2.1, V8.3.1).
- "Private to HR" is a server-side authorization rule, not a UI hide: any read API used by employees or managers must structurally exclude commentary fields, and a separate read endpoint exists for HR commentary (V8.2.3).
- Commentary input is validated at the service layer: maximum length (proposed 4,000 characters), Unicode normalization (NFC), control-character rejection, and a documented allow-list policy for permitted characters (V2.2.1, V2.2.2).
- Commentary is stored with derived server-side fields: `authorUserId` (from session, never client-provided), `createdAt` (server clock, UTC), `commentaryId` (server-generated), `targetReviewId` (validated against the caller's authorization scope) (FIASSE S6.4.1.2 Derived Integrity).
- Commentary write is transactional — either the commentary, its index entry, and its audit log line all persist, or none do (V2.3.3).
- Commentary is rendered using output encoding appropriate to the rendering context (HTML-escaped on the page, JSON-serialized in API responses); raw text is never injected into a DOM. (See Cross-Cutting V13.x rendering rule.)
- Every commentary create/edit/delete is logged with `authorUserId`, `targetEmployeeId`, `targetReviewId`, `commentaryId`, `action`, `timestamp` — but **not** the body, which is high-sensitivity (V16.3.1, V16.3.3, V16.4.1).
- Errors during commentary write return a generic message; the partial write (if any) is rolled back; an `commentary.write_failed` log entry is recorded (V16.5.1, V2.3.3).

**Acceptance Criteria**:
- A user without the HR Commentary entitlement calling the create endpoint receives HTTP 403, no record is written, and an `authz.deny` log line is emitted. (V8.2.1)
- A request body that includes `authorUserId` or `createdAt` is processed *as if those fields were absent* — the server uses session and clock values, and a `request.surplus_param` log entry is written. (FIASSE S6.4.1.1, S6.4.1.2)
- An employee or manager calling any review-read endpoint never sees commentary in the response body, verified by a contract test. (V8.2.3)
- Commentary text exceeding 4,000 characters returns HTTP 400 with a validation error code (no length leak in the message); a `validation.fail` log entry is written. (V2.2.1)
- Commentary text containing a payload such as `<script>alert(1)</script>` is stored verbatim and rendered as inert text (HTML-escaped) in the HR view; an automated DOM test asserts no script execution. (V13.x output encoding)
- A simulated database failure mid-write leaves no commentary visible on subsequent reads and produces a `commentary.write_failed` log entry. (V2.3.3, V16.5.3)
- The audit log line for a commentary write contains author, target, action, and IDs; a grep for the body text in audit logs returns zero results. (V16.2.5, V16.3.3)

**Securability Notes**: Free-text fields are the most reliable carrier of injection content; treat the commentary field as untrusted input even though the author is an authenticated employee. The two load-bearing concerns are **Integrity** (server owns `authorUserId`, `createdAt`, `targetReviewId` — apply the **Derived Integrity Principle (FIASSE S6.4.1.2)**) and **Accountability** (the commentary is, in effect, a personnel record about a named individual, so the audit line for create/edit/delete is non-negotiable). The "private to HR" property is a *server-side authorization* property; building it as UI-only guarantees a future leak. Centralize input validation, encoding, and write-with-audit in one module (**Modifiability**, **Testability**) so a future change to the commentary schema doesn't reopen any of these gaps.

---

### Feature F-03: Export Region Report (CSV)

**Actor**: Authenticated HR staff with the "HR Reporting" entitlement, scoped to a region.
**Data**: Employee ID, name, rating, manager comment, compensation note. This is a *bulk* sensitive-data egress surface — the highest-risk feature in the product.
**Trust Boundaries**: browser → application server; application server → review datastore (bulk read); application server → file/storage layer for CSV materialization; application server → audit log pipeline.

**ASVS Mapping**: V8.2.1, V8.2.2, V8.4.1, V8.4.2 (escalated), V2.3.2, V14.1.2, V14.2.4, V14.2.6 (escalated), V14.2.7 (escalated), V13.4.5, V16.3.1, V16.3.2 (escalated), V16.4.x.

**Updated Requirements**:
- The export feature requires a separate "HR Reporting" entitlement, distinct from review-read (V8.2.1).
- The region scope of the export is *derived server-side* from the caller's identity. The endpoint takes no client-supplied region parameter; if multiple regions are within scope, the user selects from a server-rendered list of permitted regions, and the server re-validates the selection (FIASSE S6.4.1.2, V8.4.1).
- The compensation note column is included only if the caller has the HR-Comp entitlement; otherwise it is omitted from the CSV (column absent, not blank) (V8.2.3, V14.2.4, V14.2.6).
- Per-user and global rate limits apply: proposed default of 5 exports per user per 24 hours and a global cap of 50 exports per 24 hours, with 429 responses on excess (V2.3.2).
- Exports are materialized to a server-side temporary store with a documented retention TTL (proposed 24 hours), then deleted on a schedule or on successful download (V14.2.7 escalated).
- Every export request is logged with: requester, region scope, row count, columns included, request timestamp, completion timestamp, and outcome (success / denied / failed). The CSV body itself is **not** logged. (V16.3.1, V16.3.2 escalated, V16.2.5)
- Export endpoints are not reachable without SSO and are not advertised in any anonymous route inventory or client-side bundle metadata (V13.4.5).
- The export response carries `Cache-Control: no-store` and `Content-Disposition: attachment; filename="..."` with a sanitized filename; the filename does not contain employee identifiers or free-text fields (V14.2.1, V14.3.2).
- An export request whose region scope evaluates to zero rows still produces an audit log entry (signal: a probe attempting to enumerate scopes) (V16.3.3).

**Acceptance Criteria**:
- A user without HR Reporting calling the export endpoint receives HTTP 403, no file, and an `export.deny` log entry; verified by integration test. (V8.2.1)
- Tampering the region parameter (or adding a `region` parameter when none was offered) does not expand scope; the server uses only its own derived scope and emits `request.surplus_param`. (FIASSE S6.4.1.2, V8.4.1)
- A user without HR-Comp downloading their region's CSV finds no `compensationNote` column in the file header; a generalist user and an HR-Comp user run the same export and column counts differ. (V14.2.4, V14.2.6)
- The 6th export in a 24-hour rolling window per user returns HTTP 429 with a `Retry-After` header and a `ratelimit.export` log entry. (V2.3.2)
- 24 hours after generation, the temp CSV is no longer present in the storage path; an automated cleanup job logs each deletion. (V14.2.7)
- The audit log row for any export contains the row count and column list and *does not* contain any of the row data; a grep for any sample employee name in audit logs returns zero results. (V16.2.5, V16.3.2)
- An export endpoint accessed without a valid SSO session returns HTTP 401 and is not present in any anonymous route discovery. (V13.4.5)
- A simulated zero-row export produces a `export.empty` audit entry with the requested scope. (V16.3.3)

**Securability Notes**: This feature is the system's highest-impact egress and the most likely abuse vector — once a CSV leaves the application, none of the in-app controls apply. The load-bearing securable qualities are **Confidentiality** (minimum-data exposure: HR-Comp gating, no compensation column for users without entitlement), **Accountability** (every export, including denied and empty ones, must be reconstructable), and **Resilience** (rate limits prevent both accidental excess and credentialed-insider abuse). Apply the **Derived Integrity Principle (FIASSE S6.4.1.2)** rigorously: the region scope is server-owned state. Apply the **Request Surface Minimization Principle (FIASSE S6.4.1.1)**: ignore any client-supplied parameter that the server should own. Treat the materialized CSV file as data at rest under the highest classification — TTL, isolated storage, and download integrity check all flow from that. **Transparency**: surface a "your recent exports" view to the requesting user as a self-audit feedback loop.

---

### Feature F-04: Bulk Reassign Reviewer

**Actor**: HR Admin (a privileged role distinct from general HR staff). Approver: a second HR Admin.
**Data**: Set of pending review records (HR-confidential), source manager identity, target manager identity. Mass-mutation surface — touches many records in one operation.
**Trust Boundaries**: browser → application server; application server → review datastore (bulk write); application server → audit log pipeline.

**ASVS Mapping**: V2.2.1, V2.2.3, V2.3.1, V2.3.3, V2.3.5 (escalated), V8.2.1, V8.4.2 (escalated), V13.2.1, V16.3.1, V16.3.2, V16.3.3, V16.5.3.

**Updated Requirements**:
- The bulk-reassign capability is restricted to the HR Admin role, enforced server-side; UI gating is presentation only (V8.2.1).
- Initiating a bulk reassignment triggers a step-up authentication (SSO re-prompt or MFA challenge) regardless of current session age (V8.4.2 escalated).
- The operation is structured as a *proposal → approval → commit* workflow: the initiating admin proposes (source manager → target manager), a second admin reviews and approves, and only then does the reassignment commit. No single user can both initiate and approve. (V2.3.5 escalated, "four-eyes")
- The set of "pending reviews to reassign" is derived server-side at commit time from the source manager identifier; the client never supplies the list of review IDs to mutate (FIASSE S6.4.1.2).
- Inputs are validated server-side: source manager exists and is active, target manager exists and is active and is a permitted reviewer for the affected employees, source ≠ target, both are within the admin's region scope (V2.2.1, V2.2.3).
- The reassignment is transactional — either all affected reviews are updated and an audit batch line is written, or none are; a partial commit must not be observable (V2.3.3).
- The workflow processes steps in order; the commit endpoint rejects requests that did not pass through the approval step (V2.3.1).
- Every step (propose, approve, reject, commit, fail) is logged with actor, action, source manager, target manager, and the resulting affected review-ID set; the proposal carries an idempotency token to prevent double-commit (V16.3.1, V16.3.2, V16.3.3).
- On commit failure (any backend error), the operation rolls back, returns a generic error message, and writes a `bulk_reassign.failed` log entry; the system fails closed (V16.5.3, V2.3.3).
- Service-account credentials used by the application to perform the bulk write are short-lived and least-privileged (V13.2.1, V13.2.2).

**Acceptance Criteria**:
- A non-admin user calling any of the bulk-reassign endpoints (propose, approve, commit) receives HTTP 403 and an `authz.deny` log entry. (V8.2.1)
- Initiating a proposal triggers the IdP step-up flow; bypassing it (e.g., by hitting `commit` with only a base session) returns HTTP 401 and writes `stepup.required`. (V8.4.2)
- Submitting `commit` without a corresponding approved `proposalId` returns HTTP 409 (or 400) and writes `workflow.out_of_order`. (V2.3.1)
- The same admin attempting to approve their own proposal is rejected with HTTP 403 and `four_eyes.violation` log entry. (V2.3.5)
- A request body for `commit` that includes a `reviewIds` array is processed as if that field were absent; the server derives the list from `sourceManagerId` and emits `request.surplus_param`. (FIASSE S6.4.1.2)
- Validation: source = target, inactive manager, or out-of-scope manager all return HTTP 400 with a generic error code and a `validation.fail` log entry. (V2.2.1, V2.2.3)
- A simulated mid-commit datastore failure leaves zero affected reviews mutated; a follow-up read of any of them returns the original `assignedManager`; a `bulk_reassign.failed` entry is written. (V2.3.3, V16.5.3)
- The audit log batch entry for a successful commit contains actor (initiator), approver, source manager, target manager, count of reviews affected, and an enumerable list (or stable hash) of affected review IDs. (V16.3.2)
- Replaying the same idempotency token returns the original outcome and does not re-execute the mutation. (V2.3.3)

**Securability Notes**: This is the only mass-mutation surface in the product, so its load-bearing securable qualities are **Integrity** (the operation either fully succeeds or fully rolls back; the affected set is server-derived) and **Accountability** (a single click changes ownership of many sensitive records — the audit trail must allow full reconstruction, including who proposed and who approved). The escalation to the L3 controls V2.3.5 (multi-user approval) and V8.4.2 (administrative step-up) is justified by blast radius: a credentialed-insider abuse here moves all of a manager's reviews silently. Apply the **Derived Integrity Principle (FIASSE S6.4.1.2)** to the affected-review set; apply **Request Surface Minimization (FIASSE S6.4.1.1)** so that surplus client-supplied parameters are ignored, not merged. Build the workflow as a small state machine in one module (**Modifiability**, **Analyzability**) so the four-eyes invariant is enforced in one place and visible in one diagram.

---

## Cross-Cutting Securability Requirements

Controls that span all features. Each must be implemented once and reused, not re-implemented per feature.

- **Centralized authorization policy** — One policy module evaluates role, region, and field-level entitlements; called from every read/write endpoint. UI hiding is presentation only. (V8.2, V8.3, V8.4)
- **Centralized structured audit logging** — All security-relevant events (auth success/failure, authorization decisions, sensitive-record reads, exports, bulk operations, validation failures, errors) emit JSON log lines with: timestamp (UTC ISO-8601), actor user ID, action, resource, outcome, and request correlation ID. Bodies of sensitive data (commentary text, CSV rows) are not logged. (V16.1.1, V16.2.1, V16.2.2, V16.2.4, V16.2.5)
- **Tamper-resistant audit pipeline** — Logs are forwarded to a logically separate store; the application's runtime account cannot delete or rewrite log records. Log injection is mitigated by structured logging (no string concatenation of user input into log messages). (V16.4.1, V16.4.2, V16.4.3)
- **Output encoding standard** — All free-text fields (manager comments, peer feedback, HR commentary) are rendered using context-appropriate encoding (HTML-escape for DOM, JSON-encode for API). No `innerHTML` of untrusted content; CSP applied to the application origin. (V13.x output encoding)
- **Input validation at the trusted service layer** — Schema validation on every API endpoint; reject unknown fields rather than ignoring them silently *for security-relevant operations* (the **Request Surface Minimization** signal); cap request sizes; canonicalize Unicode input. (V2.2.1, V2.2.2, FIASSE S6.4.1.1)
- **TLS baseline** — TLS 1.2+ with TLS 1.3 preferred for all transport, including intra-corporate (browser↔server, server↔IdP, server↔datastore, server↔log pipeline). HTTP requests redirect to HTTPS only on user-facing endpoints. (V12.1.1, V4.1.2)
- **Session and SSO** — Documented inactivity timeout, absolute lifetime, and SSO-coordinated logout. Logout signals revoke the local session, issue `Clear-Site-Data`, and invalidate any server-side tokens. (V7.1.1, V7.1.3, V7.3.1, V7.3.2, V14.3.1)
- **Sensitive-data classification** — A single classification table covering each review field with: classification level, encryption at rest, encryption in transit, log policy, retention. Implementation references the classification, not the field name. (V14.1.1, V14.1.2, V14.2.4)
- **Anti-caching for sensitive responses** — All endpoints that return review or commentary data set `Cache-Control: no-store`. Verified by a CI header-check. (V14.3.2)
- **Service-account least privilege** — The application's database account has read/write only on the review tables it needs; no schema-modification or admin rights. Credentials are rotated and stored in a secrets manager, never in source. (V13.2.1, V13.2.2, V13.2.3)
- **Generic error handling** — A last-resort handler catches unhandled exceptions, returns a generic 5xx body with a correlation ID, and writes a full server-side log entry. No stack traces, queries, or paths are returned to clients. (V16.5.1, V16.5.3, V16.5.4)
- **Configuration hygiene** — Production has debug modes off, no directory listings, no `.git`/`.svn` exposure, no internal API documentation routes reachable, no detailed version banners. (V13.4.1, V13.4.2, V13.4.3, V13.4.5, V13.4.6)
- **Dependency and supply-chain policy** — Application dependencies are pinned, scanned in CI for known vulnerabilities, and updated on a documented cadence. (Aligned with V15/V17 themes; not feature-specific.)
- **Securable engineering ownership** — Authorization, audit logging, input validation, output encoding, and crypto are each owned by a single module with one set of tests, supporting **Modifiability** and **Testability** as the codebase evolves.

---

## Open Gaps and Assumptions

The following items could not be resolved from the input PRD. They should be closed by Product / Security / IT before implementation.

1. **Regulatory scope unspecified.** The PRD says "4 regions" but does not name them. If any region is in the EU, UK, or California, GDPR / UK GDPR / CCPA obligations attach to performance-review data (subject access, deletion, lawful basis, processor agreements). Confirm regions and re-evaluate retention, logging, and access disclosures.
2. **Role model not defined.** The PRD references "HR staff" and "HR admin" but does not enumerate roles. Required: a role table covering HR-General, HR-Comp, HR-Reporting, HR-Admin (and any others), the entitlements each grants, and which IdP groups map to them.
3. **Data-classification table absent.** The protection level for each review field (rating, manager comment, compensation note, peer feedback, HR commentary) must be agreed; controls flow from the classification.
4. **SSO/IdP details absent.** Which IdP, which protocol (SAML / OIDC), which session duration, how role/region attributes are claimed, how logout is propagated, whether step-up MFA is available for F-04. V7.1.3 cannot be fully satisfied without these.
5. **Audit log retention undefined.** The PRD does not state how long audit logs are kept. Recommend 1-year minimum given personnel data context; confirm against regulatory retention requirements.
6. **CSV export retention and download channel undefined.** Where is the temp CSV materialized? Does it leave the application domain? Is it sent over email or downloaded directly? Email-based delivery introduces a separate trust boundary not covered here.
7. **Peer-feedback authorship.** The PRD says reviews include "free-text peer feedback" but does not say whether peer authors are identified to HR or whether peers are anonymized. This affects re-identification risk in F-03 exports.
8. **Employee subject-access pathway out of scope.** F-04 et al. mention employees do not see commentary and there is no self-service product. If employees in some regions have a legal right to access or correct their review data, that pathway must exist *somewhere*; clarify whether this PRD is the system of record or only a viewer.
9. **Bulk-reassignment 4-eyes feasibility.** V2.3.5 requires multi-user approval. With only ~80 HR staff across 4 regions, an HR Admin in a small region may not have a peer to approve. Define fallback (e.g., approval by an Admin from another region or by a designated security/compliance role).
10. **Compensation-note presence not confirmed across regions.** Some regions may legally restrict storing compensation in HR-review records. Confirm before classifying that field uniformly.
11. **Threat model not documented.** A short threat model for the product (insider abuse, credentialed-insider exfiltration via export, compromised IdP, leaked CSV) would let the team prioritize the controls above. Recommended deliverable before implementation.
12. **Performance acceptance criterion ("under 2 seconds") interaction with rate limits.** The 2-second target does not specify error/timeout behavior. Confirm whether 429 / step-up flows are excluded from the latency SLA (they should be).
