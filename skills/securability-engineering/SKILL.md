---
name: securability-engineering
description: Generate, scaffold, or refactor code so it embodies FIASSE securable engineering qualities by default — applying the ten SSEM attributes (Analyzability, Modifiability, Testability, Observability, Confidentiality, Accountability, Authenticity, Availability, Integrity, Resilience), the Transparency and Least-Astonishment principles, ASVS-aligned controls at the feature level, and FIASSE v1.0.4 defensive coding practices. Invoke this skill whenever the user asks for "secure code", "securable code", "FIASSE-compliant code", asks to "harden" / "secure-by-default" / "audit-ready" code, asks to refactor for security, or generates security-sensitive components — even when those words are not explicit (e.g., "write an auth/login endpoint", "build a file upload handler", "implement password reset", "validate this user input", "write an API for X", "generate a database query handler", "make this safe to expose"). Use for code-generation moments specifically; for requirements work use prd-securability-enhancement, and for full SSEM-scored review use securability-engineering-review.
license: CC-BY-4.0
---

# Securability Engineering — Code Generation Wrapper

This skill augments the built-in code generation capability by applying FIASSE/SSEM principles as engineering constraints. It does **not** perform full SSEM scoring (use `securability-engineering-review` for that) and does **not** run the full requirement → generate → review → enhance loop (use `plays/code-generation/securable-generation.md` for that). It ensures that **generated code embodies securable qualities from the start**.

Reference data: `data/fiasse/` (especially S2.1–S2.6 foundational principles, S3.2.1–S3.2.3 SSEM attributes including S3.2.1.4 Observability, S2.5 Transparency, S4.3 Boundary Control, S4.4 Resilient Coding, S4.4.1 Canonical Input Handling, S4.6 Dependency Stewardship) and `data/asvs/` for feature-level requirements.

## When to Invoke

Trigger this skill when the user asks to:

- Generate new code (functions, modules, services, APIs, scripts)
- Scaffold a project, feature, or component
- Refactor existing code for security or maintainability
- Implement security-sensitive functionality: authentication, authorization, input handling, file upload/download, data access, cryptography, logging, error handling, session management
- Write code that crosses a trust boundary (any user/external input, any storage I/O, any network egress, any cross-service call)

Watch for adjacent phrasings that should still trigger: "make this safe", "harden this endpoint", "I'm exposing this to the internet, can you...", "write the production version of...", "audit-ready", "production-grade".

## Foundational Constraints

Before generating any code, apply these FIASSE principles:

1. **The Securable Paradigm (S2.1)** — There is no static "secure" state. Generate code with qualities that let it adapt to evolving threats, not code that is merely "secure right now".

2. **Resiliently Add Computing Value (S2.2)** — Code must be robust enough to withstand change, stress, and attack while delivering business value. Security qualities are engineering requirements, not afterthoughts.

3. **Reducing Material Impact (S2.3)** — Favor pragmatic controls aligned with the code's context and exposure, not theoretical completeness.

4. **Derived Integrity (S4.4.1.2)** — Never implicitly trust client-supplied values for server-owned state. Explicitly extract only expected values from requests; never accept client input directly for critical state or decisions.

5. **Transparency & Observability (S2.5, S3.2.1.4)** — Code must be observable from its own outputs: meaningful naming, structured logging at trust boundaries, audit trails for security-sensitive actions, and instrumentation for health/performance built into the code rather than depending on external tooling alone.

6. **Least Astonishment (S2.6)** — Behaviour and side-effects must match what the name and signature suggest. No hidden mutation, no implicit network/filesystem effects, no surprising error paths. Predictable behaviour aids both Analyzability and security reasoning.

7. **Boundary Control (S4.3)** — Flexibility belongs in the interior; control belongs at every trust boundary. Treat boundaries as the hard shell — strict input handling there — and keep the interior loose enough to evolve.

8. **Dependency Hygiene & Stewardship (S4.5, S4.6)** — Default to the latest stable release compatible with the runtime and framework. Prefer packages with low CVE/CWE exposure, active maintenance, and strong release signals. Minimize dependency count and transitive risk; treat each dependency as an ongoing relationship, not a one-time decision.

9. **Canonical Input Handling (S4.4.1)** — Apply canonicalize → sanitize → validate at every trust boundary. Prefer specific types and constrained enums. Never use a value that has not been fully vetted. Apply Request Surface Minimization (S4.4.1.1) — process only the specific named values you expect.

## SSEM Attribute Enforcement

Every code generation output must satisfy these ten attributes. Read `data/fiasse/` sections for definitions when context is needed.

### Maintainability (S3.2.1)

