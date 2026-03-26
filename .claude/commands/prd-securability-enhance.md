# PRD Securability Enhancement

Enhance a PRD with securability requirements by combining ASVS coverage and FIASSE/SSEM implementation guidance.

Use the full workflow in `plays/requirements-analysis/prd-fiasse-asvs-enhancement.md`.
Use `skills/prd-securability-enhancement/SKILL.md` for trigger conditions and execution sequence.
Reference `data/asvs/` for requirement mapping and `data/fiasse/` for SSEM and tenet guidance.

## Steps

1. **Choose ASVS Level First** — Select a baseline ASVS assurance level (1/2/3) with rationale.

2. **Parse and Normalize Features** — Break the PRD into discrete features and testable requirements.

3. **Map Features to ASVS Requirements** — For each feature, find relevant ASVS sections/requirements and check coverage.

4. **Close Requirement Gaps** — Add explicit missing requirements and clarify partial coverage.

5. **Annotate SSEM Implementation Expectations** — Add feature-level notes for all nine SSEM attributes.

6. **Apply FIASSE Tenets Iteratively** — For each feature, explicitly annotate S2.1, S2.2, S2.3, S2.4, and S2.6.

7. **Produce Enhanced PRD Sections** — Output ASVS decision, coverage matrix, enhanced features, and cross-cutting securability requirements.

## Arguments

- `$ARGUMENTS` — PRD file path, feature list, or requirement scope to enhance.
