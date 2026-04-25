Generate code that embodies securable qualities by default, applying FIASSE/SSEM principles as engineering constraints.

Use the skill definition in `skills/securability-engineering/SKILL.md` for attribute enforcement rules.
Reference `data/fiasse/` sections for detailed definitions when needed.

## Constraints Applied

Every piece of generated code is held to the ten SSEM attributes (FIASSE v1.0.4):

- **Analyzability** (S3.2.1.1) — Small methods (≤30 LoC), cyclomatic complexity < 10, clear naming, comments at trust boundaries
- **Modifiability** (S3.2.1.2) — Loose coupling, dependency injection, no static mutable state, centralized security logic
- **Testability** (S3.2.1.3) — All public interfaces testable, dependencies injectable/mockable
- **Observability** (S3.2.1.4) — Code-level instrumentation: structured logs at boundaries with sufficient context, failure paths produce signals, health/metrics through a standardized API
- **Confidentiality** (S3.2.2.1) — Sensitive data classified at the type level, no secrets in code/logs/errors, encryption where applicable
- **Accountability** (S3.2.2.2) — Structured audit logging for security-sensitive actions, no sensitive data in logs
- **Authenticity** (S3.2.2.3) — Defendable Authentication mechanisms, token/session integrity verification (signed JWTs with pinned algorithms)
- **Availability** (S3.2.3.1) — Resource limits, timeouts on external calls, rate limiting, graceful degradation
- **Integrity** (S3.2.3.2) — Input validation at trust boundaries (canonicalize → sanitize → validate, S4.4.1), parameterized queries, Derived Integrity Principle (S4.4.1.2), Request Surface Minimization (S4.4.1.1)
- **Resilience** (S3.2.3.3) — Defensive coding, specific exception handling, secure failure (no internals leak), least privilege at the code level, deterministic resource disposal, immutable data in concurrent code

Cross-cutting principles: **Transparency** (S2.5), **Least Astonishment** (S2.6), and **Boundary Control** (S4.3).

## Trust Boundary Handling (Boundary Control Principle, S4.3)

Hard shell at trust boundaries, flexible interior. Identify all trust boundaries and apply strict input handling at every entry point. Flexibility within the interior is an engineering asset; control at the boundary is a security requirement.

## Arguments

- `$ARGUMENTS` — Description of what code to generate (e.g., "REST API endpoint for user registration", "file upload handler with validation").
