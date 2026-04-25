---
name: securability-engineering-review
description: Analyze a software project using the official SSEM scoring and reporting model. Use when assessing code securability, producing an SSEM scorecard, generating a structured SSEM evaluation report, reviewing merge requests through a securable engineering lens, or establishing a security posture baseline. Complements vulnerability-centric reviews by focusing on whether code is engineered to remain understandable, modifiable, trustworthy, and reliable over time.
license: CC-BY-4.0
---

# SSEM Evaluation (Scoring and Reporting)

Analyze code for securable engineering qualities by following the workflow in `plays/code-analysis/securability-engineering-review.md`.

For scoring and reporting, this skill is authoritative. If other repository materials use older FIASSE/SSEM attribute groupings or different report shapes, follow the official prompt-aligned model in this file.

Source of truth for alignment:
- Official prompt: `https://raw.githubusercontent.com/Securability-Engineering/securable-framework-supplement/refs/heads/main/examples/SSEM-analysis/SSEM-analysis.prompt.md`
- Prompt version: 1.0
- Prompt date: December 11, 2025

## Scoring Framework

Each sub-attribute is scored **0-10**. Pillar scores are calculated using weighted sub-attribute scores. The overall SSEM score is the simple average of the three pillar scores.

Use the official scoring taxonomy below even if local FIASSE materials describe the attributes differently.

### Pillar Weights

| Pillar | Weight | Sub-Attributes (Weight) |
|--------|--------|------------------------|
| **Maintainability** | 33% | Analyzability (40%), Modifiability (30%), Testability (30%) |
| **Trustworthiness** | 34% | Confidentiality (30%), Authenticity & Accountability (35%), Integrity (35%) |
| **Reliability** | 33% | Integrity (Operational) (30%), Resilience (40%), Availability (30%) |

**Overall SSEM Score** = (Maintainability + Trustworthiness + Reliability) / 3

### Scoring Rubric Use

Use the official anchor points from the prompt for each sub-attribute:
- **10**: exemplary implementation
- **8**: strong implementation with minor issues
- **6**: adequate implementation with notable gaps
- **4**: weak implementation with significant issues
- **2**: minimal or poor implementation

Interpolation between anchor points is allowed when justified by evidence, but scoring must remain consistent with the official rubric language.

### Grading Scale

| Score Range | Grade | Description |
|-------------|-------|-------------|
| 9.0 - 10.0 | **Excellent** | Exemplary implementation, minimal improvement needed |
| 8.0 - 8.9 | **Good** | Strong implementation, minor improvements beneficial |
| 7.0 - 7.9 | **Adequate** | Functional but notable improvement opportunities exist |
| 6.0 - 6.9 | **Fair** | Basic requirements met, significant improvements needed |
| < 6.0 | **Poor** | Critical deficiencies requiring immediate attention |

## Required Inputs

If the repository context is incomplete, ask the user for the following before scoring:
- Project name and short description
- Programming language(s) and framework(s)
- Architecture overview
- Repository URL or codebase access
- Existing documentation, test results, or prior security assessments

## Steps

1. **Gather Project Information** — Request missing project metadata and context before scoring when necessary.

2. **Scope & Context** — Establish language/framework, system type, data sensitivity, exposure, lifecycle stage, and team context.

3. **Evaluate Maintainability**:
   - **Analyzability** — Volume, duplication, unit size, cyclomatic complexity, comment density, time-to-understand
   - **Modifiability** — Module coupling, change impact size, regression rate, centralized security code
   - **Testability** — Code coverage, unit test density, mocking complexity, component independence

4. **Evaluate Trustworthiness**:
   - **Confidentiality** — Data protection, secrets management, encryption, access control
   - **Authenticity & Accountability** — Authentication, authorization, audit logging, traceability
   - **Integrity** — Input validation, output encoding, cryptographic verification, tamper detection

5. **Evaluate Reliability**:
   - **Integrity (Operational)** — Input validation, error propagation, consistency, state management
   - **Resilience** — Exception handling, graceful degradation, error recovery, resource management
   - **Availability** — Thread safety, deadlock prevention, performance, scalability

6. **Document Evidence** — Reference actual code patterns, files, architecture choices, test posture, and operational safeguards.

7. **Calculate Scores**:
   - Score each sub-attribute 0-10
   - Calculate each weighted pillar score
   - Calculate the overall SSEM score as the average of the three pillar scores
   - Assign the overall grade using the grading scale above

8. **Produce the Official Report** — Output the report using the required three-part structure below.

## Output Requirements

The report must contain exactly these three parts.

### Part 1: SSEM Score Summary

Use an ASCII report block that includes:
- Project name and date
- Overall SSEM score, grade, and brief status assessment
- Pillar summary table with Maintainability, Trustworthiness, and Reliability
- Maintainability breakdown table with weights, scores, and short assessments
- Trustworthiness breakdown table with weights, scores, and short assessments
- Reliability breakdown table with weights, scores, and short assessments
- Top strengths section with three concrete strengths
- Top improvement opportunities section with three concrete weaknesses/recommendations

### Part 2: Detailed Findings

For each pillar, provide:
- Pillar name, score, and grade
- **Strengths** with specific evidence or observed patterns
- **Weaknesses** with concrete examples, locations, or architecture impacts
- **Recommendations** using this structure:

1. **[Recommendation Title]** (Priority: High/Medium/Low)
   - **Issue:** specific problem
   - **Impact:** effect on pillar score
   - **Solution:** actionable remediation steps
   - **Expected Improvement:** +[X.X] points

### Part 3: Appendix A - Evaluation Checklist

Include the official 45-item checklist with checkbox markers and a pass-rate summary.

The checklist must cover:
- Maintainability: 15 items total
  - Analyzability: 5 items
  - Modifiability: 5 items
  - Testability: 5 items
- Trustworthiness: 15 items total
  - Confidentiality: 5 items
  - Authenticity & Accountability: 5 items
  - Integrity: 5 items
- Reliability: 15 items total
  - Integrity (Operational): 5 items
  - Resilience: 5 items
  - Availability: 5 items

Include a checklist summary with:
- Maintainability pass count and percentage
- Trustworthiness pass count and percentage
- Reliability pass count and percentage
- Overall pass count and percentage

## Required Evaluation Criteria

Always:
- Be specific and reference observable code or architecture evidence
- Support scores with concrete examples
- Keep recommendations actionable and implementation-oriented
- Consider project size, domain, architecture, and intended use
- Apply the official weights exactly
- Avoid inventing coverage, architecture, or operational controls when evidence is missing

If evidence is insufficient, state the limitation explicitly and score conservatively.

## OWASP & FIASSE References

- [OWASP FIASSE](https://github.com/Xcaciv/securable_software_engineering/blob/main/docs/secureable_framework.md) — Framework for Integrating Application Security into Software Engineering
- ISO/IEC 25010:2011 — Software quality models (Maintainability, Reliability definitions)
- RFC 4949 — Internet Security Glossary (Trustworthiness, Integrity, Availability definitions)
- OWASP Code Review Guide
- OWASP ASVS v5.0

## Invocation Behavior

When invoked:
- Ask for missing project information if the repository context is incomplete
- Evaluate the codebase against the official scoring model in this file
- Produce the report in the required three-part format
- Use repository evidence over assumptions
