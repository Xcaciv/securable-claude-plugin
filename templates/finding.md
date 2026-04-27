# SSEM Finding Template

Use this structure for individual findings produced by the `securability-engineering-review` skill. Findings describe **engineering-attribute deficits**, not exploits. FIASSE v1.0.4 does not borrow CVSS, CWE, or CVE: those belong to assurance tools, not the SSEM rubric.

```markdown
### [SEVERITY] Title: [SSEM Attribute] Deficit

- **SSEM Pillar**: Maintainability | Trustworthiness | Reliability
- **SSEM Attribute**: Analyzability | Modifiability | Testability | Observability | Confidentiality | Accountability | Authenticity | Availability | Integrity | Resilience
- **FIASSE Reference**: FIASSE v1.0.4 S{section} (e.g., FIASSE v1.0.4 S4.4.1.2 for Derived Integrity)
- **Pattern Tag**: From the Pattern Tag Reference in the review skill (e.g., "Derived Integrity violation", "Trust boundary input handling", "Silent failure")
- **Location**: `file_path:line_number` or component / module name
- **Current State**: What the code does today (1-2 sentences)
- **Evidence**: Code snippet, configuration excerpt, or trace observation that demonstrates the deficit
- **Impact**: Effect on the attribute score and on the system's ability to remain securable. Tie back to which SSEM attributes are pulled down and by approximately how much.
- **Remediation**: Specific engineering improvement with a concrete code shape (the reader should be able to open a PR from this text)
- **Expected Improvement**: +[X.X] points on [attribute] (and any cross-attribute lift)
- **Verification**: How to confirm the improvement landed: a test, a log line, a metric, or a re-review checkpoint
- **Confidence**: HIGH | MEDIUM | LOW (how certain is this finding)
```

## Severity Definitions

Severity reflects engineering impact on SSEM scores and on the system's ability to remain securable. Defined in [skills/securability-engineering-review/SKILL.md](../skills/securability-engineering-review/SKILL.md#severity-classification-for-individual-findings).

- **CRITICAL**: A pillar score is held ≤4 because of this finding alone; or an attribute scores ≤2 due to systemic absence (e.g., no input validation anywhere, no audit trail, ambient client-trust). Remediation requires architectural change.
- **HIGH**: A single attribute scores ≤4 due to this finding; or the finding reduces a pillar score by ≥1.5 points. Localized but pervasive.
- **MEDIUM**: Reduces a single attribute by ~1 point; specific module or pattern. Remediation contained to one module.
- **LOW**: Localized engineering improvement; ≤0.5 score impact.
- **INFO**: Best-practice observation; no measurable score impact.

## Confidence Levels

- **HIGH**: Confirmed via direct code inspection of the cited `file:line`, with full context understood.
- **MEDIUM**: Strong indicators from code inspection, but some context unverified (e.g., upstream caller, runtime configuration): flag for manual verification.
- **LOW**: Heuristic match; pattern recognized but full context not inspected. May be false positive.

## Authoring Guidance

- **Anchor every finding in code**: a finding without a `file_path:line_number` (or named component) is a recommendation, not a finding.
- **Name the principle**: use a tag from the Pattern Tag Reference. "The auth is sketchy" is not a finding; "Derived Integrity violation (FIASSE v1.0.4 S4.4.1.2): authorization decision rests on a client-asserted JWT claim at `api/orders.py:84`" is.
- **Quantify expected improvement**: readers prioritize by score lift, not by prose.
- **Verification must be concrete**: "review again in 6 months" is not verification. "After fix: structured log `note.update` with `actor` and `outcome` appears for every PUT to `/notes/{id}`; the existing test `test_audit_emits_actor` passes" is.
