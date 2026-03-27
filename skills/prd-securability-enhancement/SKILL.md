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

5. **Add Compact Securability Notes** — For each feature, write a brief paragraph capturing only the material SSEM and FIASSE considerations that shape implementation.

6. **Emit Enhanced PRD Content** — Produce ASVS level decision, coverage matrix, updated feature specs with securability notes, cross-cutting requirements, and open gaps.

## Output

Deliver a concise enhanced PRD that includes:
- ASVS level selection and rationale
- Feature-ASVS coverage matrix (gap summary)
- Per-feature updated requirements with compact securability notes
- Cross-cutting securability requirements
- Open gaps and assumptions

## References

- `plays/requirements-analysis/prd-fiasse-asvs-enhancement.md`
- `data/asvs/README.md`
- `data/asvs/V*.md`
- `data/fiasse/S*.md`
