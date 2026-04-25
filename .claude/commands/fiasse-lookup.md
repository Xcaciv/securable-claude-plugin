Look up the FIASSE/SSEM reference material for the specified topic and provide a concise explanation with practical guidance.

Reference `data/fiasse/` sections to find the relevant content. Each section file has YAML frontmatter (including `fiasse_version: 1.0.4`) with `when_to_use` triggers that help match the query.

## SSEM Quick Reference (FIASSE v1.0.4 — 10 attributes)

| **Maintainability** | **Trustworthiness** | **Reliability** |
|:--------------------|:-------------------:|----------------:|
| Analyzability (S3.2.1.1) | Confidentiality (S3.2.2.1) | Availability (S3.2.3.1) |
| Modifiability (S3.2.1.2) | Accountability (S3.2.2.2) | Integrity (S3.2.3.2) |
| Testability (S3.2.1.3)   | Authenticity (S3.2.2.3)   | Resilience (S3.2.3.3) |
| Observability (S3.2.1.4) |                           |                       |

## Section Index (FIASSE v1.0.4)

- **S1.1–S1.2** — Introduction (challenge, purpose, scope)
- **S2.1–S2.6** — Foundational Principles (incl. S2.5 Transparency, S2.6 Least Astonishment)
- **S3.1** — SSEM Model Overview and Design Language
- **S3.2** — Core Securable Attributes (umbrella)
- **S3.2.1** — Maintainability + leaves (S3.2.1.1 Analyzability, S3.2.1.2 Modifiability, S3.2.1.3 Testability, S3.2.1.4 Observability)
- **S3.2.2** — Trustworthiness + leaves (Confidentiality, Accountability, Authenticity)
- **S3.2.3** — Reliability + leaves (Availability, Integrity, Resilience)
- **S4.1–S4.6** — Practical Guidance: Clear Expectations (S4.1), Threat Modeling (S4.2), Boundary Control Principle (S4.3), Resilient Coding (S4.4) + Canonical Input Handling leaves (S4.4.1, S4.4.1.1 Request Surface Minimization, S4.4.1.2 Derived Integrity), Dependency Management (S4.5), Dependency Stewardship (S4.6)
- **S5.1–S5.3** — Integrating Security into Development Processes (Native extension, Merge Reviews, Early Integration)
- **S6.1–S6.2** — Common AppSec Anti-Patterns (Shoveling Left, Strategic Use of Output)
- **S7.1–S7.4** — Roles and Responsibilities (Security Team, Senior Engineers, Developing Engineers, Product Owners)
- **S8** — Organizational Adoption of FIASSE
- **SA.1–SA.3** — Appendix A: Measuring SSEM Attributes (Maintainability, Trustworthiness, Reliability) with attribute leaves (SA.1.4 measures Observability)

## Arguments

- `$ARGUMENTS` — The FIASSE/SSEM topic to look up (e.g., "integrity", "trust boundaries", "input validation", "transparency", "observability", "least astonishment", "boundary control", "S3.2.2").
