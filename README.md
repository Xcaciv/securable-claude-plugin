# securable-claude-plugin

A Claude Code plugin offering secure code generation and securability analysis through application of the OWASP FIASSE: The Securable framework. Also, part of (OWASP Secure Agent Playbook)[https://github.com/OWASP/secure-agent-playbook].

## Overview

This plugin augments Claude Code with three capabilities:

1. **Securability Engineering Review** — Analyze existing code for securable qualities using the nine SSEM attributes across three pillars (Maintainability, Trustworthiness, Reliability), producing scored assessments with actionable findings.
2. **Securability Engineering Code Generation** — Generate new code that embodies securable qualities by default, applying OWASP FIASSE principles as engineering constraints.
3. **PRD Securability Enhancement** — Enhance product requirements documents with ASVS level selection, feature-level ASVS requirement mapping, SSEM implementation annotations, and FIASSE tenet coverage.

## Installation

Add this plugin to your project by cloning it into your workspace or adding it as a git submodule:

```bash
# Clone directly
git clone https://github.com/Xcaciv/securable-claude-plugin.git

# Or as a submodule
git submodule add https://github.com/Xcaciv/securable-claude-plugin.git
```

Then symlink or copy the `.claude/` directory and `CLAUDE.md` file into your project root, or include the plugin directory in your Claude Code workspace.

## Slash Commands

| Command                      | Description                                               |
| ---------------------------- | --------------------------------------------------------- |
| `/securability-review`       | Run a full SSEM securability assessment on code           |
| `/secure-generate`           | Generate code with FIASSE/SSEM constraints applied        |
| `/prd-securability-enhance`  | Enhance PRD features with ASVS + FIASSE/SSEM requirements |
| `/fiasse-lookup`             | Look up FIASSE/SSEM reference material by topic           |

## Example: PRD Enhancement

See the before/after example in:

- `examples/prd-enhancement/input-prd.md`
- `examples/prd-enhancement/enhanced-prd.md`
- `examples/prd-enhancement/README.md`

## SSEM Model

The Securable Software Engineering Model (SSEM) defines nine attributes across three pillars:

| **Maintainability** | **Trustworthiness** | **Reliability** |
| ------------------- | :-----------------: | --------------: |
| Analyzability       |   Confidentiality   |    Availability |
| Modifiability       |    Accountability   |       Integrity |
| Testability         |     Authenticity    |      Resilience |

Each attribute is scored 0–10. Pillar scores are weighted averages. The overall SSEM score is the average of the three pillar scores. See `skills/securability-engineering-review/SKILL.md` for full scoring details.

## Project Structure

```text
CLAUDE.md                          # Plugin entry point — Claude Code reads this first
.claude/
  commands/
    securability-review.md         # /securability-review slash command
    secure-generate.md             # /secure-generate slash command
    prd-securability-enhance.md    # /prd-securability-enhance slash command
    fiasse-lookup.md               # /fiasse-lookup slash command
  settings.json                    # Plugin permissions
.claudeignore                      # Files excluded from context
data/
  fiasse/                          # FIASSE RFC reference sections (S2.x–S8.x)
skills/
  securability-engineering/        # Code generation wrapper skill
  securability-engineering-review/ # Code analysis skill
  prd-securability-enhancement/    # PRD securability enhancement skill
plays/
  code-generation/                # Step-by-step code generation workflows
  code-analysis/                   # Step-by-step analysis procedures
  requirements-analysis/           # Step-by-step PRD enhancement workflows
templates/
  finding.md                       # Individual finding format
  report.md                        # Full assessment report format
template/
  SKILL.md                         # Template for creating new skills
scripts/
  extract_fiasse_sections.py       # Utility to extract sections from FIASSE RFC
examples/
  prd-enhancement/                 # Before/after PRD securability enhancement example
```

## References

- [FIASSE RFC](https://github.com/Xcaciv/securable_software_engineering/blob/main/docs/FIASSE-RFC.md) — Framework for Integrating Application Security into Software Engineering
- [Xcaciv/securable_software_engineering](https://github.com/Xcaciv/securable_software_engineering) — Source repository

## License

CC-BY-4.0 — See [LICENSE](LICENSE)
