Analyze the code in this project (or the specified files/directories) for securable engineering qualities using the FIASSE/SSEM framework.

Follow the full procedure in `plays/code-analysis/securability-engineering-review.md`.
Use the skill definition in `skills/securability-engineering-review/SKILL.md` for scoring weights, grading scale, and severity classification.
Reference `data/fiasse/` sections for attribute definitions and measurement criteria.

## Steps

1. **Scope & Context** — Determine language/framework, system type, data sensitivity, exposure, and trust boundaries for the target code.

2. **SSEM Assessment** — The FIASSE v1.0.4 SSEM model defines 10 attributes; the rubric in `skills/securability-engineering-review/SKILL.md` scores 9 sub-attributes by combining/splitting some, with Observability folded into Analyzability and Accountability evidence:
   - **Maintainability**: Analyzability, Modifiability, Testability (Observability evidence informs Analyzability)
   - **Trustworthiness**: Confidentiality, Authenticity & Accountability, Integrity
   - **Reliability**: Integrity (Operational), Resilience, Availability

3. **Transparency & Observability Assessment** — Evaluate logging, audit trails, code-level instrumentation (FIASSE S2.5 Transparency, S3.2.1.4 Observability), and Least Astonishment in interfaces (S2.6).

4. **Code-Level Threat Identification** — Apply the Four Question Framework: "What can go wrong?" Map solutions to SSEM attributes.

5. **Produce Report** — Generate the full report using `templates/report.md` format, with individual findings using `templates/finding.md` format. Include the SSEM Score Summary, detailed findings per pillar, and the 45-item evaluation checklist.

## Arguments

- `$ARGUMENTS` — Files, directories, or components to analyze. If empty, analyze the entire project.
