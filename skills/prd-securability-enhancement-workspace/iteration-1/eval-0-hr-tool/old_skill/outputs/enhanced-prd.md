# PRD: Internal Performance Review Browser (Securability-Enhanced)

> Enhanced with FIASSE/SSEM implementation guidance and OWASP ASVS 5.0 requirement coverage.

## Context

Internal-only tool for HR staff to view and comment on employee performance reviews. Hosted on the corporate intranet behind SSO. Used by ~80 HR staff across 4 regions.

Performance review data includes manager comments, ratings, compensation notes, and free-text peer feedback. This is **sensitive personnel data** and likely subject to local employment-privacy regulations (e.g., GDPR for EU regions, US state privacy laws). Although the system is internal and SSO-fronted, the population of authorized viewers is broad enough — and the impact of leakage to a non-HR employee or external party severe enough — that "internal" must not be treated as a substitute for technical access control.

---

## 1. ASVS Level Decision

**Selected Baseline: ASVS Level 2** (with selective Level 3 controls on the bulk reassignment and CSV export flows).

### Rationale

- **Why Level 1 is insufficient:** Level 1 is suited to low-risk/prototype systems. This tool stores compensation notes, ratings, manager and peer feedback, and identifiable employee data — material disclosure of which causes employee-relations, legal, and HR-trust harm. Level 1 lacks the access-control granularity (field-level, data-level), logging coverage, and data-protection requirements needed here.
- **Why Level 2 is the right baseline:** Level 2 is the standard for production systems with authenticated users handling business-critical and personal data. It pulls in V8.2 data- and field-level authorization, V14.1/V14.2 sensitive data protection and minimization, V16.1–V16.4 structured logging and log protection, V2.1/V2.4 documented validation and anti-automation, and V8.1.2 field-level rules — all directly relevant.
- **Why selective Level 3:** Two flows materially escalate risk and warrant L3 treatment:
  - **F-03 Export region report** — bulk extraction of sensitive data; warrants L3 data-minimization (V14.2.6), authorization logging (V16.3.2), and bulk-extraction monitoring.
  - **F-04 Bulk reassign reviewer** — privileged administrative action affecting many records at once; warrants L3 administrative-interface controls (V8.4.2) and full authorization-decision logging (V16.3.2).
- **Internal/SSO context:** Behind SSO is a perimeter control, not an authorization model. ASVS Level 2 application-layer enforcement is still required because (a) any authenticated corporate user could attempt to reach the app directly, (b) HR staff have legitimate access only to a subset of employees in practice, and (c) audit obligations for HR data require application-tier accountability.

### Out-of-Scope ASVS Areas (with rationale)

- **V2.x password storage, V2.2 password recovery, V2.3 credential storage** — Authentication is delegated to the corporate SSO IdP; the application MUST NOT issue or store passwords.
- **V4.3 GraphQL** — Not used.
- **V11.6 public-key crypto, V11.7 in-use cryptography (L3)** — No bespoke PKI or confidential-computing requirement at this scope.

---

## 2. Feature-ASVS Coverage Matrix

