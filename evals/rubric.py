"""Rubric runner.

Loads a scenario yaml, grades a generated app directory (and optionally a
transcript) against its rubric. Emits per-check results + aggregate scores.

Usage:
    python -m evals.rubric <scenario.yaml> <generated_app_dir> [--transcript <path>]
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml


AXES = ("stand_up", "config_knowledge", "mcp_usage")


@dataclass
class CheckResult:
    id: str
    desc: str
    kind: str
    passed: bool | None  # None = skipped
    detail: str = ""
    tags: list[str] = field(default_factory=list)
    penalizes: list[str] | None = None  # failure signals only


@dataclass
class CheckContext:
    app_dir: Path
    transcript: list[dict[str, Any]] | None


@dataclass
class ScenarioResult:
    scenario_id: str
    stand_up: list[CheckResult] = field(default_factory=list)
    config_knowledge: list[CheckResult] = field(default_factory=list)
    mcp_usage: list[CheckResult] = field(default_factory=list)
    failure_signals: list[CheckResult] = field(default_factory=list)

    def _axis_checks(self, axis: str) -> list[CheckResult]:
        return getattr(self, axis)

    def _signals_for(self, axis: str) -> list[CheckResult]:
        return [
            s
            for s in self.failure_signals
            if s.passed and axis in (s.penalizes or ["config_knowledge"])
        ]

    def _axis_score(self, axis: str) -> float | None:
        """None when no positive checks are graded — penalties dilute an existing signal, not fabricate one."""
        graded = [c for c in self._axis_checks(axis) if c.passed is not None]
        if not graded:
            return None
        penalties = self._signals_for(axis)
        denom = len(graded) + len(penalties)
        return sum(1 for c in graded if c.passed) / denom

    def _axis_score_raw(self, axis: str) -> float | None:
        graded = [c for c in self._axis_checks(axis) if c.passed is not None]
        if not graded:
            return None
        return sum(1 for c in graded if c.passed) / len(graded)

    @property
    def stand_up_score(self) -> float | None:
        return self._axis_score("stand_up")

    @property
    def config_knowledge_score(self) -> float | None:
        return self._axis_score("config_knowledge")

    @property
    def mcp_usage_score(self) -> float | None:
        return self._axis_score("mcp_usage")

    @property
    def failure_signals_tripped(self) -> list[str]:
        return [c.id for c in self.failure_signals if c.passed]

    def tag_scores(self) -> dict[str, tuple[int, int]]:
        """passed / total per tag, across all axes (signals excluded — they're tripwires, not positive checks)."""
        totals: dict[str, list[int]] = {}
        for axis in AXES:
            for c in self._axis_checks(axis):
                if c.passed is None:
                    continue
                for t in c.tags:
                    bucket = totals.setdefault(t, [0, 0])
                    bucket[1] += 1
                    if c.passed:
                        bucket[0] += 1
        return {t: (p, n) for t, (p, n) in totals.items()}

    def tag_breakdown(self) -> dict[str, dict[str, list[CheckResult]]]:
        """per-tag: {tag: {"checks": [...], "signals": [...]}}.

        `checks` contribute to the tag score; `signals` are tripwires shown for context only.
        """
        breakdown: dict[str, dict[str, list[CheckResult]]] = {}
        for axis in AXES:
            for c in self._axis_checks(axis):
                for t in c.tags:
                    bucket = breakdown.setdefault(t, {"checks": [], "signals": []})
                    bucket["checks"].append(c)
        for s in self.failure_signals:
            for t in s.tags:
                bucket = breakdown.setdefault(t, {"checks": [], "signals": []})
                bucket["signals"].append(s)
        return breakdown


# ---------- check implementations ----------


IGNORE_DIRS = {"node_modules", ".venv", "venv", "__pycache__", ".git", "dist", ".next", "build", ".pytest_cache"}


def _glob(root: Path, pattern: str) -> list[Path]:
    return [
        p for p in root.glob(pattern)
        if not any(part in IGNORE_DIRS for part in p.parts)
    ]


def _check_file_exists(ctx: CheckContext, check: dict[str, Any]) -> CheckResult:
    path = ctx.app_dir / check["path"]
    ok = path.exists()
    return _result(
        check, kind="file_exists", passed=ok,
        detail=str(path.relative_to(ctx.app_dir)) if ok else f"missing: {check['path']}",
    )


def _check_grep(ctx: CheckContext, check: dict[str, Any], *, invert: bool = False) -> CheckResult:
    pattern = re.compile(check["pattern"])
    target = check["in"]
    matches: list[str] = []
    for p in _glob(ctx.app_dir, target):
        if not p.is_file():
            continue
        try:
            text = p.read_text(errors="ignore")
        except OSError:
            continue
        if pattern.search(text):
            matches.append(str(p.relative_to(ctx.app_dir)))
    found = bool(matches)
    passed = (not found) if invert else found
    detail = f"matched in {matches[:3]}" if found else "no match"
    return _result(check, kind="not_grep" if invert else "grep", passed=passed, detail=detail)


def _check_shell(ctx: CheckContext, check: dict[str, Any]) -> CheckResult:
    cmd = check["cmd"]
    timeout = check.get("timeout", 60)
    try:
        result = subprocess.run(
            cmd, shell=True, cwd=ctx.app_dir, capture_output=True, text=True, timeout=timeout
        )
        passed = result.returncode == 0
        detail = (
            f"exit {result.returncode}"
            if passed
            else f"exit {result.returncode}: {result.stderr[-300:]}"
        )
    except subprocess.TimeoutExpired:
        passed = False
        detail = f"timeout after {timeout}s"
    return _result(check, kind="shell", passed=passed, detail=detail)


def _check_judge(ctx: CheckContext, check: dict[str, Any]) -> CheckResult:
    from evals.judge import judge
    paths = check.get("paths") or check.get("path_globs") or ["**/*.ts", "**/*.tsx", "**/*.py", "**/*.js", "**/*.mjs"]
    v = judge(check["prompt"], app_dir=ctx.app_dir, paths=paths)
    return _result(check, kind="judge", passed=v.passed, detail=v.reasoning)


def _tool_uses(transcript: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [e for e in transcript if e.get("type") == "tool_use"]


def _check_tool_used(ctx: CheckContext, check: dict[str, Any], *, invert: bool = False) -> CheckResult:
    if ctx.transcript is None:
        return _result(
            check, kind="tool_not_used" if invert else "tool_used",
            passed=None, detail="skipped (no transcript provided)",
        )
    pattern = re.compile(check["pattern"])
    min_count = check.get("min_count", 1)
    matches = [tu for tu in _tool_uses(ctx.transcript) if pattern.search(tu.get("name", ""))]
    found = len(matches) >= min_count
    passed = (not found) if invert else found
    detail = f"found {len(matches)} call(s): {[m['name'] for m in matches[:3]]}" if matches else "no match"
    return _result(
        check, kind="tool_not_used" if invert else "tool_used",
        passed=passed, detail=detail,
    )


def _check_judge_transcript(ctx: CheckContext, check: dict[str, Any]) -> CheckResult:
    if ctx.transcript is None:
        return _result(
            check, kind="judge_transcript",
            passed=None, detail="skipped (no transcript provided)",
        )
    from evals.judge import judge
    v = judge(check["prompt"], transcript=ctx.transcript)
    return _result(check, kind="judge_transcript", passed=v.passed, detail=v.reasoning)


def _result(check: dict[str, Any], *, kind: str, passed: bool | None, detail: str) -> CheckResult:
    return CheckResult(
        id=check["id"],
        desc=check.get("desc", ""),
        kind=kind,
        passed=passed,
        detail=detail,
        tags=list(check.get("tags", [])),
        penalizes=list(check["penalizes"]) if "penalizes" in check else None,
    )


DISPATCH = {
    "file_exists": _check_file_exists,
    "grep": _check_grep,
    "not_grep": lambda ctx, c: _check_grep(ctx, c, invert=True),
    "shell": _check_shell,
    "judge": _check_judge,
    "tool_used": _check_tool_used,
    "tool_not_used": lambda ctx, c: _check_tool_used(ctx, c, invert=True),
    "judge_transcript": _check_judge_transcript,
}


def run_check(ctx: CheckContext, check: dict[str, Any]) -> CheckResult:
    fn = DISPATCH.get(check["kind"])
    if not fn:
        return _result(check, kind=check["kind"], passed=False, detail=f"unknown kind: {check['kind']}")
    return fn(ctx, check)


# ---------- orchestration ----------


def grade(
    scenario_path: Path,
    app_dir: Path,
    *,
    transcript_path: Path | None = None,
    skip_shell: bool = False,
) -> ScenarioResult:
    scenario = yaml.safe_load(scenario_path.read_text())
    transcript = None
    if transcript_path is not None:
        payload = json.loads(transcript_path.read_text())
        transcript = payload.get("events", [])

    ctx = CheckContext(app_dir=app_dir, transcript=transcript)
    result = ScenarioResult(scenario_id=scenario["id"])

    for axis in AXES:
        checks = scenario.get("rubric", {}).get(axis, [])
        bucket = getattr(result, axis)
        for check in checks:
            if skip_shell and check["kind"] == "shell":
                bucket.append(_result(check, kind="shell", passed=None, detail="skipped (--skip-shell)"))
                continue
            bucket.append(run_check(ctx, check))

    for signal in scenario.get("known_failure_signals", []):
        result.failure_signals.append(run_check(ctx, signal))

    return result


# ---------- rendering ----------


def _mark(passed: bool | None) -> str:
    return "✓" if passed else ("✗" if passed is False else "·")


def format_report(result: ScenarioResult, *, verbose_transcript: list[dict] | None = None) -> str:
    lines: list[str] = []
    lines.append(f"# {result.scenario_id}")
    lines.append("")
    for axis in AXES:
        score = result._axis_score(axis)
        raw = result._axis_score_raw(axis)
        score_s = f"{score:.2f}" if score is not None else "unscored"
        raw_s = f"{raw:.2f}" if raw is not None else "unscored"
        lines.append(f"{axis + '_score:':<28}{score_s:<8}   (raw: {raw_s})")
    lines.append(f"{'failure_signals_tripped:':<28}{result.failure_signals_tripped}")
    tags = result.tag_scores()
    if tags:
        lines.append("")
        lines.append("tag scores:")
        breakdown = result.tag_breakdown()
        for tag, (p, n) in sorted(tags.items()):
            lines.append(f"  {tag:<20} {p}/{n}")
            for c in breakdown.get(tag, {}).get("checks", []):
                if c.passed is None:
                    continue
                lines.append(f"    {_mark(c.passed)} {c.id} — {c.detail or c.desc}")
            for s in breakdown.get(tag, {}).get("signals", []):
                label = "tripped" if s.passed else "clear"
                lines.append(f"    ! {s.id} (signal, {label}) — {s.detail or s.desc}")
    lines.append("")

    for axis in AXES:
        lines.append(f"## {axis}")
        for c in result._axis_checks(axis):
            lines.append(f"  {_mark(c.passed)} [{c.kind}] {c.id} — {c.desc}")
            if c.tags:
                lines.append(f"      tags: {c.tags}")
            if c.detail:
                lines.append(f"      {c.detail}")
        lines.append("")
    lines.append("## failure_signals")
    for c in result.failure_signals:
        pen = c.penalizes or ["config_knowledge"]
        lines.append(f"  {_mark(c.passed)} [{c.kind}] {c.id} — {c.desc}")
        lines.append(f"      penalizes: {pen}")
        if c.tags:
            lines.append(f"      tags: {c.tags}")
        if c.detail:
            lines.append(f"      {c.detail}")
    lines.append("")

    if verbose_transcript is not None:
        lines.append("## transcript (verbose)")
        for e in verbose_transcript:
            t = e.get("type", "?")
            if t == "user":
                lines.append(f"  [user] {_truncate(e.get('text', ''), 400)}")
            elif t == "assistant":
                lines.append(f"  [assistant] {_truncate(e.get('text', ''), 400)}")
            elif t == "tool_use":
                lines.append(f"  [tool_use] {e.get('name')} input={_truncate(json.dumps(e.get('input', {})), 200)}")
            elif t == "tool_result":
                lines.append(f"  [tool_result] {e.get('name')} content={_truncate(str(e.get('content', '')), 200)}")
            else:
                lines.append(f"  [{t}] {e}")
        lines.append("")

    return "\n".join(lines)


def _truncate(s: str, n: int) -> str:
    return s if len(s) <= n else s[: n - 3] + "..."


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("scenario", type=Path)
    parser.add_argument("app_dir", type=Path)
    parser.add_argument("--transcript", type=Path, default=None)
    parser.add_argument("--skip-shell", action="store_true")
    parser.add_argument("--verbose", "-v", action="store_true", help="include transcript in report")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = grade(
        args.scenario,
        args.app_dir,
        transcript_path=args.transcript,
        skip_shell=args.skip_shell,
    )

    if args.json:
        payload = {
            **asdict(result),
            "stand_up_score": result.stand_up_score,
            "config_knowledge_score": result.config_knowledge_score,
            "mcp_usage_score": result.mcp_usage_score,
            "failure_signals_tripped": result.failure_signals_tripped,
            "tag_scores": {t: list(v) for t, v in result.tag_scores().items()},
        }
        print(json.dumps(payload, indent=2))
        return

    verbose_transcript = None
    if args.verbose and args.transcript is not None:
        verbose_transcript = json.loads(args.transcript.read_text()).get("events", [])
    print(format_report(result, verbose_transcript=verbose_transcript))


if __name__ == "__main__":
    main()