| Attribute | Enforcement |
|-----------|-------------|
| **Analyzability** (S3.2.1.1) | Methods ≤ 30 LoC. Cyclomatic complexity < 10. Clear, descriptive naming. No dead code. Comments only at trust boundaries and complex logic, explaining *why* — not *what*. |
| **Modifiability** (S3.2.1.2) | Loose coupling via interfaces / dependency injection. No static mutable state. Security-sensitive logic (auth, crypto, validation) centralized in dedicated modules, not scattered across call sites. Configuration externalized. |
| **Testability** (S3.2.1.3) | All public interfaces testable without modifying code under test. Dependencies injectable / mockable. Security controls isolated for dedicated test suites. |
| **Observability** (S3.2.1.4) | Code-level instrumentation, not external tooling alone. Structured logs with sufficient context (who/what/where/when/outcome) at trust boundaries and security-sensitive operations. Health and performance metrics exposed through a standardized API. Failure paths produce observable signals; no silent exception swallowing. UI/operator feedback surfaces meaningful state without leaking internals. |

### Trustworthiness (S3.2.2)

| Attribute | Enforcement |
|-----------|-------------|
| **Confidentiality** (S3.2.2.1) | Sensitive data classified at the type level. Least-privilege data access. No secrets in code, logs, or error messages. Encryption at rest and in transit where applicable. Data minimization — collect and retain only what is needed. |
| **Accountability** (S3.2.2.2) | Security-sensitive actions logged with structured data (who, what, where, when). Audit trails append-only. Auth events (login, logout, failure) and authz decisions (grant, deny) recorded. No sensitive data in logs. |
| **Authenticity** (S3.2.2.3) | Use established authentication mechanisms (Defendable Authentication). Verify token/session integrity (signed JWTs with pinned algorithm, secure cookies). Mutually authenticate service-to-service calls. Support non-repudiation. |

### Reliability (S3.2.3)

| Attribute | Enforcement |
|-----------|-------------|
| **Availability** (S3.2.3.1) | Enforce resource limits (memory, connections, file handles). Configure timeouts for all external calls. Rate-limit where appropriate. Thread-safe design for concurrent code. Graceful degradation for non-critical failures. |
| **Integrity** (S3.2.3.2) | Validate input at every trust boundary: canonicalize → sanitize → validate (S4.4.1). Output-encode when crossing trust boundaries. Use parameterized queries exclusively. Apply Derived Integrity Principle (S4.4.1.2) — never accept client-supplied values for server-owned state. Apply Request Surface Minimization (S4.4.1.1) — extract only specific expected values from requests. |
| **Resilience** (S3.2.3.3) | Defensive coding: anticipate out-of-bounds input and handle gracefully. Specific exception handling — no bare catch-all. Sandbox null checks to input/DB boundaries. Use immutable data structures in concurrent code. No resource leaks — deterministic disposal patterns (`with`, `using`, RAII). Graceful and **secure** failure: error messages don't leak internals; least privilege at the code level (drop elevated permissions when no longer needed). |

## Trust Boundary Handling (S4.3)

Apply the **Boundary Control Principle** (the "turtle analogy"): hard shell at trust boundaries, flexible interior.

- Identify trust boundaries: user input, API calls, DB queries, file I/O, service-to-service.
- Apply strict input handling (canonicalization → sanitization → validation) at every boundary entry point.
- Log boundary crossings with validation outcomes.
- Keep interior logic flexible — strict control belongs at the boundary, not everywhere.

### Defensive Boundary Parsing

Boundary input is hostile until proven otherwise — and "hostile" includes *well-meaning but unusual*, not just attacker-crafted. Real protocols and formats have edge cases that naive parsers fail on. Before writing any boundary-parsing code, think through these classes of variation explicitly:

- **HTTP headers** — case-insensitive names (`Authorization`, `authorization`); scheme tokens whose RFC behavior is case-insensitive (`Bearer`, `bearer`, `BEARER` per RFC 6750/7235); leading/trailing whitespace; multiple values for the same header; comma-separated lists; non-ASCII; missing entirely.
- **URLs and query strings** — percent-encoding variants, normalization (`/a/./b` → `/a/b`), path traversal (`..`), trailing slash, mixed-case schemes, IDN/punycode, repeated query keys.
- **Filenames and paths** — Unicode normalization forms (NFC/NFD), case sensitivity differences across filesystems, embedded null bytes, reserved names (`CON`, `PRN` on Windows), traversal segments.
- **Numeric and boolean inputs** — leading zeros, signed forms, scientific notation, `Infinity`/`NaN`, locale-specific separators, "yes"/"true"/"1"/"on" boolean variants.
- **Content types and MIME** — case-insensitive names, optional parameters (`; charset=utf-8`), spoofed declared type vs sniffed type.
- **JSON and structured payloads** — duplicate keys, depth bombs, integer overflow, type confusion (`"123"` vs `123`).
- **Tokens and credentials** — leading/trailing whitespace, base64url vs base64, padding variants, leading `Bearer ` already stripped or not.