| Feature | ASVS Section / Req       | Level | Coverage  | PRD Change Needed                                                                              |
| ------- | ------------------------ | :---: | --------- | ---------------------------------------------------------------------------------------------- |
| F-01    | V8.1.1, V8.1.2           |   2   | Missing   | Document who-sees-what rules; define field-level read permissions                              |
| F-01    | V8.2.1, V8.2.2, V8.2.3   |   2   | Missing   | Enforce function/data/field-level authz server-side (not just SSO group)                       |
| F-01    | V8.3.1                   |   1   | Partial   | Make explicit: authz at trusted backend tier, never client-side                                |
| F-01    | V12.1.1, V12.2.1         |  1/2  | Partial   | Mandate TLS 1.2+ in-transit, including intranet hops                                           |
| F-01    | V14.1.1, V14.1.2, V14.2.4|   2   | Missing   | Classify review fields; document protection requirements                                       |
| F-01    | V14.2.1                  |   1   | Missing   | No employee IDs/PII in URLs or query strings used for routing                                  |
| F-01    | V16.2.x, V16.3.2, V16.3.3|   2   | Missing   | Log every review view (who, when, employee_id) without logging the review content              |
| F-01    | V16.5.1                  |   2   | Missing   | Generic error messages on access failures; no stack traces                                     |
| F-02    | V8.2.1, V8.2.2, V8.2.3   |   2   | Missing   | Only HR-author role can write; field-level rule that note is invisible to employee/manager     |
| F-02    | V2.1.1, V12.x (input)    |  1/2  | Missing   | Define input validation for note text (length, encoding, allowed characters)                   |
| F-02    | V13.1.x output encoding  |   2   | Missing   | Output-encode notes when rendered to prevent stored XSS                                        |
| F-02    | V16.2.1, V16.3.3         |   2   | Missing   | Log note creation events with author, timestamp, target review id                              |
| F-02    | V14.2.4                  |   2   | Missing   | Note retention policy aligned to HR record-retention schedule                                  |
| F-03    | V8.2.1, V8.2.2           |   2   | Missing   | Restrict export to a specific HR-export role; deny by default                                  |
| F-03    | V8.4.1                   |   2   | Missing   | Cross-region scoping: HR staff can only export their region                                    |
| F-03    | V14.2.4, V14.2.6         |  2/3  | Missing   | Minimize fields in the CSV; mask compensation unless explicit purpose is selected              |
| F-03    | V2.4.1                   |   2   | Missing   | Rate-limit export operations; throttle bulk extraction                                         |
| F-03    | V16.3.2 (L3), V16.3.3    |  2/3  | Missing   | Log every export event with row count, region, requester, justification                        |
| F-03    | V11.3.2 (CSV at rest)    |   2   | Partial   | Encrypt CSVs at rest; short retention on any temp storage                                      |
| F-03    | V16.5.1, V16.5.3         |   2   | Missing   | Fail-closed on partial export errors; never deliver partial CSVs silently                      |
| F-04    | V8.2.1, V8.2.2, V8.4.2   |  2/3  | Missing   | Require dedicated HR-Admin role; step-up authentication for the action                         |
| F-04    | V2.1.3, V2.4.1           |   2   | Missing   | Document upper limit on records per bulk action; require confirmation; rate-limit              |
| F-04    | V16.3.2 (L3), V16.3.3    |  2/3  | Missing   | Log full authorization decision and every reassigned review id; immutable audit               |
| F-04    | V16.4.2, V16.4.3         |   2   | Missing   | Audit trail of bulk reassignments must be append-only and forwarded to central log store       |
| F-04    | V11.5.1                  |   2   | Missing   | Bulk action requires a CSPRNG-generated correlation id for traceability/undo                   |
| F-04    | V16.5.3                  |   2   | Missing   | Fail closed on partial reassignment; provide a single-step undo                                |
| ALL     | V7.1.3, V7.2.x           |   2   | Partial   | Document SSO session lifetime, idle timeout, single-logout behavior                            |
| ALL     | V13.1.1                  |   2   | Missing   | Document all external service dependencies (IdP, log store, file storage)                      |
| ALL     | V14.1.1, V14.1.2         |   2   | Missing   | Single data-classification table for the product                                               |

Coverage status legend: **Covered / Partial / Missing / Not Applicable**.

---

## 3. Enhanced Feature Specifications

### Feature F-01: View employee performance review

**Description.** HR staff can search for an employee by name or employee ID and open their performance review history. The page shows all past reviews in reverse chronological order with reviewer, date, rating, manager comment, and any peer feedback.

**ASVS Mapping:** V8.1.1, V8.1.2, V8.2.1, V8.2.2, V8.2.3, V8.3.1, V12.1.1, V12.2.1, V14.1.1, V14.1.2, V14.2.1, V14.2.4, V16.2.1, V16.2.2, V16.3.2, V16.3.3, V16.5.1.

**Updated Requirements:**

