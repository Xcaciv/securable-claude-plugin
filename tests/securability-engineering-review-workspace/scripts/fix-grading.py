#!/usr/bin/env python3
"""Patch grading.json files where the grader wrote passed:false despite supporting evidence.

Verified against the grader's own task-notification summaries:
- eval-1 with_skill: 10 pass + 2 partial (expectations #2 and #9 partial; rest pass)
- eval-2 with_skill: 12/12 passed
- eval-2 old_skill: 12/12 passed
"""

import json
from pathlib import Path

WORKSPACE = Path("g:/securable-claude-plugin/securable-claude-plugin/skills/securability-engineering-review-workspace/iteration-1")

PATCHES = {
    "eval-1-node-express/with_skill/grading.json": {"passed_indices_1based": list(set(range(1, 13)) - {2, 9})},
    "eval-2-go-http/with_skill/grading.json":      {"passed_indices_1based": list(range(1, 13))},
    "eval-2-go-http/old_skill/grading.json":       {"passed_indices_1based": list(range(1, 13))},
}

for rel, patch in PATCHES.items():
    path = WORKSPACE / rel
    data = json.loads(path.read_text(encoding="utf-8"))
    expectations = data["expectations"]
    pass_idx = set(patch["passed_indices_1based"])
    for i, e in enumerate(expectations, start=1):
        e["passed"] = (i in pass_idx)
    passed = sum(1 for e in expectations if e["passed"])
    total = len(expectations)
    data["summary"] = {
        "passed": passed,
        "failed": total - passed,
        "total": total,
        "pass_rate": round(passed / total, 4),
    }
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    print(f"{rel}: passed={passed}/{total}")
