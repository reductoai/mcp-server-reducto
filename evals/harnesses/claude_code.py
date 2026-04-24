"""Claude Code harness.

Drives the `claude` CLI in `--bare --print --output-format stream-json` mode,
wiring the reducto mcp in via --mcp-config --strict-mcp-config so each run
sees only that mcp (no user-level mcp config bleeds in).

Produces:
  - a canonical transcript.json (events list: user/assistant/tool_use/tool_result)
  - the working directory (where the agent did its edits)
  - metadata (session id, model, exit code, cost)

v0.1 scope: single-shot. Multi-turn will switch --input-format to stream-json
and pipe follow-up user messages from the simulator.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Literal

ClaudeModel = Literal["opus", "sonnet"] | str


# path to the mcp-server-reducto checkout (repo root)
REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class HarnessResult:
    session_id: str
    model: str
    working_dir: Path
    transcript: list[dict[str, Any]] = field(default_factory=list)
    raw_events: list[dict[str, Any]] = field(default_factory=list)
    exit_code: int = 0
    total_cost_usd: float | None = None
    duration_s: float | None = None
    stderr_tail: str = ""

    def write(self, out_dir: Path) -> None:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "transcript.json").write_text(
            json.dumps({"events": self.transcript}, indent=2)
        )
        (out_dir / "raw_events.jsonl").write_text(
            "\n".join(json.dumps(e) for e in self.raw_events)
        )
        (out_dir / "meta.json").write_text(
            json.dumps(
                {
                    "session_id": self.session_id,
                    "model": self.model,
                    "exit_code": self.exit_code,
                    "total_cost_usd": self.total_cost_usd,
                    "duration_s": self.duration_s,
                    "working_dir": str(self.working_dir),
                    "stderr_tail": self.stderr_tail,
                },
                indent=2,
            )
        )


def _mcp_config(mcp_repo: Path = REPO_ROOT) -> dict[str, Any]:
    """mcp config JSON that launches the reducto mcp via uv run."""
    return {
        "mcpServers": {
            "reducto": {
                "command": "uv",
                "args": [
                    "run",
                    "--project",
                    str(mcp_repo),
                    "mcp-server-reducto",
                ],
                "env": {k: v for k, v in os.environ.items() if k.startswith("REDUCTO_")},
            }
        }
    }


def _trunc(s: str, n: int = 2000) -> str:
    return s if len(s) <= n else s[: n - 3] + "..."


def _content_blocks(msg: dict[str, Any]) -> list[dict[str, Any]]:
    """Extract content blocks from an anthropic message dict. Returns [] if absent."""
    content = msg.get("content", [])
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    return content or []


def _normalize_event(sj: dict[str, Any]) -> list[dict[str, Any]]:
    """stream-json event → canonical events (0 or more).

    stream-json shape (observed):
      {"type": "system", "subtype": "init", ...}           → []
      {"type": "user", "message": {...anthropic msg...}}   → user text and/or tool_result blocks
      {"type": "assistant", "message": {...}}              → assistant text and/or tool_use blocks
      {"type": "result", ...}                              → []
    """
    t = sj.get("type")
    out: list[dict[str, Any]] = []

    if t == "user":
        for block in _content_blocks(sj.get("message", {})):
            bt = block.get("type")
            if bt == "text":
                out.append({"type": "user", "text": block.get("text", "")})
            elif bt == "tool_result":
                content = block.get("content", "")
                if isinstance(content, list):
                    content = "\n".join(
                        c.get("text", "") if isinstance(c, dict) else str(c) for c in content
                    )
                out.append(
                    {
                        "type": "tool_result",
                        "tool_use_id": block.get("tool_use_id", ""),
                        "content": _trunc(str(content)),
                    }
                )

    elif t == "assistant":
        for block in _content_blocks(sj.get("message", {})):
            bt = block.get("type")
            if bt == "text":
                out.append({"type": "assistant", "text": block.get("text", "")})
            elif bt == "tool_use":
                out.append(
                    {
                        "type": "tool_use",
                        "id": block.get("id", ""),
                        "name": block.get("name", ""),
                        "input": block.get("input", {}),
                    }
                )

    # system and result events are captured in raw_events only, not canonical transcript
    return out


class ClaudeCodeHarness:
    def __init__(
        self,
        *,
        model: ClaudeModel = "sonnet",
        mcp_repo: Path = REPO_ROOT,
        timeout_s: int = 600,
        bare: bool = False,
    ) -> None:
        """
        bare=True gives full eval isolation (no user CLAUDE.md/hooks/plugins) but
        requires ANTHROPIC_API_KEY — OAuth/keychain auth is ignored under --bare.
        Default off so local iteration uses whatever auth is already configured.
        """
        self.model = model
        self.mcp_repo = mcp_repo
        self.timeout_s = timeout_s
        self.bare = bare

    def prepare_working_dir(
        self,
        *,
        fixtures: list[Path] | None = None,
        seed_repo: Path | None = None,
    ) -> Path:
        """Create a clean working dir. Optionally copy in fixture files or a brownfield seed repo."""
        wd = Path(tempfile.mkdtemp(prefix="reducto-eval-"))
        if seed_repo is not None:
            # brownfield: copy the pre-existing app contents in
            for item in seed_repo.iterdir():
                if item.name in {".git", "node_modules", ".venv", "__pycache__"}:
                    continue
                dest = wd / item.name
                if item.is_dir():
                    shutil.copytree(item, dest)
                else:
                    shutil.copy2(item, dest)
        if fixtures:
            fx_dir = wd / "fixtures"
            fx_dir.mkdir(exist_ok=True)
            for f in fixtures:
                shutil.copy2(f, fx_dir / f.name)
        return wd

    def run(
        self,
        seed_prompt: str,
        working_dir: Path,
        *,
        on_event: Callable[[dict[str, Any]], None] | None = None,
    ) -> HarnessResult:
        session_id = str(uuid.uuid4())
        mcp_config_path = working_dir / ".reducto-eval-mcp.json"
        mcp_config_path.write_text(json.dumps(_mcp_config(self.mcp_repo), indent=2))

        cmd = ["claude"]
        if self.bare:
            cmd.append("--bare")
        cmd += [
            "--print",
            "--output-format", "stream-json",
            "--verbose",  # required by stream-json
            "--mcp-config", str(mcp_config_path),
            "--strict-mcp-config",
            "--dangerously-skip-permissions",
            "--model", self.model,
            "--session-id", session_id,
            f"--add-dir={working_dir}",  # = form — variadic flag would eat the prompt otherwise
            seed_prompt,
        ]

        import time
        t0 = time.time()
        proc = subprocess.Popen(
            cmd,
            cwd=working_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,  # avoid buffer-fill deadlock; failures show up as is_error=true in result event
            text=True,
            bufsize=1,
        )

        raw_events: list[dict[str, Any]] = []
        transcript: list[dict[str, Any]] = []
        # prepend the seed as a user event so transcripts are self-contained
        transcript.append({"type": "user", "text": seed_prompt})

        total_cost: float | None = None
        assert proc.stdout is not None
        try:
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    sj = json.loads(line)
                except json.JSONDecodeError:
                    continue
                raw_events.append(sj)
                if on_event:
                    on_event(sj)
                for norm in _normalize_event(sj):
                    transcript.append(norm)
                if sj.get("type") == "result":
                    # explicit key check — $0.00 is a legitimate value (cached/free-tier runs)
                    # and would be dropped by `a or b` because 0.0 is falsy in python
                    total_cost = sj["total_cost_usd"] if "total_cost_usd" in sj else sj.get("cost_usd")
            proc.wait(timeout=self.timeout_s)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()

        duration = time.time() - t0

        # surface the last result event's error as stderr_tail for visibility
        last_result = next((e for e in reversed(raw_events) if e.get("type") == "result"), None)
        stderr_tail = ""
        if last_result and last_result.get("is_error"):
            stderr_tail = str(last_result.get("result", ""))[-2000:]

        return HarnessResult(
            session_id=session_id,
            model=str(self.model),
            working_dir=working_dir,
            transcript=transcript,
            raw_events=raw_events,
            exit_code=proc.returncode or 0,
            total_cost_usd=total_cost,
            duration_s=duration,
            stderr_tail=stderr_tail,
        )


# ---------- cli ----------


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="run a scenario through the claude code harness")
    parser.add_argument("scenario", type=Path, help="scenario yaml path")
    parser.add_argument("--model", default="sonnet")
    parser.add_argument("--bare", action="store_true", help="use --bare (requires ANTHROPIC_API_KEY)")
    parser.add_argument("--out", type=Path, help="output dir for transcript/meta (default: reports/<run_id>/<scenario>/)")
    parser.add_argument("--verbose", "-v", action="store_true", help="stream events to stdout")
    args = parser.parse_args()

    import yaml

    scenario = yaml.safe_load(args.scenario.read_text())
    scenario_id = scenario["id"]

    fixtures_root = REPO_ROOT / "evals" / "fixtures"
    fixtures = [fixtures_root / f for f in scenario.get("fixture", []) if (fixtures_root / f).exists()]

    # Prepend the shared setup/usage prelude so every scenario sees the reducto mcp setup doc.
    # Keeps scenarios focused on task-specific content; central update point for the prelude.
    prelude_path = REPO_ROOT / "evals" / "scenarios" / "_setup_prelude.md"
    prelude = prelude_path.read_text() if prelude_path.exists() else ""
    # Harness note to the agent: mcp is already wired in this session, no need to re-add.
    harness_note = (
        "\n> **Note for this session:** the reducto mcp is already installed and connected "
        "(tools available as `mcp__reducto__*`). skip step 1 and 2 above — go straight to using the tools.\n"
    )
    seed = f"{prelude}{harness_note}\n---\n\n## Task\n\n{scenario['seed_prompt']}" if prelude else scenario["seed_prompt"]

    run_id = uuid.uuid4().hex[:8]
    out_dir = args.out or (REPO_ROOT / "evals" / "reports" / run_id / f"{scenario_id}__claude_code__{args.model}")

    harness = ClaudeCodeHarness(model=args.model, bare=args.bare)
    wd = harness.prepare_working_dir(fixtures=fixtures)

    def on_event(sj: dict[str, Any]) -> None:
        if args.verbose:
            t = sj.get("type")
            if t == "assistant":
                for b in _content_blocks(sj.get("message", {})):
                    if b.get("type") == "text":
                        print(f"[assistant] {_trunc(b.get('text', ''), 400)}")
                    elif b.get("type") == "tool_use":
                        print(f"[tool_use] {b.get('name')}({_trunc(json.dumps(b.get('input', {})), 200)})")
            elif t == "user":
                for b in _content_blocks(sj.get("message", {})):
                    if b.get("type") == "tool_result":
                        content = b.get("content")
                        if isinstance(content, list):
                            content = " ".join(
                                c.get("text", "") if isinstance(c, dict) else str(c) for c in content
                            )
                        print(f"[tool_result] {_trunc(str(content), 300)}")

    print(f"[harness] running {scenario_id} on claude-code ({args.model})")
    print(f"[harness] working dir: {wd}")
    if prelude:
        print(f"[harness] prelude prepended ({len(prelude)} chars)")
    result = harness.run(seed, wd, on_event=on_event)
    result.write(out_dir)

    # copy generated_app snapshot into out_dir
    gen_app = out_dir / "generated_app"
    if gen_app.exists():
        shutil.rmtree(gen_app)
    shutil.copytree(wd, gen_app, ignore=shutil.ignore_patterns("node_modules", ".venv", "__pycache__", ".reducto-eval-mcp.json"))

    print(f"[harness] done. exit={result.exit_code} duration={result.duration_s:.1f}s cost=${result.total_cost_usd or 0:.4f}")
    print(f"[harness] artifacts: {out_dir}")


if __name__ == "__main__":
    main()