- **R-01.1 Access scope:** Search and view are gated by an explicit `hr.review.read` permission granted only to HR staff; the application MUST NOT rely on SSO group membership alone to authorize access. Authorization is enforced at the backend service tier.
- **R-01.2 Data scoping:** HR staff see reviews only for employees in regions for which they hold an explicit regional entitlement. Cross-region access requires a separate `hr.review.read.cross_region` entitlement.
- **R-01.3 Field-level rules:** Compensation notes are gated by a separate `hr.review.read.compensation` entitlement and are masked by default in the UI; staff must perform an explicit "reveal" action that is logged.
- **R-01.4 Identifier handling:** Employee IDs MUST NOT appear in URL paths or query strings used for navigation. Use opaque, server-issued review/employee handles in URLs; resolve to internal IDs server-side.
- **R-01.5 Search input validation:** Define and document allowed characters and length bounds for name and employee-ID search inputs (V2.1.1). Reject malformed input at the trust boundary with a generic error.
- **R-01.6 Transport:** All connections (browser-to-app, app-to-DB, app-to-IdP, app-to-log-store) use TLS 1.2+; no fallback to cleartext.
- **R-01.7 Audit logging:** Every review view emits a structured log event with `who` (subject id), `when` (UTC timestamp), `what` (action=`review.view`), `target` (employee id, review id), `outcome`, and a correlation id. The review content itself MUST NOT be logged.
- **R-01.8 Failure mode:** Authorization denials and unexpected errors return a generic message (no stack traces, no internal field names) and are logged as security events.

**Updated Acceptance Criteria:**

- An authenticated user without `hr.review.read` who calls the review-fetch endpoint receives 403 and produces a logged authorization-failure event (V8.2.1, V16.3.2).
- An HR user without compensation entitlement sees compensation fields masked; toggling reveal records a `compensation.reveal` audit event (V8.2.3, V16.3.3).
- No URL or browser history entry contains a raw employee ID or review ID (V14.2.1).
- Network capture shows no plaintext HTTP for any in-scope flow (V12.2.1).
- Each successful and failed `review.view` call appears in the centralized log store within 60 seconds, with all required metadata fields populated (V16.2.1, V16.2.2, V16.4.3).
- Triggering a backend exception returns a generic 500 with a correlation id; no stack trace is rendered (V16.5.1).

**Securability Notes.** This is the primary read path for sensitive personnel data, so the dominant SSEM concerns are *Confidentiality* (field-level entitlements; mask compensation until intent is declared) and *Accountability* (every read produces an unambiguous audit event so misuse is detectable). FIASSE trust-boundary discipline (S2.6) applies at the edge: validate identifiers and search input strictly, then keep the interior code straightforward. *Analyzability* matters because audit-log usefulness depends on consistent, structured event shape across all read paths — design one logging contract and reuse it. SSO authentication is not authorization; treat the application's permission checks as the load-bearing control.

---

### Feature F-02: Add HR commentary

**Description.** HR staff can attach a private commentary note to an existing review. The note is visible to other HR staff but not to the employee or their manager. Notes are timestamped with the author's name.

**ASVS Mapping:** V2.1.1, V2.1.3, V2.4.1, V8.2.1, V8.2.2, V8.2.3, V8.3.1, V8.3.2, V13.1.x (output encoding), V14.1.1, V14.2.4, V16.2.1, V16.2.5, V16.3.3, V16.4.1, V16.5.1.

**Updated Requirements:**

