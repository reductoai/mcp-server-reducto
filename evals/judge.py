"""LLM judge for rubric checks that can't be expressed as grep/shell.

Calls the Anthropic API with a forced tool call so we get a deterministic
`{passed: bool, reasoning: str}` verdict.

Skips cleanly (returns (None, "<reason>")) when:
  - ANTHROPIC_API_KEY is unset
  - the anthropic client raises (network, auth, rate limit, etc.)

Intent: judges are *one* vote, not the whole rubric. If a judge is flaky the
whole scorecard shouldn't go red.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

try:
    import anthropic
except ImportError:
    anthropic = None  # type: ignore[assignment]


DEFAULT_MODEL = "claude-sonnet-4-6"
MAX_CONTEXT_CHARS_PER_FILE = 6000
MAX_TOTAL_CONTEXT_CHARS = 40000


@dataclass
class Verdict:
    passed: bool | None  # None = skipped
    reasoning: str


VERDICT_TOOL = {
    "name": "verdict",
    "description": "Return a pass/fail verdict for the rubric check.",
    "input_schema": {
        "type": "object",
        "properties": {
            "passed": {"type": "boolean", "description": "true if the check passes"},
            "reasoning": {"type": "string", "description": "one sentence explanation"},
        },
        "required": ["passed", "reasoning"],
    },
}


SYSTEM_PROMPT = """You are a rubric judge for a reducto-mcp eval set. You answer a
single pass/fail question about the agent's output and return your verdict via
the `verdict` tool.

You may see two sources of evidence:
  1. Generated code files — what the agent ultimately wrote in the app.
  2. Agent transcript — mcp tool calls and assistant text during development.

Use whichever source is relevant to the question asked. Most questions are about
the generated code (what the user will run); some are about agent behavior
(what the agent investigated or verified). The transcript is evidence of what
the agent investigated, not of what the app does — unless the question
specifically asks about investigation/verification behavior.

Be strict but fair. If the evidence is ambiguous, fail. Your reasoning must be
one sentence and cite the specific code or tool-use event that drove your
decision."""


def _collect_files(app_dir: Path, globs: list[str]) -> list[tuple[str, str]]:
    """Collect (relative_path, content) for files matching any glob. Truncates per file."""
    seen: set[Path] = set()
    collected: list[tuple[str, str]] = []
    total = 0
    for g in globs:
        for p in app_dir.glob(g):
            if not p.is_file() or p in seen:
                continue
            seen.add(p)
            try:
                text = p.read_text(errors="ignore")
            except OSError:
                continue
            if len(text) > MAX_CONTEXT_CHARS_PER_FILE:
                text = text[:MAX_CONTEXT_CHARS_PER_FILE] + "\n... <truncated>"
            collected.append((str(p.relative_to(app_dir)), text))
            total += len(text)
            if total > MAX_TOTAL_CONTEXT_CHARS:
                break
        if total > MAX_TOTAL_CONTEXT_CHARS:
            break
    return collected


def _transcript_summary(events: list[dict]) -> str:
    """Compact the transcript into a readable form for judge context."""
    lines: list[str] = []
    for e in events:
        t = e.get("type")
        if t == "user":
            lines.append(f"[user] {e.get('text', '')[:500]}")
        elif t == "assistant":
            txt = e.get("text", "")
            if txt:
                lines.append(f"[assistant] {txt[:500]}")
        elif t == "tool_use":
            inp = json.dumps(e.get("input", {}))[:400]
            lines.append(f"[tool_use] {e.get('name')}({inp})")
        elif t == "tool_result":
            c = str(e.get("content", ""))[:300]
            lines.append(f"[tool_result] {c}")
    return "\n".join(lines)


def _build_message(prompt: str, *, files: list[tuple[str, str]] | None = None,
                   transcript: list[dict] | None = None) -> str:
    parts = [f"Question:\n{prompt}\n"]
    if files:
        parts.append("\nCode context:")
        for rel, content in files:
            parts.append(f"\n--- {rel} ---\n{content}")
    if transcript is not None:
        parts.append("\nAgent transcript (user/assistant text, tool calls, tool results):")
        parts.append(_transcript_summary(transcript))
    parts.append("\nReturn your verdict via the `verdict` tool.")
    return "\n".join(parts)


def _client() -> "anthropic.Anthropic | None":
    if anthropic is None:
        return None
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return None
    return anthropic.Anthropic()


def judge(
    prompt: str,
    *,
    app_dir: Path | None = None,
    paths: list[str] | None = None,
    transcript: list[dict] | None = None,
    model: str = DEFAULT_MODEL,
) -> Verdict:
    """Ask the judge. Returns Verdict(passed=None) on any failure/skip."""
    client = _client()
    if client is None:
        return Verdict(passed=None, reasoning="skipped — ANTHROPIC_API_KEY unset or anthropic sdk missing")

    files: list[tuple[str, str]] = []
    if app_dir is not None and paths:
        files = _collect_files(app_dir, paths)

    try:
        resp = client.messages.create(
            model=model,
            max_tokens=400,
            system=SYSTEM_PROMPT,
            tools=[VERDICT_TOOL],
            tool_choice={"type": "tool", "name": "verdict"},
            messages=[{"role": "user", "content": _build_message(prompt, files=files, transcript=transcript)}],
        )
    except Exception as e:  # broad — any failure skips, doesn't fail the scorecard
        return Verdict(passed=None, reasoning=f"skipped — judge error: {type(e).__name__}: {str(e)[:120]}")

    # pull the tool_use block
    for block in resp.content:
        if getattr(block, "type", None) == "tool_use" and getattr(block, "name", None) == "verdict":
            inp = block.input if isinstance(block.input, dict) else {}
            return Verdict(
                passed=bool(inp.get("passed")),
                reasoning=str(inp.get("reasoning", ""))[:300],
            )

    return Verdict(passed=None, reasoning="skipped — no verdict tool call in response")
