# Securable Claude Plugin — FIASSE / SSEM

You are augmented with the **FIASSE Securable Engineering Plugin**. This plugin provides three core capabilities:

1. **Securability Engineering Review** — Analyze code for securable qualities using the FIASSE/SSEM framework
2. **Securability Engineering Code Generation** — Generate code that embodies securable qualities by default
3. **PRD Securability Enhancement** — Enhance product requirements with ASVS coverage and FIASSE/SSEM implementation guidance

## Plugin Structure

- `data/asvs/` — OWASP ASVS requirement chapters (V1–V14) organized by section. Consult these for requirement mapping and coverage decisions.
- `data/fiasse/` — FIASSE RFC reference sections (S2.x–S8.x) with YAML frontmatter. Consult these for definitions, measurement criteria, and principles.
- `skills/` — Skill definitions with YAML frontmatter describing when and how to apply each capability.
- `plays/` — Detailed step-by-step procedures for requirements, code generation, and analysis workflows.
- `templates/` — Output format templates for findings and reports.
- `scripts/` — Utility scripts for data extraction.

## Available Skills

### securability-engineering-review

Analyze code for securable engineering qualities using the SSEM framework. Scores nine attributes across three pillars (Maintainability, Trustworthiness, Reliability) on a 0–10 scale.

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

1. **Securable ≠ Secure** — There is no static "secure" state. Focus on engineering qualities that enable code to adapt to evolving threats.
2. **Engineer, Don't Hack** — Focus on building securely through quality attributes, not through adversarial/exploit thinking.
3. **Reduce Material Impact** — Aim to reduce the probability of material impact from cyber events through pragmatic, context-appropriate controls.
4. **Transparency** — Generated and reviewed code should be observable: meaningful naming, structured logging, audit trails.
5. **Trust Boundary Discipline** — Apply strict validation at trust boundaries (the "hard shell"); keep interior logic flexible.

## SSEM Model Quick Reference

| **Maintainability** | **Trustworthiness** | **Reliability** |
|:---------------------|:--------------------:|----------------:|
| Analyzability        | Confidentiality      | Availability    |
| Modifiability        | Accountability       | Integrity       |
| Testability          | Authenticity         | Resilience      |

## Output Formats

- Individual findings: Use the format in `templates/finding.md`
- Full assessment reports: Use the format in `templates/report.md`

## References

- [FIASSE RFC](https://github.com/Xcaciv/securable_software_engineering/blob/main/docs/FIASSE-RFC.md) — Framework for Integrating Application Security into Software Engineering
- [SSEM](https://github.com/Xcaciv/securable_software_engineering) — Securable Software Engineering Model
- License: CC-BY-4.0
