# PRD Securability Enhancement

Enhance a PRD with securability requirements by combining ASVS coverage and FIASSE/SSEM implementation guidance.

Use the full workflow in `plays/requirements-analysis/prd-fiasse-asvs-enhancement.md`.
Use `skills/prd-securability-enhancement/SKILL.md` for trigger conditions and execution sequence.
Use the built-in ASVS catalog for requirement mapping and `data/fiasse/` for SSEM and tenet guidance.

## Steps

1. **Choose ASVS Level First** — Select a baseline ASVS assurance level (1/2/3) with rationale.

2. **Parse and Normalize Features** — Break the PRD into discrete features and testable requirements.

3. **Map Features to ASVS Requirements** — For each feature, find relevant ASVS sections/requirements and check coverage.

4. **Close Requirement Gaps** — Add explicit missing requirements and clarify partial coverage.

5. **Add Compact Securability Notes** — Write a brief paragraph per feature covering only the material SSEM and FIASSE points.

6. **Produce Enhanced PRD Sections** — Output ASVS decision, coverage matrix (gap summary), enhanced features with securability notes, cross-cutting requirements, and open gaps.

## Arguments

- `$ARGUMENTS` — PRD file path, feature list, or requirement scope to enhance.