- **R-02.1 Authorization:** Only users with `hr.commentary.write` may create or edit notes; only users with `hr.commentary.read` may read them. Employees and managers MUST NOT receive this entitlement.
- **R-02.2 Field-level visibility:** Commentary notes are excluded from any read endpoint accessible to non-HR roles, including any future self-service surface. Backend filtering (not UI hiding) enforces this (V8.3.1).
- **R-02.3 Input validation:** Note body length is bounded (e.g., 4 KB max — value to be confirmed with HR), character set is documented, and content is treated as untrusted free text. Reject inputs exceeding bounds at the trust boundary.
- **R-02.4 Storage and rendering:** Notes are stored verbatim and output-encoded at render time (HTML-context-aware encoding) to prevent stored XSS. The application MUST NOT execute or render embedded markup that escalates beyond plain text and a documented allowed subset (if any).
- **R-02.5 Authenticity / accountability:** The author identity is set server-side from the authenticated subject; clients MUST NOT supply or override `author_id`. Timestamps are UTC and set server-side.
- **R-02.6 Immutability of audit metadata:** Note edits create a new revision rather than overwriting; original `created_by`, `created_at`, and prior content are preserved for accountability.
- **R-02.7 Logging:** Each note create/edit/delete emits a security event: `who`, `when` (UTC), `what` (action), `target_review_id`, and a hash of the note body (not the body itself, per V16.2.5).
- **R-02.8 Anti-automation:** Per-user create/edit rate is bounded to detect scripted abuse (V2.4.1).
- **R-02.9 Retention:** Note retention follows HR record-retention policy; retention period is documented in the data classification (V14.2.4).

**Updated Acceptance Criteria:**

- A user without `hr.commentary.read` who fetches a review receives the review without notes; the response shape MUST be identical to the case where no notes exist (no field-presence side channel) (V8.2.3).
- A request with a client-supplied `author_id` is ignored; the recorded author is the authenticated subject (V8.3.1).
- A note containing `<script>` tags renders as inert escaped text in every consuming surface (V13.1).
- Editing a note preserves the original revision and all fields are retrievable for audit (V16.4.2).
- Each note operation produces a structured audit event reaching the central log store within 60 seconds (V16.2.1, V16.4.3).
- Submitting beyond N notes/minute by the same user triggers a rate-limit response and a security event (V2.4.1, V16.3.3).

**Securability Notes.** F-02 is a write path for free-text data that is then displayed to other HR staff, so *Integrity* (server-controlled author and timestamp; immutable revisions) and the output-encoding side of *Confidentiality/Trustworthiness* (no stored XSS escalating into other staff sessions) drive the design. FIASSE trust-boundary discipline (S2.6) applies at both ingress (length, character-set validation) and egress (context-aware encoding at render). Visibility scoping must be enforced server-side; UI hiding alone is a known anti-pattern. Keep the audit log shape consistent with F-01 to preserve *Analyzability* across the product.

---

### Feature F-03: Export region report

**Description.** HR staff can export a CSV of all reviews in their region for the current cycle. The CSV includes employee ID, name, rating, manager comment, and compensation note.

**ASVS Mapping:** V2.1.3, V2.4.1, V8.2.1, V8.2.2, V8.4.1, V11.3.2, V14.1.1, V14.2.4, V14.2.6 (L3), V16.2.1, V16.3.2 (L3), V16.3.3, V16.4.2, V16.4.3, V16.5.1, V16.5.3.

**Updated Requirements:**

- **R-03.1 Dedicated export entitlement:** A separate `hr.review.export` entitlement is required, granted to a small subset of HR staff; deny-by-default.
- **R-03.2 Region scoping:** Export query MUST be server-constrained to the requester's authorized region(s); request parameters cannot widen scope (V8.4.1). A cross-region export requires a distinct entitlement.
- **R-03.3 Field minimization (L3):** The default CSV omits compensation notes. Including compensation requires a secondary `hr.review.export.compensation` entitlement, an explicit user choice, and a recorded business justification field (V14.2.6).
- **R-03.4 Volume limits:** A documented per-user and per-region cap on rows-per-export and exports-per-day (V2.1.3, V2.4.1). Exceeding the cap is denied and logged as a security event.
- **R-03.5 At-rest protection:** If exports are stored server-side (e.g., for download retrieval), files are encrypted at rest using approved authenticated encryption (V11.3.2/V11.3.3) and auto-deleted after a documented short window (e.g., 24 h).
- **R-03.6 Generation hygiene:** The CSV writer MUST defend against CSV injection (`=`, `+`, `-`, `@`, tab, CR prefixed cells are escaped or sanitized) so opening the file in spreadsheet software cannot trigger formulas (transparency/integrity).
- **R-03.7 Logging (L3):** Every export emits a structured event including `who`, `when`, `region`, `row_count`, `fields_included`, `compensation_included` (boolean), `justification`, and a correlation id. Export content itself is not logged (V16.2.5, V16.3.2).
- **R-03.8 Fail-closed:** Partial-failure during export aborts the export and returns an error; partial CSVs are never delivered silently (V16.5.3).
- **R-03.9 Transport:** Download links are short-lived, single-use, and served only over TLS to authenticated sessions; URLs MUST NOT contain the export ID in a guessable form — use a CSPRNG-generated handle (V11.5.1, V14.2.1).

