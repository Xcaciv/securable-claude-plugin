# Play: PRD Securability Enhancement (FIASSE/SSEM + ASVS)

Enhance a Product Requirements Document (PRD) so each feature is explicitly engineered for securability using FIASSE/SSEM principles and mapped to relevant OWASP ASVS requirements.

This play is requirement-centric (not code-centric): it upgrades feature requirements before implementation so delivery teams build securable capabilities by design.

## Trigger Conditions

Use this play when:

- A user asks to strengthen a PRD with security requirements
- A team needs feature-level ASVS requirement coverage before design or implementation
- Product and engineering want explicit implementation guidance using SSEM attributes
- A user asks to annotate PRD features with FIASSE principles or securability constraints

## Inputs

- PRD document (markdown, text, or structured requirements)
- Target system context (if available): user types, deployment model, data sensitivity, integration boundaries
- Optional risk profile, compliance constraints, or business criticality

## Output

Produce a concise enhanced PRD artifact with these sections:

- ASVS level decision and rationale
- Feature-ASVS coverage matrix (gap summary)
- Per-feature updated requirements with compact securability notes
- Cross-cutting securability requirements
- Open gaps and assumptions

## Procedure

### 1. Establish Scope and Parse Features

1. Parse the PRD into discrete feature entries.
2. For each feature, capture:
   - Feature ID and title
   - User/system actor
   - Data touched
   - Trust boundaries crossed
   - Existing acceptance criteria
3. Normalize feature statements into testable requirement form where needed.

### 2. Choose ASVS Assurance Level First

Select one baseline ASVS level for the PRD before feature mapping.

Decision guide:

- **Level 1**: Low-risk/internal or prototype-like systems with limited sensitive data exposure.
- **Level 2**: Typical production web/API systems with authenticated users and business-critical behavior.
- **Level 3**: High-assurance systems (sensitive data, high-impact operations, elevated attacker interest, or strict regulatory pressure).

Document:

- Chosen level
- Why lower levels are insufficient (if level > 1)
- Any features requiring level escalation beyond baseline

### 3. Process Requirements Feature-by-Feature Against ASVS

Iterate each feature and map it to applicable ASVS chapters and requirements.

For every feature:

1. Use `data/asvs/README.md` chapter index plus `when_to_use` frontmatter in `data/asvs/V*.md`.
2. Identify all relevant ASVS sections (auth, access control, input validation, crypto, logging, etc.).
3. Filter requirements by the selected ASVS level.
4. Compare mapped requirements against current PRD text.
5. Add missing requirement statements to the feature specification.

Record results in a coverage table:

| Feature | ASVS Section | Requirement ID | Level | Coverage | PRD Change Needed                 |
| ------- | ------------ | -------------- | ----- | -------- | --------------------------------- |
| F-01    | V2.1         | 2.1.1          | 2     | Missing  | Add MFA/strong auth requirement   |

Coverage statuses:

- **Covered**: PRD already satisfies intent
- **Partial**: intent partly covered; clarify acceptance criteria
- **Missing**: requirement absent and must be added
- **Not Applicable**: justified with short rationale

### 4. Add Compact Securability Notes Per Feature

For each feature, add a short **Securability Notes** paragraph that captures the most material SSEM and FIASSE considerations in plain language. Do not enumerate all nine SSEM attributes or all five FIASSE tenets individually. Instead, call out only the points that meaningfully shape implementation for that feature.

Consider across SSEM pillars (Maintainability, Trustworthiness, Reliability) and FIASSE tenets (S2.1–S2.6) but surface only what matters:

- Key trust-boundary or data-handling constraints
- Required observability / audit expectations
- Resilience or availability design drivers
- Separation-of-concern or testability mandates

Notation format per feature:

```markdown
### Feature F-01: [Title]

**ASVS Mapping**: Vx.y.z, ...

**Updated Requirements**:
- ...

**Securability Notes**: Brief paragraph covering material SSEM and FIASSE points.
```

### 5. Update Acceptance Criteria and NFRs

For each feature, convert augmentations into explicit acceptance criteria and non-functional requirements:

- Security behavior must be testable
- Logs/audit outputs must be verifiable
- Boundary validation and failure behavior must be defined
- Data handling constraints must be measurable

### 6. Produce Final Enhanced PRD Sections

Produce:

1. **ASVS Level Decision** — brief rationale
2. **Feature-ASVS Coverage Matrix** — gap summary table
3. **Enhanced Feature Specifications** — updated requirements + compact securability notes per feature
4. **Cross-Cutting Securability Requirements** — shared controls
5. **Open Gaps and Assumptions**

## Quality Checklist

- [ ] ASVS level selected before requirement mapping
- [ ] Every feature mapped to applicable ASVS requirements
- [ ] Missing/partial requirements converted into concrete PRD updates
- [ ] Material SSEM and FIASSE considerations captured per feature in compact securability notes
- [ ] Acceptance criteria are testable and unambiguous
- [ ] Trust boundaries and data handling expectations are explicit

## References

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
