#!/usr/bin/env python3
"""
Normalize grading.json files (graders used inconsistent schemas) and aggregate
into benchmark.json compatible with skill-creator's eval-viewer.

Layout:
  <iteration_dir>/
    eval-N-<name>/
      with_skill/
        outputs/enhanced-prd.md
        timing.json
        grading.json
      old_skill/
        outputs/enhanced-prd.md
        timing.json
        grading.json

Normalizes each grading.json in place to:
  {
    "expectations": [{"text": ..., "passed": bool, "evidence": ...}],
    "summary": {"passed": n, "failed": n, "total": n, "pass_rate": 0..1},
    "timing": {...}
  }

Treats grader "partial" as failed (binary), but tracks partial counts in benchmark notes.
"""

import json
import math
import sys
from pathlib import Path
from datetime import datetime, timezone


def normalize_expectation(exp):
    """Coerce one expectation entry to {text, passed, evidence}."""
    text = exp.get("text") or exp.get("expectation") or ""
    evidence = exp.get("evidence") or exp.get("reasoning") or exp.get("notes") or ""

    if "passed" in exp and isinstance(exp["passed"], bool):
        passed = exp["passed"]
        partial = False
    else:
        result = (exp.get("result") or "").lower()
        if result == "pass":
            passed, partial = True, False
        elif result == "partial":
            passed, partial = False, True
        else:
            passed, partial = False, False

    return {"text": text, "passed": passed, "evidence": evidence, "_partial": partial}


def normalize_grading(path):
    data = json.loads(path.read_text(encoding="utf-8"))
    raw = data.get("expectations", [])
    norm = [normalize_expectation(e) for e in raw]

    passed = sum(1 for e in norm if e["passed"])
    partial = sum(1 for e in norm if e["_partial"])
    total = len(norm)
    failed = total - passed
    pass_rate = passed / total if total else 0.0

    out = {
        "expectations": [{"text": e["text"], "passed": e["passed"], "evidence": e["evidence"]} for e in norm],
        "summary": {"passed": passed, "failed": failed, "total": total, "pass_rate": round(pass_rate, 4), "partial": partial},
        "timing": data.get("timing", {}),
    }
    path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


def stats(values):
    if not values:
        return {"mean": 0.0, "stddev": 0.0, "min": 0.0, "max": 0.0}
    n = len(values)
    mean = sum(values) / n
    if n > 1:
        variance = sum((v - mean) ** 2 for v in values) / (n - 1)
        stddev = math.sqrt(variance)
    else:
        stddev = 0.0
    return {"mean": round(mean, 4), "stddev": round(stddev, 4), "min": round(min(values), 4), "max": round(max(values), 4)}