**Updated Acceptance Criteria:**

- A user from Region A requesting Region B's export receives 403 regardless of any client-side parameter; the attempt is logged (V8.4.1, V16.3.2).
- The default export contains no compensation column; enabling it requires both the L3 entitlement and a non-empty justification, and produces an additional `export.compensation_included=true` event field.
- Submitting an export request with a row count exceeding the documented cap returns a deny response and a logged security event.
- A cell starting with `=` in source data appears in the CSV with the leading character neutralized (e.g., prefixed apostrophe or quoted), per documented CSV-injection defense.
- Inducing a backend failure mid-stream causes the request to fail closed; no partial file is delivered to the user (V16.5.3).
- Stored export files are encrypted at rest and deleted within the documented retention window; deletion is verifiable from a log event.
- Network capture confirms TLS 1.2+ for download; URLs contain no PII or guessable IDs.

**Securability Notes.** Bulk export is the highest-leverage data-exfiltration surface in this product, so *Confidentiality* (entitlement, region scoping, field minimization) and *Accountability* (rich, immutable audit with field-list and justification) dominate. *Resilience* matters because partial failures must fail closed — silent partial CSVs are an integrity hazard. FIASSE's "reduce material impact" tenet (S2.3) directly justifies the L3 escalation here: one careless export can materially harm many employees, so the cost of stricter controls is well-spent. Guard CSV generation against formula-injection — it is a routinely overlooked side channel. Keep export volumes observable so abuse patterns are detectable.

---

### Feature F-04: Bulk reassign reviewer

**Description.** When a manager leaves the company, an HR admin can bulk-reassign all of that manager's pending reviews to another manager. The admin selects the source and target managers and clicks "Reassign all".

**ASVS Mapping:** V2.1.3, V2.4.1, V8.2.1, V8.2.2, V8.4.1, V8.4.2 (L3), V11.5.1, V16.2.1, V16.3.2 (L3), V16.3.3, V16.4.1, V16.4.2, V16.4.3, V16.5.1, V16.5.3.

**Updated Requirements:**

- **R-04.1 Privileged role:** Action requires a dedicated `hr.review.reassign.admin` role, distinct from regular HR staff entitlements; deny-by-default.
- **R-04.2 Step-up authentication (L3):** Initiating a bulk reassignment MUST require recent (within a documented short window, e.g., 5 minutes) re-authentication via the corporate IdP step-up flow (V8.4.2).
- **R-04.3 Operation correlation:** Each bulk action receives a CSPRNG-generated `operation_id` (≥128 bits entropy) used to tie all per-review changes to one logical action (V11.5.1).
- **R-04.4 Target validation:** The target manager MUST be a current, active employee with a permitted reviewer entitlement; the source manager MUST be in a documented "departing/departed" state. Attempts to reassign to invalid targets are rejected with a logged event.
- **R-04.5 Volume / business limits:** Documented upper bound on reviews per single bulk action (V2.1.3); above the bound, the operation must be split or escalated. Anti-automation rate limit applies (V2.4.1).
- **R-04.6 Confirmation:** UI requires a two-step confirmation showing: source manager identity, target manager identity, exact count of pending reviews, and the `operation_id`. The confirmation payload is what the server validates — not a separate, weaker request.
- **R-04.7 Atomicity / fail-closed:** The reassignment is executed as a transactional unit. On partial failure, the system MUST roll back to the pre-action state OR record a complete partial-state record and surface a single-step undo using `operation_id` (V16.5.3).
- **R-04.8 Undo capability:** A reverse operation, gated by the same role and step-up, can revert by `operation_id` within a documented window (e.g., 7 days).
- **R-04.9 Audit (L3):** Emit one `reassign.bulk.start` event and one event per affected review (`reassign.review`) plus a final `reassign.bulk.complete` event, all carrying `operation_id`, `actor`, `source_manager`, `target_manager`, `review_id`, UTC timestamp, and outcome. All authorization decisions (allow and deny) are logged (V16.3.2 L3).
- **R-04.10 Log integrity:** Bulk-action audit events are written append-only and forwarded to a logically separate log store (V16.4.2, V16.4.3).
- **R-04.11 Input validation and encoding:** Source/target identifiers and any free-text justification field undergo strict input validation and log-injection-safe encoding (V16.4.1).