Don't enumerate all of these in code — pick the ones that *matter for this boundary* and handle them deliberately. The default for any RFC-defined token is **"follow the RFC, don't reject the spec-compliant variant just because your prototype only saw one shape."**

## Steps

When generating code, apply this sequence:

1. **Identify Context** — Language, framework, system type, data sensitivity, exposure level, trust boundaries, feature category.

2. **Map Feature Requirements to ASVS** — Use `data/asvs/README.md` and the relevant `data/asvs/V*.md` chapters to identify the security requirements applying to the feature being generated. Match the request to ASVS sections via chapter topic and `when_to_use` guidance, then use the applicable requirements as implementation constraints.

3. **Apply SSEM Constraints** — Enforce the attribute rules in the tables above. Consult `data/fiasse/S3.2.1.md`–`S3.2.3.md` for umbrella definitions, and the leaf files (e.g., `S3.2.1.4.md` Observability, `S3.2.2.3.md` Authenticity) for attribute-specific guidance.

4. **Handle Trust Boundaries** — Identify where generated code crosses trust boundaries. Apply S4.3 (Boundary Control Principle) and S4.4 (Resilient Coding, including S4.4.1 Canonical Input Handling, S4.4.1.1 Request Surface Minimization, S4.4.1.2 Derived Integrity).

5. **Select Dependencies Deliberately** (S4.5 Management, S4.6 Stewardship):
   - Latest stable versions unless a compatibility constraint is known
   - Low known CVE/CWE exposure; no unresolved critical/high issues
   - Mature, actively maintained projects with recent releases
   - Minimize footprint; avoid libraries when standard library suffices
   - Pin versions; include lockfile guidance for reproducibility
   - Treat the dependency as an ongoing relationship: would it remain trustworthy and maintainable a year from now? (Stewardship)

6. **Instrument Transparency & Observability** — Add structured logging at security-sensitive points (S2.5). Include audit-trail hooks for auth/authz events. Expose health metrics where applicable. Build observability into the code itself, not relying on external tooling alone (S3.2.1.4).

7. **Generate Code** — Produce the code with all SSEM constraints applied. Code should be:
   - Small, single-purpose functions with clear names (Analyzability)
   - Loosely coupled with injectable dependencies (Modifiability, Testability)
   - Defensive at trust boundaries, flexible inside (Integrity, Resilience)
   - Aligned to applicable ASVS feature requirements
   - Observable via structured logging and audit trails (Transparency, Accountability)

8. **Self-Check** — Verify against the Generation Checklist below before returning.

## Output Format

The code itself is the primary deliverable. Spend the lion's share of your effort on the code.

After the code, append a short **Securability Notes** block. Keep it lean — bullets, not essays. The minimum useful shape is:

```markdown
## Securability Notes

- **SSEM attributes enforced**: [the 2–4 that actually shape this code, named briefly]
- **ASVS references**: [V-chapter.section IDs that apply]
- **Trust boundaries**: [where input is canonicalized/validated]
- **Dependencies**: [package@version — only when something non-trivial was introduced]
- **Trade-offs**: [decisions a reviewer needs to know — e.g., "in-process rate limit; switch to shared store for multi-instance"]
```

Skip bullets that have nothing material to say — an empty bullet is noise. For tiny edits with no boundary crossing, a single sentence is enough. The point of this block is to make review faster, not to perform thoroughness.

## Worked Example (Mini)

**User request**: "Write a Python FastAPI endpoint that lets a logged-in user fetch one of their own orders by ID."

**Sloppy default (what to avoid)**:

```python
@app.get("/orders/{order_id}")
def get_order(order_id: str, current_user=Depends(get_user)):
    order = db.query("SELECT * FROM orders WHERE id = '" + order_id + "'")
    return order
```

Issues: SQL injection (string concatenation), missing ownership check (any user can read any order — IDOR), broad return shape leaks fields, no logging, no input validation, no error handling.

**Securable version**:

```python
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from uuid import UUID
import structlog

router = APIRouter()
log = structlog.get_logger()

class OrderView(BaseModel):
    id: UUID
    placed_at: str
    status: str
    total_cents: int

@router.get("/orders/{order_id}", response_model=OrderView)
def get_order(
    order_id: UUID,                                  # canonicalized: must parse as UUID or 422
    current_user = Depends(get_authenticated_user),  # auth at the boundary
    orders = Depends(get_orders_repo),               # injectable for tests
):
    order = orders.find_owned_by(order_id, current_user.id)  # ownership enforced server-side
    if order is None:
        log.info("order_lookup.denied",
                 user_id=current_user.id, order_id=str(order_id), reason="not_found_or_not_owned")
        raise HTTPException(status_code=404, detail="Order not found")
    log.info("order_lookup.granted",
             user_id=current_user.id, order_id=str(order_id))
    return OrderView.model_validate(order)
```

