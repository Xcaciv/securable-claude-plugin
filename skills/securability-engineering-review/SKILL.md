---
name: securability-engineering-review
description: Perform an SSEM-scored review of a codebase, file, or merge request — producing a 0-10 score per sub-attribute, weighted pillar scores (Maintainability / Trustworthiness / Reliability), an overall grade, evidence-backed strengths and weaknesses, prioritized recommendations, and a 45-item checklist appendix. Use whenever the user asks for a securability assessment, SSEM scorecard, FIASSE/SSEM compliance review, securable-engineering audit, code-quality-for-security review, security posture baseline, or "review this MR through a securable lens" — even when the user does not say "SSEM" explicitly (e.g. "rate how securable this code is", "score this codebase", "where would you start hardening this?", "is this audit-ready?", "give me a security-engineering report on X"). Complementary to vulnerability-centric reviews — focuses on engineering qualities that determine whether code can adapt to evolving threats. For requirements review use prd-securability-enhancement; for new code generation use securability-engineering.
license: CC-BY-4.0
---

# SSEM Evaluation (Scoring and Reporting)

Analyze code for securable engineering qualities and produce a structured SSEM scorecard. This skill is **authoritative** for the scoring rubric and report shape — if other materials in the repo describe older attribute groupings, follow this file.

Source of truth for alignment:
- Official prompt: `https://raw.githubusercontent.com/Securability-Engineering/securable-framework-supplement/refs/heads/main/examples/SSEM-analysis/SSEM-analysis.prompt.md`
- Prompt version 1.0 (December 11, 2025)

The full per-attribute analysis procedure lives in `plays/code-analysis/securability-engineering-review.md`. The rubric and report format below are sufficient for most reviews — consult the play when you need deeper guidance on a specific attribute.

## When to Invoke

Trigger this skill when the user asks to:

- Assess, audit, score, rate, or evaluate the **securability** of code
- Produce an **SSEM scorecard** or SSEM evaluation report
- Review a merge request / pull request through a **securable engineering** lens
- Establish a **security posture baseline** for a project
- Identify **engineering quality** issues that affect security (not vulnerability-centric)
- Answer "where would I start hardening this codebase?"
- Check **FIASSE/SSEM compliance**

Watch for adjacent phrasings: "rate this code for security", "is this audit-ready?", "what's the security health of X?", "how securable is this?", "do a sec-engineering review", "give me a posture report".

## Scoring Framework

Each sub-attribute is scored **0–10**. Pillar scores are weighted sub-attribute averages. The overall SSEM score is the simple average of the three pillar scores.

### Pillar Weights

| Pillar | Pillar Weight | Sub-Attributes (Weight) |
|--------|---------------|-------------------------|
| **Maintainability** | 33% | Analyzability (40%), Modifiability (30%), Testability (30%) |
| **Trustworthiness** | 34% | Confidentiality (30%), Authenticity & Accountability (35%), Integrity (35%) |
| **Reliability** | 33% | Integrity, Operational (30%), Resilience (40%), Availability (30%) |

**Overall SSEM Score** = (Maintainability + Trustworthiness + Reliability) / 3

### Scoring Rubric (Anchor Points)

Use the official anchor points for every sub-attribute:

| Score | Anchor |
|-------|--------|
| **10** | Exemplary implementation |
| **8**  | Strong implementation with minor issues |
| **6**  | Adequate implementation with notable gaps |
| **4**  | Weak implementation with significant issues |
| **2**  | Minimal or poor implementation |

Interpolation between anchors is allowed when justified by evidence, but stay consistent with the rubric language.

### Sub-Attribute Inventory

This rubric scores **9 sub-attributes**, which is a deliberate restructuring of the FIASSE v1.0.4 SSEM model (10 attributes). The rubric **combines** Authenticity and Accountability into one Trustworthiness item and **splits** Integrity into a Trustworthiness item and a separate Reliability "Operational Integrity" item. **Observability** (the 10th SSEM attribute introduced in v1.0.4) is treated as evidence supporting Analyzability and Accountability scores rather than scored separately — flag observability gaps inline in those sub-attributes.

The nine sub-attributes are exactly:

1. **Analyzability** (Maintainability)
2. **Modifiability** (Maintainability)
3. **Testability** (Maintainability)
4. **Confidentiality** (Trustworthiness)
5. **Authenticity & Accountability** (Trustworthiness — *one combined sub-attribute*, scored as a single 0–10 value with weight 35%)
6. **Integrity** (Trustworthiness)
7. **Integrity, Operational** (Reliability — distinct from Trustworthiness Integrity; focused on operational guarantees: validation enforcement, state-transition correctness, idempotency, atomic writes)
8. **Resilience** (Reliability)
9. **Availability** (Reliability)

Every report MUST produce a numeric 0–10 score for each of these nine items, in the breakdown tables and in the appendix. Do not split "Authenticity & Accountability" into two scores; do not collapse "Integrity" and "Integrity (Operational)" into one — they live in different pillars and answer different questions.

### Grading Scale

