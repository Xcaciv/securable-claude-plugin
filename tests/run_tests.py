#!/usr/bin/env python3
"""
Run a securable-claude-plugin test workspace using the Claude Code CLI.

Each workspace under tests/ contains:
    evals/
        evals.json              # eval set with prompts, files, assertions
        inputs/                 # any input files referenced by evals
    skill-snapshot/SKILL.md     # the pre-optimization skill version (baseline)
    iteration-N/                # per-iteration outputs (created by this runner)

This runner:

    1. Reads the eval set
    2. For each eval, invokes `claude` (Claude Code CLI) in non-interactive mode
       with a prompt that points at either the live skill or the snapshot
    3. Saves each Claude output to iteration-<N>/eval-<id>-<name>/<config>/outputs/<file>
    4. Records timing + token usage to iteration-<N>/eval-<id>-<name>/<config>/timing.json
    5. Optionally re-runs the LLM-as-judge grader the same way (--grade)

Examples:

    # Run all three workspaces with both configs
    python tests/run_tests.py tests/prd-securability-enhancement-workspace
    python tests/run_tests.py tests/securability-engineering-workspace
    python tests/run_tests.py tests/securability-engineering-review-workspace

    # Run only the new (live) skill, single eval, with grading
    python tests/run_tests.py tests/securability-engineering-workspace \\
        --config with_skill --eval-id 1 --grade

    # Bump iteration counter and run everything fresh
    python tests/run_tests.py tests/securability-engineering-review-workspace \\
        --iteration 2

The Claude Code CLI must be on PATH. Outputs use the same directory layout
as the workspaces produced during the original optimization runs, so the
existing aggregate.py script and skill-creator eval-viewer continue to work.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Per-workspace conventions
# ---------------------------------------------------------------------------
#
# Each workspace produces a different output filename because the skills
# produce different artifact types.

OUTPUT_FILENAMES: dict[str, str] = {
    "prd-securability-enhancement-workspace": "enhanced-prd.md",
    "securability-engineering-workspace": "generated.md",
    "securability-engineering-review-workspace": "report.md",
}

# Map a workspace directory name to the path of the LIVE skill (relative to repo root).
SKILL_PATHS: dict[str, str] = {
    "prd-securability-enhancement-workspace": "skills/prd-securability-enhancement/SKILL.md",
    "securability-engineering-workspace": "skills/securability-engineering/SKILL.md",
    "securability-engineering-review-workspace": "skills/securability-engineering-review/SKILL.md",
}


# ---------------------------------------------------------------------------
# Prompt construction
# ---------------------------------------------------------------------------

EXECUTOR_PROMPT = """You are running a skill evaluation. Read the skill below in full and follow its procedure to perform the user's task.

Skill to follow:
{skill_path}

