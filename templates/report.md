# SSEM Assessment Report Template

Use this scaffold to assemble the three-part output of the `securability-engineering-review` skill, or the baseline / delta / post-enhancement report from the end-to-end securable generation play.

The skill at [skills/securability-engineering-review/SKILL.md](../skills/securability-engineering-review/SKILL.md) is the source of truth for the rubric (FIASSE v1.0.4 — 10 attributes, equal pillar weights), severity classification, and 50-item checklist. This template only supplies the structural shape.

```markdown
# SSEM Assessment Report — [Project Name]

**Date**: YYYY-MM-DD
**Scope**: [What was assessed — repo / service / module / merge request / changeset]
**Language / Framework**: [...]
**Exposure**: [internet-facing | internal | local-only]
**Lifecycle Stage**: [new | mature | legacy]
**Sampling Discipline**: [comprehensive | sampled — list the file paths actually inspected; declare un-sampled areas, which are capped at 6]

---

## Part 1 — SSEM Score Summary

### Overall

- **SSEM Score**: [X.X] / 10
- **Grade**: Excellent | Good | Adequate | Fair | Poor
- **Status**: [one-line assessment]

### Pillar Summary

| Pillar | Score | Grade | Key Finding |
| --- | --- | --- | --- |
| Maintainability | [X.X] / 10 | [Grade] | [one-line key finding] |
| Trustworthiness | [X.X] / 10 | [Grade] | [one-line key finding] |
| Reliability | [X.X] / 10 | [Grade] | [one-line key finding] |

### Maintainability Breakdown

| Attribute | Weight | Score | Assessment |
| --- | --- | --- | --- |
| Analyzability (FIASSE v1.0.4 S3.2.1.1) | 25% | [X]/10 | [brief] |
| Modifiability (FIASSE v1.0.4 S3.2.1.2) | 25% | [X]/10 | [brief] |
| Testability (FIASSE v1.0.4 S3.2.1.3) | 25% | [X]/10 | [brief] |
| Observability (FIASSE v1.0.4 S3.2.1.4) | 25% | [X]/10 | [brief] |
| **Pillar score** | 100% | **[X.X]** | simple average |

### Trustworthiness Breakdown

| Attribute | Weight | Score | Assessment |
| --- | --- | --- | --- |
| Confidentiality (FIASSE v1.0.4 S3.2.2.1) | 33.3% | [X]/10 | [brief] |
| Accountability (FIASSE v1.0.4 S3.2.2.2) | 33.3% | [X]/10 | [brief] |
| Authenticity (FIASSE v1.0.4 S3.2.2.3) | 33.3% | [X]/10 | [brief] |
| **Pillar score** | 100% | **[X.X]** | simple average |

### Reliability Breakdown

| Attribute | Weight | Score | Assessment |
| --- | --- | --- | --- |
| Availability (FIASSE v1.0.4 S3.2.3.1) | 33.3% | [X]/10 | [brief] |
| Integrity (FIASSE v1.0.4 S3.2.3.2) | 33.3% | [X]/10 | [brief] |
| Resilience (FIASSE v1.0.4 S3.2.3.3) | 33.3% | [X]/10 | [brief] |
| **Pillar score** | 100% | **[X.X]** | simple average |

### Top 3 Strengths

1. [Strength with concrete evidence — file path, pattern name, or short quote]
2. [Strength with concrete evidence]
3. [Strength with concrete evidence]

### Top 3 Improvement Opportunities

1. [Weakness + concrete recommendation]
2. [Weakness + concrete recommendation]
3. [Weakness + concrete recommendation]

---

## Part 2 — Detailed Findings

### Maintainability — [X.X]/10 ([Grade])

**Strengths**
- [Specific strength with file:line or pattern]
- [Another strength]

**Weaknesses**
- [Specific weakness with location and impact note]
- [Another weakness]

**Recommendations**

1. **[Title]** (Severity: CRITICAL | HIGH | MEDIUM | LOW | INFO)
   - Issue: [Specific problem]
   - Impact: [Effect on pillar score and on the system]
   - Solution: [Actionable steps]
   - Expected Improvement: +[X.X] points

[Add additional recommendations as needed.]

### Trustworthiness — [X.X]/10 ([Grade])

[Same shape as Maintainability above.]

### Reliability — [X.X]/10 ([Grade])

[Same shape as Maintainability above.]

### Individual Findings

For each finding, use the format defined in [finding.md](finding.md). Findings name the SSEM pillar and attribute, the FIASSE v1.0.4 reference, the pattern tag, location, current state, evidence, impact, remediation, expected improvement, verification, and confidence.

---

## Part 3 — Appendix A: Evaluation Checklist (50 items)

Mark each `[x]` (passing) or `[ ]` (failing) with a brief inline note when failing.

### Maintainability (20 items)

**Analyzability**
- [ ] Methods under 30 lines
- [ ] Cyclomatic complexity < 10
- [ ] Clear, descriptive naming
- [ ] Self-documenting code; comments only at trust boundaries / complex logic
- [ ] No dead code or commented-out blocks

**Modifiability**
- [ ] Loose coupling with clear interfaces
- [ ] No static mutable state
- [ ] Security-sensitive logic centralized (auth, crypto, validation)
- [ ] Configuration externalized
- [ ] Dependency injection (or equivalent) enables component replacement

**Testability**
- [ ] Security controls have dedicated test suites
- [ ] Negative / boundary / malicious-input cases covered
- [ ] Tests run without external dependencies (clean mocking)
- [ ] Test execution fast enough for every commit
- [ ] Integration tests cover trust-boundary crossings

**Observability**
- [ ] Structured logs include who, what, where, when, outcome at security-relevant events
- [ ] Failure paths produce log/metric output (no silent failures)
- [ ] Code-level instrumentation at trust boundaries (not external tooling alone)
- [ ] Health and performance metrics exposed via standardized API
- [ ] UI/operator feedback surfaces meaningful state without leaking internals

### Trustworthiness (15 items)

**Confidentiality**
- [ ] Sensitive data types identified and classified
- [ ] Least-privilege data access
- [ ] Encryption at rest for sensitive data
- [ ] Encryption in transit enforced
- [ ] No secrets / PII / tokens in code, logs, or error messages

**Accountability**
- [ ] Security-sensitive actions logged with structured data (who/what/where/when)
- [ ] Audit trails immutable or append-only
- [ ] Authentication events recorded (login, logout, failure)
- [ ] Authorization decisions logged (grant, deny)
- [ ] Permission / config changes captured with actor and outcome

**Authenticity**
- [ ] Authentication uses established, strong mechanisms (MFA where appropriate)
- [ ] Token / session integrity verified (signed JWTs with pinned alg, secure cookies)
- [ ] Service-to-service calls mutually authenticated
- [ ] Data origin verifiable where applicable (signatures, checksums)
- [ ] Non-repudiation supported for security-sensitive actions

### Reliability (15 items)

**Availability**
- [ ] Resource limits enforced (memory, connections, file handles)
- [ ] Timeouts configured for all external calls
- [ ] Rate limiting protects against resource exhaustion
- [ ] Thread-safe design where concurrency is used
- [ ] Graceful degradation for non-critical failures

**Integrity**
- [ ] Input canonicalized → sanitized → validated at every trust boundary (FIASSE v1.0.4 S4.4.1)
- [ ] Output-encoded when crossing trust boundaries
- [ ] Database operations use parameterized queries exclusively
- [ ] Derived Integrity applied — server-owned state never client-supplied (FIASSE v1.0.4 S4.4.1.2)
- [ ] Request Surface Minimization applied — only expected named values extracted (FIASSE v1.0.4 S4.4.1.1)

**Resilience**
- [ ] Specific exception handling (no bare catch-all) with meaningful messages
- [ ] Defensive coding anticipates out-of-bounds input
- [ ] Null checks sandboxed to input / DB boundaries
- [ ] No resource leaks; deterministic disposal patterns (`with`, `using`, RAII)
- [ ] Graceful and **secure** failure — error messages do not leak internals

### Checklist Summary

- Maintainability: N/20 passing (NN%)
- Trustworthiness: N/15 passing (NN%)
- Reliability: N/15 passing (NN%)
- **Overall: N/50 passing (NN%)**

### Severity Summary

- CRITICAL: N
- HIGH: N
- MEDIUM: N
- LOW: N
- INFO: N
```