**Updated Acceptance Criteria:**

- A user without `hr.review.reassign.admin` calling the reassign endpoint directly receives 403; the attempt is logged with full subject identity and `operation_id` if one was supplied (V8.2.1, V16.3.2).
- Initiating reassignment without recent step-up authentication forces an IdP step-up challenge; bypassing the UI does not bypass the check (V8.4.2).
- Reassigning to an inactive or unauthorized target manager is rejected; rejection produces an audit event.
- The audit log for one reassignment can be reconstructed end-to-end by `operation_id` and shows: actor, source, target, every affected review, timestamps, and outcome.
- A failure injected mid-batch results in either (a) full rollback or (b) a recorded partial state plus a working single-step undo, with no silent partial completion (V16.5.3).
- An undo within the documented window restores the pre-action state and emits a fully linked audit trail.
- Submitting reassignments exceeding the documented per-action cap is rejected; a security event is logged.
- Log entries containing user-supplied free text render safely when ingested by the central log processor (no log injection) (V16.4.1).

**Securability Notes.** F-04 is privileged, high-blast-radius, and irreversible-by-default — the SSEM emphasis is *Authenticity* (step-up auth so the action is provably the admin's), *Accountability* (rich, append-only audit keyed by `operation_id`), and *Resilience* (atomic execution, undo). FIASSE's "reduce material impact" tenet (S2.3) and trust-boundary discipline (S2.6) justify treating this as L3 even though the rest of the product is L2. Make the operation observable and reversible: a bulk privileged action that cannot be reconstructed from logs or undone is a known incident-response failure mode. Keep the action's permission distinct from the regular HR role so least-privilege is preserved when ordinary staff do their day-to-day work.

---

## 4. Cross-Cutting Securability Requirements

These apply across all features and should be tracked once, not duplicated per feature.

### 4.1 Identity, Session, and Trust Boundary

- **X-IDP-1** Authentication is delegated to the corporate IdP via SSO; the application MUST NOT issue or store passwords (V2.x out of scope).
- **X-IDP-2** Session inactivity timeout, absolute session lifetime, concurrent-session policy, and single-logout coordination with the IdP are documented (V7.1.1, V7.1.2, V7.1.3).
- **X-IDP-3** All session-token verification occurs at a trusted backend (V7.2.1). The application MUST NOT use long-lived static API keys for session identity (V7.2.2).
- **X-IDP-4** IdP group/claim attributes are mapped explicitly to internal roles (`hr.review.read`, `hr.review.read.compensation`, `hr.review.export`, `hr.review.export.compensation`, `hr.commentary.read`, `hr.commentary.write`, `hr.review.reassign.admin`); no implicit mapping.

### 4.2 Authorization

- **X-AZ-1** All authorization decisions are made server-side at a trusted tier (V8.3.1). Client-side controls are UX, not security.
- **X-AZ-2** Authorization is documented (V8.1.1, V8.1.2): a single matrix of `role → action → field/scope` is maintained as the source of truth.
- **X-AZ-3** Permission changes (role grants/revocations) take effect immediately on the next request; cached entitlement data refreshes within a documented bound (V8.3.2).

### 4.3 Data Classification and Protection

- **X-DC-1** A single product data-classification table identifies sensitivity tier per field (employee_id, name, rating, manager_comment, peer_feedback, compensation_note, hr_commentary) with documented protection requirements (V14.1.1, V14.1.2).
- **X-DC-2** Compensation notes and HR commentary are classified at the highest tier in the product; controls (encryption at rest, access logging, masked-by-default UI) follow the classification (V14.2.4).
- **X-DC-3** Sensitive fields MUST NOT appear in URLs, query strings, browser cache headers, or third-party trackers (V14.2.1, V14.2.3).
- **X-DC-4** Retention schedules per data class are documented and enforced; outdated data is deleted on a defined schedule (V14.2.7 considered as L3 stretch).

### 4.4 Transport and Configuration

- **X-TR-1** TLS 1.2+ with recommended cipher suites is required for all network hops (browser-app, app-DB, app-IdP, app-log-store) (V12.1.1, V12.1.2). No fallback.
- **X-CFG-1** All external service dependencies (IdP, DB, log store, file storage) and their timeouts, retry policies, and failure modes are documented (V13.1.1).
- **X-CFG-2** No secrets in source control; secrets retrieval and rotation policy is documented (V13.1.4 L3 considered).

### 4.5 Input Validation and Output Encoding

- **X-IV-1** A documented input validation contract exists per endpoint (allowed types, lengths, character sets, value ranges) (V2.1.1).
- **X-IV-2** Output encoding is context-aware (HTML, attribute, JS, CSV) at render time; trusting upstream sanitization is forbidden.
- **X-IV-3** Anti-automation/rate-limit thresholds are documented per sensitive endpoint (search, note create, export, reassign) (V2.4.1).

### 4.6 Logging and Audit (Foundation)

- **X-LOG-1** A logging inventory documents event types, schema, destinations, retention, and access controls (V16.1.1).
- **X-LOG-2** Every security-relevant event includes UTC timestamp, actor, action, target, outcome, and correlation id (V16.2.1, V16.2.2).
- **X-LOG-3** Authentication outcomes (delegated from IdP), authorization decisions (allow + deny), and security-control bypass attempts are logged (V16.3.1, V16.3.2, V16.3.3).
- **X-LOG-4** Sensitive review content, commentary content, and compensation values MUST NOT be written to logs; references (IDs, hashes) only (V16.2.5).
- **X-LOG-5** Logs are append-only at the storage tier and forwarded to a logically separate log store within a documented latency bound (V16.4.2, V16.4.3).
- **X-LOG-6** All logged user-supplied data is encoded to prevent log injection (V16.4.1).

### 4.7 Error Handling and Resilience

- **X-ER-1** Generic error messages are returned for unexpected/security-sensitive errors; correlation ids tie user-visible errors to logs (V16.5.1).
- **X-ER-2** External-resource failure modes (IdP unreachable, DB timeout, log store unavailable) have documented graceful-degradation behavior; the system fails closed for authorization decisions (V16.5.2, V16.5.3).
- **X-ER-3** A last-resort exception handler prevents process crash and ensures errors are logged (V16.5.4 considered as L3 stretch).

### 4.8 Cross-Cutting Securability Notes

The unifying engineering theme across all features is *Accountability with Confidentiality*: the system must produce a faithful, unambiguous record of who did what to which sensitive record, while never letting the audit trail itself become a leak channel. FIASSE trust-boundary discipline (S2.6) anchors this — strict validation and mapping at the edge (SSO claims to internal roles, opaque IDs to internal IDs, raw input to validated input), simple and consistent enforcement in the interior. *Analyzability* and *Modifiability* (SSEM Maintainability pillar) are paid forward by enforcing one logging contract and one authorization matrix shared by all features; that lets the security posture *evolve* (S2.1) when entitlements change rather than re-auditing every endpoint. The "internal-only behind SSO" framing is treated as risk reduction, not as the security architecture.

---

## 5. Out of Scope (Unchanged + Confirmed)

- Mobile app
- Self-service access by employees (separate product) — confirms F-02's hard constraint that commentary MUST NOT leak via any future surface
- Integration with payroll systems

---

## 6. Acceptance (Replaces Original Two Bullets)

The acceptance criteria below supersede the original PRD's two bullets. Functional and securability acceptance are tracked together.

### Functional

- **A-F1** HR staff can complete each task (view, comment, export, reassign) without raising a support ticket.
- **A-F2** The tool loads in under 2 seconds for typical queries.

### Securability (must all be demonstrably testable)

- **A-S1** Every authorization decision (allow and deny) for in-scope features produces a structured log event reaching the central log store within 60 seconds.
- **A-S2** No URL, log, error message, or browser cache entry exposes raw employee IDs, review content, or compensation values.
- **A-S3** Compensation fields and HR commentary are masked by default in the UI; reveal/export of compensation is gated by a distinct entitlement and produces an audit event.
- **A-S4** Bulk reassignment requires a fresh step-up authentication, runs atomically (or with verifiable undo), and produces a fully reconstructable audit trail keyed by `operation_id`.
- **A-S5** Region-scoped access is server-enforced; client-side parameter changes cannot widen scope.
- **A-S6** All external traffic uses TLS 1.2+; no fallback path exists.
- **A-S7** A documented data-classification table, authorization matrix, and logging inventory exist and match implementation behavior.
- **A-S8** Synthetic abuse tests (over-rate note creation, oversized export, malformed search input, log-injection payloads, CSV-injection payloads, unauthenticated direct API call) all fail closed and produce expected security events.

---

## 7. Open Gaps and Assumptions

### Assumptions

- **A1** SSO is provided by a corporate IdP (e.g., Entra ID / Okta / equivalent) that supports step-up authentication; if the IdP cannot enforce step-up, F-04's L3 controls require redesign.
- **A2** A central, append-only log store and SIEM exist or will be provisioned; if not, X-LOG-5 and F-04 audit requirements need a dedicated solution.
- **A3** "Region" is a defined organizational attribute available in the IdP or HRIS that can be authoritatively used for scoping; otherwise region authorization is unenforceable.
- **A4** The 80-HR-staff population is small enough that manual entitlement management is feasible; if it grows or churns rapidly, an automated entitlement-lifecycle process is required.

### Open Gaps Requiring Stakeholder Input

- **G1 Retention windows.** HR/legal must specify retention durations per data class (reviews, commentary, exports, audit logs) before X-DC-4 is implementable.
- **G2 Bulk-action upper bound.** A specific maximum number of reviews per F-04 operation must be set (R-04.5).
- **G3 Export volume cap.** A per-user and per-region per-day export cap must be set (R-03.4).
- **G4 Cross-region access policy.** Whether `hr.review.read.cross_region` and `hr.review.export.cross_region` are needed at all, and if so for which roles, is a policy decision.
- **G5 Compensation reveal/export justification.** The required content of the justification field (free-text vs. ticket reference vs. dropdown reason code) needs HR/compliance input.
- **G6 Undo window for F-04.** Confirm the 7-day suggestion or set the actual value.
- **G7 Privacy regulation scope.** Confirm which regional regimes (e.g., GDPR for EU regions) apply; this may pull V14.2.7 (L3 retention automation) into baseline.
- **G8 Peer feedback attribution.** Original PRD does not state whether peer feedback is attributed or anonymized; this materially affects V14.1 classification and X-DC-1.
- **G9 Threat-model review.** A formal threat-model session for F-03 and F-04 is recommended before implementation given their L3 escalation.
- **G10 Logging budget.** Confirm log-store retention budget so X-LOG-1 and audit obligations align with cost constraints.

### Items Explicitly Marked Not Applicable

- **NA1** ASVS V2.2/V2.3 password storage and recovery — authentication is delegated to SSO.
- **NA2** ASVS V4.3 GraphQL — not used.
- **NA3** ASVS V11.6 / V11.7 (advanced asymmetric crypto and in-use encryption) — no use case at this scope.
- **NA4** ASVS V5.x file upload — F-03 is download-only; no user-uploaded files. Re-evaluate if file upload is added.
