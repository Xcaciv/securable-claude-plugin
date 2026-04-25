# Securable Claude Plugin — FIASSE / SSEM

You are augmented with the **FIASSE Securable Engineering Plugin**, aligned with [FIASSE v1.0.4](https://github.com/Xcaciv/securable_software_engineering/blob/v1.0.4/docs/securable_framework.md). This plugin provides three core capabilities:

1. **Securability Engineering Review** — Analyze code for securable qualities using the FIASSE/SSEM framework
2. **Securability Engineering Code Generation** — Generate code that embodies securable qualities by default
3. **PRD Securability Enhancement** — Enhance product requirements with ASVS coverage and FIASSE/SSEM implementation guidance

## Plugin Structure

- `data/asvs/` — OWASP ASVS requirement chapters (V1–V14) organized by section. Consult these for requirement mapping and coverage decisions.
- `data/fiasse/` — FIASSE framework reference sections (S1.x–S8 plus Appendix A as `SA.x`) with YAML frontmatter. Consult these for definitions, measurement criteria, and principles.
- `skills/` — Skill definitions with YAML frontmatter describing when and how to apply each capability.
- `plays/` — Detailed step-by-step procedures for requirements, code generation, and analysis workflows.
- `templates/` — Output format templates for findings and reports.
- `scripts/` — Utility scripts for data extraction.

## Available Skills

### securability-engineering-review

Analyze code for securable engineering qualities using the SSEM framework. Scores **ten attributes** across three pillars (Maintainability, Trustworthiness, Reliability) on a 0–10 scale.

**Invoke when**: User asks to review, assess, audit, or evaluate code securability, code quality for security, or FIASSE/SSEM compliance.

**Procedure**: Follow `plays/code-analysis/securability-engineering-review.md` for the full analysis workflow.

**Skill definition**: `skills/securability-engineering-review/SKILL.md`

### securability-engineering

Wrap code generation with FIASSE/SSEM constraints so that output is engineered to be inherently securable by default.

**Invoke when**: User asks to generate, scaffold, or refactor code with securable qualities, or requests "secure code", "securable code", or "FIASSE-compliant code".

**Procedure**: Follow `plays/code-generation/securable-generation.md` for the full generation -> review -> enhancement workflow.

**Skill definition**: `skills/securability-engineering/SKILL.md`

### prd-securability-enhancement

Enhance PRD features with step-by-step ASVS and FIASSE/SSEM augmentation.

**Invoke when**: User asks to choose an ASVS level, map PRD features to ASVS requirements, fill requirement gaps, and annotate implementation expectations using SSEM attributes and FIASSE tenets.

**Procedure**: Follow `plays/requirements-analysis/prd-fiasse-asvs-enhancement.md` for the full requirements workflow.

**Skill definition**: `skills/prd-securability-enhancement/SKILL.md`

## Guiding Principles

1. **Securable ≠ Secure** — There is no static "secure" state (S2.1). Focus on engineering qualities that enable code to adapt to evolving threats.
2. **Engineer, Don't Hack** — Build securely through quality attributes, not adversarial/exploit thinking (S2.4).
3. **Reduce Material Impact** — Aim to reduce the probability of material impact from cyber events through pragmatic, context-appropriate controls (S2.3).
4. **Transparency** — Generated and reviewed code should be observable: meaningful naming, structured logging, audit trails (S2.5).
5. **Least Astonishment** — Systems should behave intuitively and predictably; eliminate hidden side effects and surprising boundaries (S2.6).
6. **Boundary Control** — Apply strict control at trust boundaries (the "hard shell"); preserve flexibility in the interior (S4.3).

## SSEM Model Quick Reference (v1.0.4 — 10 attributes)

| **Maintainability** | **Trustworthiness** | **Reliability** |
|:--------------------|:-------------------:|----------------:|
| Analyzability       | Confidentiality     | Availability    |
| Modifiability       | Accountability      | Integrity       |
| Testability         | Authenticity        | Resilience      |
| Observability       |                     |                 |

> **v1.0.4 note**: Observability is the new 10th attribute under Maintainability. Measurement guidance is in Appendix A (`data/fiasse/SA.*.md`).

## Output Formats

- Individual findings: Use the format in `templates/finding.md`
- Full assessment reports: Use the format in `templates/report.md`

## References

- [FIASSE Framework v1.0.4](https://github.com/Xcaciv/securable_software_engineering/blob/v1.0.4/docs/securable_framework.md) — Framework for Integrating Application Security into Software Engineering
- [SSEM](https://github.com/Xcaciv/securable_software_engineering) — Securable Software Engineering Model
- License: CC-BY-4.0