| Score Range | Grade | Description |
|-------------|-------|-------------|
| 9.0–10.0 | **Excellent** | Exemplary implementation, minimal improvement needed |
| 8.0–8.9 | **Good** | Strong implementation, minor improvements beneficial |
| 7.0–7.9 | **Adequate** | Functional but notable improvement opportunities exist |
| 6.0–6.9 | **Fair** | Basic requirements met, significant improvements needed |
| < 6.0 | **Poor** | Critical deficiencies requiring immediate attention |

## Required Inputs

If the repository or input is incomplete, ask for these before scoring:

- Project name and short description
- Programming language(s) and framework(s)
- Architecture overview (one paragraph is enough)
- Repository URL or codebase access (or pasted code)
- Any existing documentation, test posture, or prior assessments worth incorporating

If essential context is missing, **score conservatively and state the limitation explicitly**. Do not invent coverage, architecture, or operational controls.

## Procedure

1. **Scope & Context** — Capture language, framework, system type, data sensitivity, exposure, lifecycle stage, team context. Without this, scores are guesses.

2. **Inspect the code, not the docs** — Open files. Trace flows. Sample tests. The rubric anchors are about what *is* there, not what is *claimed*.

3. **Maintainability** — Score Analyzability, Modifiability, Testability. For each: cite specific file paths or patterns, not generalities.

4. **Trustworthiness** — Score Confidentiality, Authenticity & Accountability, Integrity. Look for: secrets handling, auth/authz mechanisms, audit logging, input handling at trust boundaries, output encoding, parameterized queries.

5. **Reliability** — Score Integrity (Operational), Resilience, Availability. Look for: error handling specificity, resource management, timeouts, rate limiting, concurrency safety, graceful degradation.

6. **Compute scores** — Sub-attribute → weighted pillar → overall. Show the math.

7. **Assemble the report** — Use the three-part structure below exactly.

## Output Format

The report must contain exactly these three parts in order. Do not skip parts even on small reviews.

### Part 1: SSEM Score Summary

A compact summary block. The exact ASCII shape can flex (Markdown tables are also acceptable when the review is short), but it must include:

- Project name and date
- Overall SSEM score, grade, and a one-line status assessment
- Pillar summary (Maintainability / Trustworthiness / Reliability) — each with score, grade, and a one-line key finding
- Maintainability breakdown table — each sub-attribute with weight, score, and short assessment
- Trustworthiness breakdown table — same shape
- Reliability breakdown table — same shape
- **Top 3 strengths** with concrete evidence (file path, pattern name, or short quote)
- **Top 3 improvement opportunities** with concrete recommendations

### Part 2: Detailed Findings

Per pillar, write:

- Pillar name, score, grade
- **Strengths**: bullets with specific evidence (file:line, pattern, observation)
- **Weaknesses**: bullets with concrete examples or locations and an impact note
- **Recommendations**: numbered list using this shape:
  ```
  1. **[Title]** (Priority: High/Medium/Low)
     - Issue:    [Specific problem]
     - Impact:   [Effect on the pillar score and on the system]
     - Solution: [Actionable steps]
     - Expected Improvement: +[X.X] points
  ```

### Part 3: Appendix A — Evaluation Checklist

The official 45-item checklist, broken down as:

- **Maintainability (15 items)**: Analyzability (5), Modifiability (5), Testability (5)
- **Trustworthiness (15 items)**: Confidentiality (5), Authenticity & Accountability (5), Integrity (5)
- **Reliability (15 items)**: Integrity Operational (5), Resilience (5), Availability (5)

Mark each `[x]` (passing) or `[ ]` (failing) with a brief inline note when failing.

End with a checklist summary:
- Maintainability: N/15 passing (NN%)
- Trustworthiness: N/15 passing (NN%)
- Reliability: N/15 passing (NN%)
- **Overall: N/45 passing (NN%)**

## Worked Example (Mini)

To anchor what "evidence-backed scoring" means in practice, here is a tiny example. Real reports score against substantially more code.

**Snippet under review** (Python, ~12 lines):

```python
@app.post("/notes/{note_id}")
def update_note(note_id, body):
    sql = f"UPDATE notes SET body = '{body}' WHERE id = {note_id}"
    db.execute(sql)
    print("note updated " + note_id)
    return {"ok": True}
```

**Analyzability** — `4/10` (weak). Single-purpose function but uses unsafe string formatting; no input typing; no early returns or guards; the handler conflates I/O, persistence, and response shaping.
*Evidence*: `f"UPDATE notes SET body = '{body}' WHERE id = {note_id}"` mixes parsing, validation, and SQL into one line.

**Integrity** — `2/10` (minimal). SQL injection via string interpolation; no parameterized queries; no auth/ownership check (any caller can update any note ID).
*Evidence*: same line as above; no `current_user` derivation.

**Accountability** — `3/10` (weak). `print(...)` is not structured logging; missing actor, action verb, target ID type-tagged, and outcome.
*Evidence*: `print("note updated " + note_id)`.

