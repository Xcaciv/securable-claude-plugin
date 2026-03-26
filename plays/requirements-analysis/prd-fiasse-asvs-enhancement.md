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

Produce an enhanced PRD artifact with these sections:

- ASVS level decision and rationale
- Feature inventory with ASVS mappings
- Per-feature requirement augmentations (missing controls added)
- Per-feature SSEM implementation notes
- FIASSE tenet annotations applied iteratively across all features
- Gap/assumption list and follow-up actions

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

### 4. Add SSEM Implementation Notation Per Feature

For each feature, annotate implementation guidance across all nine SSEM attributes.

Maintainability:

- **Analyzability**: naming clarity, bounded complexity, explicit trust boundary points
- **Modifiability**: separation of concerns, centralized security controls, low coupling
- **Testability**: test hooks, boundary-condition tests, security control test cases

Trustworthiness:

- **Confidentiality**: data classification, least-privilege access, data minimization
- **Accountability**: auditable events, actor traceability, structured logs
- **Authenticity**: identity proofing, token/session integrity, service identity validation

Reliability:

- **Availability**: timeouts, rate limits, graceful degradation expectations
- **Integrity**: canonicalize/sanitize/validate at boundaries, server-owned state controls
- **Resilience**: defensive error handling, recovery expectations, fault-tolerant behavior

Notation format per feature:

```markdown
### Feature F-01: [Title]

**ASVS Mapping**: Vx.y.z, ...
**SSEM Implementation Notes**:
- Analyzability: ...
- Modifiability: ...
- Testability: ...
- Confidentiality: ...
- Accountability: ...
- Authenticity: ...
- Availability: ...
- Integrity: ...
- Resilience: ...
```

### 5. Iterate FIASSE Foundational Tenets Across Each Feature

Apply each tenet explicitly to each feature, one-by-one.

For every feature, annotate:

1. **S2.1 Securable Paradigm**: how the requirement avoids static "secure" assumptions.
2. **S2.2 Resiliently Add Computing Value**: how value delivery remains robust under change/stress.
3. **S2.3 Reduce Material Impact**: what requirement choices reduce probable business impact.
4. **S2.4 Engineer vs Hacker Mindset**: which scalable engineering controls are mandated.
5. **S2.6 Transparency**: what observability/auditability is required without overexposure.

Use this compact notation:

```markdown
**FIASSE Tenet Annotations**:
- S2.1: ...
- S2.2: ...
- S2.3: ...
- S2.4: ...
- S2.6: ...
```

### 6. Update Acceptance Criteria and NFRs

For each feature, convert augmentations into explicit acceptance criteria and non-functional requirements:

- Security behavior must be testable
- Logs/audit outputs must be verifiable
- Boundary validation and failure behavior must be defined
- Data handling constraints must be measurable

### 7. Produce Final Enhanced PRD Sections

Produce:

1. **ASVS Level Decision** section
2. **Feature-ASVS Coverage Matrix**
3. **Enhanced Feature Specifications** (each with SSEM and FIASSE annotations)
4. **Global Securability Requirements** (cross-cutting concerns)
5. **Open Gaps and Assumptions**

## Quality Checklist

- [ ] ASVS level selected before requirement mapping
- [ ] Every feature mapped to applicable ASVS requirements
- [ ] Missing/partial requirements converted into concrete PRD updates
- [ ] All 9 SSEM attributes addressed per feature
- [ ] All 5 FIASSE tenets (S2.1, S2.2, S2.3, S2.4, S2.6) annotated per feature
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
