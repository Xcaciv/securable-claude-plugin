# Play: Securable Code Generation (FIASSE/SSEM)

Generate and iteratively improve implementation code using a required five-step securability workflow: requirement enhancement, securable generation, securability review, review-driven enhancement, and report scoring evidence.

This play is the code-generation counterpart to requirements and analysis plays. It ensures code is not produced from raw requirements alone, but from an ASVS-enhanced specification and a measured SSEM improvement loop.

## Trigger Conditions

Use this play when:

- A user asks to generate or refactor code with FIASSE/SSEM quality constraints
- A team wants ASVS-aligned implementation before coding starts
- A user requests end-to-end securable generation with scoring evidence
- Generated code must be reviewed and improved before handoff

## Inputs

- PRD, feature specification, or user story set
- Target language/framework/runtime
- Architecture constraints and trust boundaries (if available)
- Existing codebase context (for refactors)

If no PRD or feature specification exists, create a compact feature specification first, then continue with Step 1.

## Required Workflow (Do Not Reorder)

### Step 1: Enhance Requirements/Specification with ASVS

Use the `prd-securability-enhancement` skill first.

1. Parse PRD/spec features into testable requirements.
2. Select ASVS assurance level and document rationale.
3. Map each feature to applicable ASVS chapters/requirements.
4. Fill coverage gaps with explicit requirement updates.
5. Add compact securability notes and open assumptions.

Required outputs from Step 1:

- Enhanced requirements/specification with ASVS-aligned coverage
- Feature-level securability notes
- Open assumptions and requirement gaps

### Step 2: Generate or Refactor Code

Use the `securability-engineering` skill.

1. Implement from the enhanced requirements produced in Step 1.
2. Apply SSEM constraints across maintainability, trustworthiness, and reliability.
3. Enforce trust-boundary discipline (canonicalize -> sanitize -> validate).
4. Include tests for valid, invalid, boundary, and error paths.

Required outputs from Step 2:

- Implementation code aligned to enhanced requirements
- Test coverage for positive and negative behavior paths
- Brief securability notes for major design decisions

### Step 3: Review Code and Build Enhancement Plan

Use the `securability-engineering-review` skill.

1. Evaluate generated/refactored code against official SSEM scoring.
2. Produce concrete findings with evidence and attribute tagging.
3. Build a prioritized enhancement plan ordered by impact and effort.

Required outputs from Step 3:

- SSEM baseline scores (pillar and overall)
- Actionable findings and recommendations
- Prioritized enhancement plan

### Step 4: Execute Enhancements from Review

Execute the improvement plan from Step 3.

1. Implement high-impact recommendations first.
2. Re-run or re-apply `securability-engineering-review` to validate improvements.
3. Capture score delta by pillar and overall.

Required outputs from Step 4:

- Updated code implementing review-driven improvements
- Post-enhancement scores
- Baseline vs post-enhancement score delta

### Step 5: Save Securability Report Score

Persist the final report to `securability_report.md`.

The report must include:

1. Project/feature scope and evaluation date
2. Baseline SSEM scores by pillar and overall
3. Implemented enhancement summary
4. Post-enhancement SSEM scores by pillar and overall
5. Delta section showing improvements/regressions
6. Final grade and concise next recommendations

## Workflow Guards

- Do not skip Step 1 for code generation/refactor tasks.
- Do not generate implementation code before requirement enhancement is complete.
- Do not skip Step 3 review before applying enhancements.
- Do not finalize output without writing `securability_report.md`.
- If required context is missing, request only the minimum needed inputs.

## Quality Checklist

- [ ] Requirements/spec were ASVS-enhanced before coding
- [ ] Code generated with `securability-engineering` skill constraints
- [ ] Code reviewed with `securability-engineering-review`
- [ ] Enhancements executed based on review findings
- [ ] `securability_report.md` written with baseline and final scores
- [ ] Score delta reported per pillar and overall

## References

- `skills/prd-securability-enhancement/SKILL.md`
- `skills/securability-engineering/SKILL.md`
- `skills/securability-engineering-review/SKILL.md`
- `plays/requirements-analysis/prd-fiasse-asvs-enhancement.md`
- `plays/code-analysis/securability-engineering-review.md`