**Recommendation (High)** — Replace the f-string with `db.execute("UPDATE notes SET body = $1 WHERE id = $2 AND owner_id = $3", body, note_id, current_user.id)` and emit a structured `note.update` log with `{actor, note_id, outcome}`. Expected improvement: Integrity +5, Accountability +3, Analyzability +2.

This is the level of specificity the report should hit at scale — every score paired with a code-anchored observation, every weakness with a remediation that names the change.

## Pattern Tag Reference

When you find one of these common patterns in code, tag it with the FIASSE/SSEM principle it violates. Specific named tagging is what makes a report actionable — saying "the code mishandles auth" is weak; saying "this is a Derived Integrity violation (FIASSE v1.0.4 S4.4.1.2) — the server's authorization decision rests on a client-asserted JWT claim" is strong.

| Pattern observed in code | Principle / sub-attribute violated | Tag in finding |
|---|---|---|
| Server decides who-can-do-what based on a client-asserted claim (`req.user.email`, `request.body.user_id`, `X-Tenant-ID` header) | Integrity — **Derived Integrity Principle** (FIASSE S4.4.1.2) | "Derived Integrity violation" |
| Spread of `req.body` / `**kwargs` directly into a database update or model field-set | Integrity — **Request Surface Minimization** (FIASSE S4.4.1.1) | "Request Surface Minimization violation; mass assignment" |
| String-built SQL or shell commands; format strings with user input | Integrity — input handling at trust boundary (FIASSE S4.4.1, S4.3) | "Trust boundary input handling" |
| Path joined with user-controlled segment without `..`/separator validation | Integrity — trust boundary; canonicalize → sanitize → validate (FIASSE S4.4.1) | "Path canonicalization gap" |
| `jwt.verify` with no pinned algorithms / no audience / no issuer; or using a default-allow algorithm list | Authenticity (token integrity); Trustworthiness | "Token verification under-specified" |
| `console.log` / `print` / `fmt.Println` standing in for an audit trail; missing actor, target, outcome, request id | Accountability (RFC 4949 traceability); Transparency / Observability (FIASSE S2.5, S3.2.1.4) | "Unstructured audit trail" |
| Bare `except:` / `catch (e)` returning raw exception text to the client | Resilience (graceful degradation); Confidentiality (info leakage) | "Specific exception handling missing" |
| Module-level globals (DB connection, app, config) created at import time | Modifiability (loose coupling) and Testability (mockability) | "Import-time side effects" |
| `ioutil.ReadAll(r.Body)` / unlimited request body buffer | Availability and Resilience (resource limits) | "Unbounded resource consumption" |
| Pervasive `any` typing on the trust-boundary surface (TypeScript / dynamic langs) | Analyzability; Integrity (validation) | "Trust-boundary type erasure" |

You don't need this whole table inline in every report. But when one of these patterns is *present*, the finding should name the principle by tag — not just describe the symptom.

## Anti-Patterns (Things That Make a Report Useless)

- **Fabricated evidence**: don't cite line numbers or function names you didn't actually read. If something is unverified, mark the score as conservative and call out the gap explicitly.
- **All-7s scoring**: if every sub-attribute lands at the same number, you haven't actually evaluated. Some attributes will be stronger than others; the report should reflect that.
- **Vulnerability-centric drift**: this is *not* a CWE pentest report. SSEM scores engineering attributes (analyzability, modifiability, etc.). A finding's value is in the *engineering improvement*, not the exploit recipe.
- **Generic recommendations**: "improve error handling" is not actionable. "Replace bare `except:` at app/handlers.py:42 with `except (ValidationError, NotFound) as e:`" is.
- **Score without code access**: if you can't see the code, say so and refuse to score that pillar — don't extrapolate.
- **Missing the math**: weighted pillar scores must show how they were derived. Don't leave the reader guessing.

## Required Evaluation Criteria

Always:

- Be specific. Reference observable code or architecture evidence by file path or function name.
- Apply the official weights exactly (Maintainability 33%, Trustworthiness 34%, Reliability 33%; sub-weights as in the table).
- Keep recommendations actionable — the reader should be able to open a PR from your text.
- Consider project size, domain, architecture, and intended use when scoring against rubric anchors.
- If evidence is insufficient, score conservatively and **state the limitation in the assessment line for that sub-attribute**.

## Invocation Behavior

When invoked:

1. Ask for missing project information if context is incomplete.
2. Evaluate against the scoring framework above using the procedure.
3. Produce the three-part report exactly as specified.
4. Use repository evidence over assumptions; declare gaps where evidence is missing.

## OWASP & FIASSE References

- [OWASP FIASSE v1.0.4](https://github.com/Xcaciv/securable_software_engineering/blob/v1.0.4/docs/securable_framework.md)
- ISO/IEC 25010:2011 — Software quality models (Maintainability, Reliability)
- RFC 4949 — Internet Security Glossary
- OWASP Code Review Guide
- OWASP ASVS v5.0
- Detailed per-attribute procedure: `plays/code-analysis/securability-engineering-review.md`