## Optional: Baseline / Delta / Post-Enhancement Sections

When this report is the artifact of the end-to-end securable generation play (see [plays/code-generation/securable-generation.md](../plays/code-generation/securable-generation.md)), append:

```markdown
## Baseline vs Post-Enhancement

| Attribute | Baseline | Post-Enhancement | Δ |
| --- | --- | --- | --- |
| Analyzability | [X.X] | [X.X] | [+/-X.X] |
| Modifiability | [X.X] | [X.X] | [+/-X.X] |
| Testability | [X.X] | [X.X] | [+/-X.X] |
| Observability | [X.X] | [X.X] | [+/-X.X] |
| Confidentiality | [X.X] | [X.X] | [+/-X.X] |
| Accountability | [X.X] | [X.X] | [+/-X.X] |
| Authenticity | [X.X] | [X.X] | [+/-X.X] |
| Availability | [X.X] | [X.X] | [+/-X.X] |
| Integrity | [X.X] | [X.X] | [+/-X.X] |
| Resilience | [X.X] | [X.X] | [+/-X.X] |
| **Maintainability pillar** | [X.X] | [X.X] | [+/-X.X] |
| **Trustworthiness pillar** | [X.X] | [X.X] | [+/-X.X] |
| **Reliability pillar** | [X.X] | [X.X] | [+/-X.X] |
| **Overall** | **[X.X]** | **[X.X]** | **[+/-X.X]** |

## Implemented Enhancements

1. [Enhancement applied — file paths touched and pattern tag addressed]
2. [...]

## Residual Findings

For findings *not* fixed within the iteration cap, list them with severity, attribute, location, and an effort estimate so the team can plan follow-up.

## Next Recommendations

[Concise, prioritized list of next steps.]
```

## Notes

- Severity is engineering-impact based; defined in [skills/securability-engineering-review/SKILL.md](../skills/securability-engineering-review/SKILL.md). Do not import CVSS, CWE, or CVE — those are assurance-tool concepts and are out of scope for an SSEM report.
- Sampling discipline is the report's credibility floor. Declare what was inspected; cap un-sampled scores at 6.
- Pillar arithmetic must be visible. Pillar score = simple average of attribute scores; overall = simple average of pillar scores.