What changed and why:

- `order_id: UUID` canonicalizes input at the boundary (Integrity, S4.4.1).
- `find_owned_by(order_id, user_id)` enforces ownership server-side — `current_user.id` is server-owned state, never trusted from the client (Derived Integrity, S4.4.1.2).
- `OrderView` projection limits the response to expected fields (Confidentiality, Request Surface Minimization S4.4.1.1).
- Structured logs at boundary outcomes give the audit pipeline what it needs (Accountability, Observability — S2.5, S3.2.1.4).
- `Depends(get_orders_repo)` is injectable, so tests can run without a real DB (Testability, Modifiability).
- 404 returned for both "not found" and "not owned" — avoids signalling existence to non-owners (Confidentiality).

A `Securability Notes` block following the code template above would round out the output.

## Generation Checklist

**Maintainability**:
- [ ] Functions ≤ 30 LoC, cyclomatic complexity < 10
- [ ] No static mutable state; dependencies injected
- [ ] Security logic centralized, not duplicated
- [ ] Testable without modifying code under test
- [ ] Observability built into the code: structured logs at boundaries with sufficient context; failure paths are observable; instrumentation does not depend on external tooling alone

**Trustworthiness**:
- [ ] No secrets, PII, or tokens in code, logs, or error output
- [ ] Auth/authz events logged with structured data
- [ ] Authentication uses established mechanisms
- [ ] Data access follows least privilege

**ASVS feature requirements**:
- [ ] Relevant ASVS chapter(s) identified for the feature
- [ ] Applicable ASVS requirements translated into implementation constraints
- [ ] Generated code satisfies the requirement intent, not just the happy path

**Reliability**:
- [ ] Input validated at every trust boundary (canonicalize → sanitize → validate)
- [ ] Derived Integrity applied (server-owned state not client-supplied)
- [ ] Request Surface Minimization applied (only expected values extracted)
- [ ] Specific exception handling with meaningful messages; no bare catch-all
- [ ] Resource limits, timeouts, and disposal patterns in place

**Dependency hygiene**:
- [ ] External libraries are necessary (no avoidable dependency added)
- [ ] Selected versions are latest stable compatible releases
- [ ] Selected packages have low known CVE/CWE exposure
- [ ] Active-maintenance signals checked
- [ ] Versions pinned; lockfile guidance included

**Transparency**:
- [ ] Meaningful naming; self-documenting code
- [ ] Structured logging at trust boundaries and security events
- [ ] Audit-trail hooks for security-sensitive actions

**Output format**:
- [ ] Securability Notes block included after the code (lean — only material points)
- [ ] Notes name the 2–4 SSEM attributes that actually shaped the code (not all ten)
- [ ] Trade-offs section calls out anything a reviewer would want to revisit

## When in Doubt

- Prefer a small, sharp piece of code with a clear Securability Notes block over a large, comprehensive one with implicit assumptions.
- Prefer flagging a missing requirement explicitly (in trade-offs) over silently introducing a default behavior.
- Prefer the standard library / framework primitive over a new dependency unless the dependency materially improves correctness.
- Prefer named exception types and explicit error responses over generic `try/except`.

## FIASSE References

- [FIASSE Framework v1.0.4](https://github.com/Xcaciv/securable_software_engineering/blob/v1.0.4/docs/securable_framework.md) — Framework for Integrating Application Security into Software Engineering
- `data/asvs/README.md` — ASVS chapter index
- `data/asvs/V*.md` — ASVS 5.0 feature requirements by chapter
- `data/fiasse/S2.1.md`–`S2.6.md` — Foundational Principles (incl. Transparency S2.5 and Least Astonishment S2.6)
- `data/fiasse/S3.2.1.md`–`S3.2.3.md` — SSEM Core Attribute umbrellas (Maintainability, Trustworthiness, Reliability)
- `data/fiasse/S3.2.1.4.md` — Observability (the 10th SSEM attribute)
- `data/fiasse/S4.3.md` — Boundary Control Principle (Trust Boundaries)
- `data/fiasse/S4.4.md` — Resilient Coding
- `data/fiasse/S4.4.1.md` — Canonical Input Handling
- `data/fiasse/S4.4.1.1.md` — Request Surface Minimization Principle
- `data/fiasse/S4.4.1.2.md` — Derived Integrity Principle
- `data/fiasse/S4.5.md` / `S4.6.md` — Dependency Management and Stewardship
- ISO/IEC 25010:2011 — Software quality models
- RFC 4949 — Internet Security Glossary
