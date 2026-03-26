---
name: prd-securability-enhancement
description: Enhance product requirement documents (PRDs) with FIASSE/SSEM implementation guidance and OWASP ASVS requirement coverage. Use when users ask to improve PRD security requirements, select an ASVS level, map feature requirements to ASVS controls, annotate features with SSEM attributes, and apply FIASSE foundational tenets across each feature.
license: CC-BY-4.0
---

# PRD Securability Enhancement (FIASSE/SSEM + ASVS)

Enhance PRD content so each feature includes explicit securability requirements, implementation notes, and measurable acceptance criteria aligned to ASVS and FIASSE/SSEM.

Follow the complete workflow in `plays/requirements-analysis/prd-fiasse-asvs-enhancement.md`.

## When to Use

- User asks to strengthen a PRD with security requirements
- User asks to choose ASVS level for requirements
- User asks to map PRD features to ASVS requirements
- User asks to annotate feature implementation with FIASSE/SSEM attributes
- Product requirements need securability-by-design before implementation starts

## Steps

1. **Parse PRD Features** — Extract and normalize each feature into testable requirement form.

2. **Choose ASVS Level First** — Select baseline ASVS assurance level (1/2/3) and record rationale.

3. **Map Features to ASVS** — For each feature, identify applicable ASVS sections and requirements from `data/asvs/V*.md`, filtered by chosen level.

4. **Close Requirement Gaps** — Mark coverage as Covered/Partial/Missing/Not Applicable, then add missing requirement statements to feature requirements.

5. **Annotate with SSEM Attributes** — Add implementation notes for all 9 attributes:
   - Maintainability: Analyzability, Modifiability, Testability
   - Trustworthiness: Confidentiality, Accountability, Authenticity
   - Reliability: Availability, Integrity, Resilience

6. **Apply FIASSE Tenets Iteratively** — For each feature, explicitly annotate S2.1, S2.2, S2.3, S2.4, and S2.6.

7. **Emit Enhanced PRD Content** — Produce ASVS level decision, feature-ASVS matrix, updated feature specs, and cross-cutting securability requirements.

## Output

Deliver enhanced PRD sections that include:
- ASVS level selection and rationale
- Per-feature ASVS requirement mapping
- Requirement gap resolutions
- Per-feature SSEM implementation notes (all 9 attributes)
- Per-feature FIASSE tenet annotations (S2.1, S2.2, S2.3, S2.4, S2.6)
- Updated acceptance criteria and NFRs

## References

- `plays/requirements-analysis/prd-fiasse-asvs-enhancement.md`
- `data/asvs/README.md`
- `data/asvs/V*.md`
- `data/fiasse/S2.1.md`
- `data/fiasse/S2.2.md`
- `data/fiasse/S2.3.md`
- `data/fiasse/S2.4.md`
- `data/fiasse/S2.6.md`
- `data/fiasse/S3.2.1.md`
- `data/fiasse/S3.2.2.md`
- `data/fiasse/S3.2.3.md`