def main(iteration_dir, skill_name):
    iteration = Path(iteration_dir)
    eval_dirs = sorted([d for d in iteration.iterdir() if d.is_dir() and d.name.startswith("eval-")])

    runs_by_config = {}
    runs_flat = []

    for eval_dir in eval_dirs:
        meta_path = eval_dir / "eval_metadata.json"
        meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
        eval_id = meta.get("eval_id", eval_dir.name)
        eval_name = meta.get("eval_name", eval_dir.name)

        for cfg_dir in sorted(eval_dir.iterdir()):
            if not cfg_dir.is_dir():
                continue
            grading_path = cfg_dir / "grading.json"
            if not grading_path.exists():
                continue
            timing_path = cfg_dir / "timing.json"

            normalized = normalize_grading(grading_path)
            timing = normalized.get("timing") or (json.loads(timing_path.read_text(encoding="utf-8")) if timing_path.exists() else {})

            cfg = cfg_dir.name
            run = {
                "eval_id": eval_id,
                "eval_name": eval_name,
                "configuration": cfg,
                "run_number": 1,
                "result": {
                    "pass_rate": normalized["summary"]["pass_rate"],
                    "passed": normalized["summary"]["passed"],
                    "failed": normalized["summary"]["failed"],
                    "total": normalized["summary"]["total"],
                    "partial": normalized["summary"].get("partial", 0),
                    "time_seconds": timing.get("total_duration_seconds", 0.0),
                    "tokens": timing.get("total_tokens", 0),
                    "tool_calls": 0,
                    "errors": 0,
                },
                "expectations": normalized["expectations"],
                "notes": [],
            }
            runs_flat.append(run)
            runs_by_config.setdefault(cfg, []).append(run)

    # Stats per config
    run_summary = {}
    for cfg, items in runs_by_config.items():
        run_summary[cfg] = {
            "pass_rate": stats([r["result"]["pass_rate"] for r in items]),
            "time_seconds": stats([r["result"]["time_seconds"] for r in items]),
            "tokens": stats([r["result"]["tokens"] for r in items]),
        }

    configs = list(runs_by_config.keys())
    if "with_skill" in configs and "old_skill" in configs:
        primary, baseline = "with_skill", "old_skill"
    elif len(configs) >= 2:
        primary, baseline = configs[0], configs[1]
    else:
        primary = configs[0] if configs else None
        baseline = None

    if primary and baseline:
        d_pr = run_summary[primary]["pass_rate"]["mean"] - run_summary[baseline]["pass_rate"]["mean"]
        d_t = run_summary[primary]["time_seconds"]["mean"] - run_summary[baseline]["time_seconds"]["mean"]
        d_tok = run_summary[primary]["tokens"]["mean"] - run_summary[baseline]["tokens"]["mean"]
        run_summary["delta"] = {
            "pass_rate": f"{d_pr:+.2f}",
            "time_seconds": f"{d_t:+.1f}",
            "tokens": f"{d_tok:+.0f}",
        }

    benchmark = {
        "metadata": {
            "skill_name": skill_name,
            "skill_path": "skills/prd-securability-enhancement",
            "executor_model": "claude (subagent)",
            "analyzer_model": "claude (subagent)",
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "evals_run": sorted({r["eval_id"] for r in runs_flat}),
            "runs_per_configuration": 1,
        },
        "runs": runs_flat,
        "run_summary": run_summary,
        "notes": [],
    }

    out_json = iteration / "benchmark.json"
    out_md = iteration / "benchmark.md"
    out_json.write_text(json.dumps(benchmark, indent=2), encoding="utf-8")

    # Markdown summary
    lines = [
        f"# Skill Benchmark: {skill_name}",
        "",
        f"**Date**: {benchmark['metadata']['timestamp']}",
        f"**Evals**: {', '.join(map(str, benchmark['metadata']['evals_run']))} (1 run each per configuration)",
        "",
        "## Summary",
        "",
        "| Metric | with_skill | old_skill | Delta |",
        "|--------|------------|-----------|-------|",
    ]
    if primary and baseline:
        a, b = run_summary[primary], run_summary[baseline]
        d = run_summary["delta"]
        lines.append(f"| Pass Rate | {a['pass_rate']['mean']*100:.0f}% ± {a['pass_rate']['stddev']*100:.0f}% | {b['pass_rate']['mean']*100:.0f}% ± {b['pass_rate']['stddev']*100:.0f}% | {d['pass_rate']} |")
        lines.append(f"| Time      | {a['time_seconds']['mean']:.1f}s | {b['time_seconds']['mean']:.1f}s | {d['time_seconds']}s |")
        lines.append(f"| Tokens    | {a['tokens']['mean']:.0f} | {b['tokens']['mean']:.0f} | {d['tokens']} |")
        lines.append("")
        lines.append("## Per-Eval")
        lines.append("")
        lines.append("| Eval | Config | Passed | Total | Partial | Pass Rate |")
        lines.append("|------|--------|--------|-------|---------|-----------|")
        for r in runs_flat:
            lines.append(f"| {r['eval_name']} | {r['configuration']} | {r['result']['passed']} | {r['result']['total']} | {r['result']['partial']} | {r['result']['pass_rate']*100:.0f}% |")

    out_md.write_text("\n".join(lines), encoding="utf-8")

    print(f"Wrote {out_json}")
    print(f"Wrote {out_md}")
    print()
    print("\n".join(lines))


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "prd-securability-enhancement")