Plugin root (so the skill's references to data/, plays/, etc. resolve):
{plugin_root}

User task (treat exactly as the user prompt):
{prompt}
{input_section}
Save your final output as a single markdown file to:
{output_path}

Do not write any other files. Do not print the report to stdout. After writing the file, return a one-line confirmation only."""


GRADER_PROMPT = """You are an LLM-as-judge grader. Read the user's task, the produced output, and grade each expectation strictly. Surface compliance does NOT pass — the underlying claim must be substantively supported.

User task:
{prompt}

Output to grade:
{output_path}
{input_section}
Expectations to evaluate (one per line, 1-indexed):
{expectations_block}

Save grading.json to:
{grading_path}

Use this exact JSON schema. Use the Write tool to create the file.

```json
{{
  "expectations": [
    {{"text": "<expectation text>", "passed": true|false, "evidence": "<short quote or paraphrase>"}}
  ],
  "summary": {{"passed": <int>, "failed": <int>, "total": <int>, "pass_rate": <float 0..1>}}
}}
```

Return a one-line confirmation when done. Do NOT return the JSON inline."""


# ---------------------------------------------------------------------------
# Workspace I/O
# ---------------------------------------------------------------------------


def read_evals(workspace: Path) -> dict[str, Any]:
    evals_path = workspace / "evals" / "evals.json"
    return json.loads(evals_path.read_text(encoding="utf-8"))


def output_filename_for(workspace_name: str) -> str:
    if workspace_name in OUTPUT_FILENAMES:
        return OUTPUT_FILENAMES[workspace_name]
    return "output.md"


def skill_path_for(workspace: Path, plugin_root: Path, config: str) -> Path:
    if config == "old_skill":
        return workspace / "skill-snapshot" / "SKILL.md"
    rel = SKILL_PATHS.get(workspace.name)
    if rel is None:
        raise SystemExit(
            f"Unknown workspace {workspace.name!r}; add it to SKILL_PATHS."
        )
    return plugin_root / rel


def slug(name: str) -> str:
    return re.sub(r"[^a-z0-9-]+", "-", name.lower()).strip("-")


def eval_dir(iteration_dir: Path, eval_id: int, name: str) -> Path:
    return iteration_dir / f"eval-{eval_id}-{slug(name)}"


# ---------------------------------------------------------------------------
# Claude CLI invocation
# ---------------------------------------------------------------------------


def find_claude_cli() -> str:
    candidate = shutil.which("claude")
    if candidate:
        return candidate
    raise SystemExit(
        "claude CLI not found on PATH. Install Claude Code or add it to PATH."
    )


def run_claude(prompt: str, *, cwd: Path, claude_cli: str) -> dict[str, Any]:
    """
    Run `claude --print --output-format json` with the given prompt.
    Returns a dict with: stdout, total_tokens, duration_ms.
    """
    start = time.monotonic()
    result = subprocess.run(
        [
            claude_cli,
            "--print",
            "--output-format", "json",
            "--permission-mode", "acceptEdits",
            prompt,
        ],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    duration_ms = int((time.monotonic() - start) * 1000)

    if result.returncode != 0:
        sys.stderr.write(result.stderr or "")
        raise SystemExit(f"claude exited with code {result.returncode}")

    parsed: dict[str, Any] = {}
    try:
        parsed = json.loads(result.stdout)
    except json.JSONDecodeError:
        # Some Claude Code versions print the assistant text directly when
        # --output-format json isn't honored. Fall back to text-only.
        parsed = {"result": result.stdout, "usage": {}}

    return {
        "raw": parsed,
        "result_text": parsed.get("result") or parsed.get("text") or "",
        "total_tokens": (
            parsed.get("usage", {}).get("input_tokens", 0)
            + parsed.get("usage", {}).get("output_tokens", 0)
        ),
        "duration_ms": duration_ms,
    }


# ---------------------------------------------------------------------------
# Eval execution
# ---------------------------------------------------------------------------


def execute_eval(
    eval_entry: dict[str, Any],
    *,
    workspace: Path,
    plugin_root: Path,
    iteration: int,
    config: str,
    output_filename: str,
    claude_cli: str,
) -> Path:
    eval_id = eval_entry["id"]
    name = eval_entry["name"]
    target_dir = eval_dir(workspace / f"iteration-{iteration}", eval_id, name)
    output_path = target_dir / config / "outputs" / output_filename
    output_path.parent.mkdir(parents=True, exist_ok=True)

    skill_path = skill_path_for(workspace, plugin_root, config)
    if not skill_path.exists():
        raise SystemExit(f"Skill not found: {skill_path}")

    files = eval_entry.get("files") or []
    if files:
        rendered = "\n".join(
            f"- {(workspace / f).resolve()}" for f in files
        )
        input_section = (
            "\nInput file(s) referenced by the task (read before producing output):\n"
            + rendered
            + "\n"
        )
    else:
        input_section = ""

    prompt = EXECUTOR_PROMPT.format(
        skill_path=skill_path.resolve(),
        plugin_root=plugin_root.resolve(),
        prompt=eval_entry["prompt"],
        input_section=input_section,
        output_path=output_path.resolve(),
    )

    print(f"  -> exec eval-{eval_id} ({name}) | config={config}", flush=True)
    response = run_claude(prompt, cwd=plugin_root, claude_cli=claude_cli)

    timing_path = target_dir / config / "timing.json"
    timing_path.write_text(
        json.dumps(
            {
                "total_tokens": response["total_tokens"],
                "duration_ms": response["duration_ms"],
                "total_duration_seconds": round(response["duration_ms"] / 1000, 2),
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    if not output_path.exists():
        # Fall back: some Claude Code versions return the artifact in `result`
        # rather than writing it to disk. Persist whatever the model returned.
        output_path.write_text(response["result_text"], encoding="utf-8")
        print(
            f"     [warn] Claude did not write the file directly; saved its "
            f"text response to {output_path.name}",
            flush=True,
        )

    return target_dir / config


def grade_eval(
    eval_entry: dict[str, Any],
    *,
    workspace: Path,
    plugin_root: Path,
    iteration: int,
    config: str,
    output_filename: str,
    claude_cli: str,
) -> Path:
    eval_id = eval_entry["id"]
    name = eval_entry["name"]
    config_dir = eval_dir(workspace / f"iteration-{iteration}", eval_id, name) / config
    output_path = config_dir / "outputs" / output_filename
    grading_path = config_dir / "grading.json"

    if not output_path.exists():
        print(f"     [skip grade] missing output: {output_path}")
        return grading_path

    expectations = eval_entry.get("assertions") or []
    if not expectations:
        print(f"     [skip grade] no assertions for eval-{eval_id}")
        return grading_path

    expectations_block = "\n".join(
        f"{i}. {e.get('text', '').strip()}" for i, e in enumerate(expectations, 1)
    )

    files = eval_entry.get("files") or []
    if files:
        rendered = "\n".join(
            f"- {(workspace / f).resolve()}" for f in files
        )
        input_section = (
            "\nReference input file(s) the executor was given:\n" + rendered + "\n"
        )
    else:
        input_section = ""

    prompt = GRADER_PROMPT.format(
        prompt=eval_entry["prompt"],
        output_path=output_path.resolve(),
        input_section=input_section,
        expectations_block=expectations_block,
        grading_path=grading_path.resolve(),
    )

    print(f"  -> grade eval-{eval_id} ({name}) | config={config}", flush=True)
    run_claude(prompt, cwd=plugin_root, claude_cli=claude_cli)
    return grading_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Run a securable-claude-plugin test workspace via Claude Code CLI."
    )
    p.add_argument("workspace", type=Path, help="Path to a tests/<workspace> directory")
    p.add_argument(
        "--config",
        choices=("with_skill", "old_skill", "both"),
        default="both",
        help="Which skill version to use (default: both)",
    )
    p.add_argument(
        "--iteration",
        type=int,
        default=None,
        help="Iteration number to write to (default: next available)",
    )
    p.add_argument(
        "--eval-id",
        type=int,
        action="append",
        help="Run only the specified eval id(s); may be repeated",
    )
    p.add_argument(
        "--grade",
        action="store_true",
        help="After running executors, run the LLM-as-judge grader",
    )
    p.add_argument(
        "--plugin-root",
        type=Path,
        default=None,
        help="Plugin root path (default: parent of the workspace's parent)",
    )
    return p.parse_args()


def next_iteration(workspace: Path) -> int:
    existing = sorted(
        int(p.name.removeprefix("iteration-"))
        for p in workspace.glob("iteration-*")
        if p.is_dir() and p.name.removeprefix("iteration-").isdigit()
    )
    return (existing[-1] + 1) if existing else 1


def main() -> int:
    args = parse_args()
    workspace: Path = args.workspace.resolve()
    if not workspace.is_dir():
        raise SystemExit(f"Not a directory: {workspace}")

    plugin_root: Path = (args.plugin_root or workspace.parent.parent).resolve()
    iteration = args.iteration or next_iteration(workspace)

    evals = read_evals(workspace)
    eval_entries = evals["evals"]
    if args.eval_id:
        wanted = set(args.eval_id)
        eval_entries = [e for e in eval_entries if e["id"] in wanted]
        if not eval_entries:
            raise SystemExit(f"No evals matched --eval-id {sorted(wanted)}")

    configs = ("with_skill", "old_skill") if args.config == "both" else (args.config,)
    output_filename = output_filename_for(workspace.name)
    claude_cli = find_claude_cli()

    print(
        f"Workspace: {workspace.name}  iteration={iteration}  "
        f"configs={configs}  evals={[e['id'] for e in eval_entries]}"
    )

    for entry in eval_entries:
        for config in configs:
            execute_eval(
                entry,
                workspace=workspace,
                plugin_root=plugin_root,
                iteration=iteration,
                config=config,
                output_filename=output_filename,
                claude_cli=claude_cli,
            )

    if args.grade:
        for entry in eval_entries:
            for config in configs:
                grade_eval(
                    entry,
                    workspace=workspace,
                    plugin_root=plugin_root,
                    iteration=iteration,
                    config=config,
                    output_filename=output_filename,
                    claude_cli=claude_cli,
                )

    print(f"Done. Outputs under: {workspace / f'iteration-{iteration}'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
