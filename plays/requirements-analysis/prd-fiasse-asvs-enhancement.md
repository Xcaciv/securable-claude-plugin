# Play: PRD Securability Enhancement (FIASSE v1.0.4 / SSEM + ASVS)

Step-by-step runbook for upgrading a PRD with explicit ASVS coverage and FIASSE v1.0.4 SSEM implementation guidance — *before* code is written.

> **Source of truth**: [skills/prd-securability-enhancement/SKILL.md](../../skills/prd-securability-enhancement/SKILL.md) defines the level rubric, ASVS coverage gap pattern table, output templates, and quality checklist. This play sequences the work — it does not redefine the rubric or templates.

## Trigger Conditions

Run this play when:

- A user asks to strengthen a PRD with security requirements
- A team needs feature-level ASVS requirement coverage before design or implementation
- Product and engineering want explicit implementation guidance using SSEM attributes
- A user asks to annotate PRD features with FIASSE principles or securability constraints

## Inputs

- PRD document (markdown, text, or structured requirements)
- Target system context (if available): user types, deployment model, data sensitivity, integration boundaries
- Optional risk profile, compliance constraints, business criticality
- ASVS-level preference, if any

## Steps

### 1. Parse features

Extract each feature into a normalized record. For each, capture:

- Feature ID and title (assign `F-NN` if absent)
- Actor (user role, system, external service)
- Data touched and sensitivity class
- Trust boundaries crossed
- Existing acceptance criteria, verbatim

Split lumped capabilities into independently testable features.

### 2. Choose ASVS level *first*

Use the level rubric in the skill (1 = internal/prototype, 2 = production default, 3 = high-assurance). Default to Level 2 unless evidence pushes lower or higher.

Document chosen level, why lower levels are insufficient, and any feature-level escalations.

### 3. Map each feature to ASVS

For every feature, identify applicable chapters from `data/asvs/README.md` and the `when_to_use` frontmatter in `data/asvs/V*.md`. Filter requirements by the chosen level. Classify each requirement as **Covered**, **Partial**, **Missing**, or **N/A** (with rationale).

Apply the **ASVS Coverage Gap Pattern Table** in the skill — it surfaces the requirements PRDs reliably miss for common feature shapes (login, password reset, file upload, profile edit, role-based access, public API, webhook, export, LLM-backed features, etc.). When a feature trips a pattern, prefill the named requirements as **Missing** unless the PRD explicitly addresses them.

### 4. Add Securability Notes per feature

Write a short paragraph surfacing only the SSEM and FIASSE points that materially shape implementation. Do not enumerate all attributes.

Useful lenses (mention only when relevant):

- Trust-boundary handling and input canonicalization (FIASSE v1.0.4 S4.3, S4.4.1)
- Derived Integrity (FIASSE v1.0.4 S4.4.1.2)
- Request Surface Minimization (FIASSE v1.0.4 S4.4.1.1)
- Observability and audit expectations (FIASSE v1.0.4 S3.2.1.4 + S2.5)
- Least Astonishment (FIASSE v1.0.4 S2.6)
- Resilience / availability drivers
- Testability or modifiability mandates (centralizing crypto/auth)
- Dependency stewardship (FIASSE v1.0.4 S4.6)

### 5. Convert into testable acceptance criteria

For each added or strengthened requirement, write at least one acceptance criterion that is:

- Behaviorally observable
- Specific about boundary conditions (failure modes, unauthorized actors, malformed input)
- Tied to a verifiable artifact (log line, response code, denied action)

Reject ambiguous "secure" or "robust" language.

### 6. Emit the enhanced PRD artifact

Produce these sections, using the exact templates in the skill:

1. **ASVS Level Decision**
2. **Feature ↔ ASVS Coverage Matrix**
3. **Enhanced Feature Specifications** (per-feature: Actor / Data / Trust Boundaries / ASVS Mapping / Updated Requirements / Acceptance Criteria / Securability Notes)
4. **Cross-Cutting Securability Requirements**
5. **Open Gaps and Assumptions**

## Quality Gates

- [ ] ASVS level selected and justified before requirement mapping
- [ ] Every feature mapped to all applicable ASVS chapters at the chosen level
- [ ] Gap-pattern table applied to every relevant feature
- [ ] Missing/partial requirements converted into concrete PRD updates
- [ ] Material SSEM/FIASSE points captured per feature in compact notes
- [ ] Acceptance criteria are behaviorally testable and unambiguous
- [ ] Trust boundaries and data handling expectations are explicit
- [ ] Open gaps and assumptions listed

## References

- [skills/prd-securability-enhancement/SKILL.md](../../skills/prd-securability-enhancement/SKILL.md) — level rubric, ASVS gap pattern table, output templates, quality checklist
- `data/asvs/README.md`
- `data/asvs/V*.md`
- `data/fiasse/S2.1.md`–`S2.6.md` — FIASSE v1.0.4 foundational principles (incl. Transparency S2.5, Least Astonishment S2.6)
- `data/fiasse/S3.2.1.md`–`S3.2.3.md` — SSEM attribute umbrellas (incl. `S3.2.1.4.md` Observability)
- `data/fiasse/S4.3.md`, `S4.4.md`, `S4.4.1.md`, `S4.4.1.1.md`, `S4.4.1.2.md` — Boundary Control, Resilient Coding, Canonical Input Handling
- `data/fiasse/S4.5.md`, `S4.6.md` — Dependency Management & Stewardship
