# evals

eval set for the reducto mcp. measures (1) how well the mcp stands up reducto in new apps, (2) how well it exposes reducto config knowledge to agents.

spec: [PRD-535](https://linear.app/reducto/issue/PRD-535/mcp-build-eval-set).

## layout

```
evals/
  scenarios/
    greenfield/    # build a new app using reducto
    brownfield/    # add reducto to an existing app (v0.3)
  fixtures/        # sample docs + brownfield repo snapshots
  harnesses/       # claude_code.py, codex.py
  reports/         # baseline + subsequent runs
  user_simulator.py
  rubric.py
  run.py
```

## running

grade an existing app against a scenario (no harness, no agent):

```
uv run python -m evals.rubric \
  evals/scenarios/greenfield/node_sdk__parse__chatwithmypdf.yaml \
  /path/to/generated/app \
  [--transcript path/to/transcript.json] \
  [--skip-shell] [--verbose]
```

drive claude code on a scenario (single-shot, produces transcript + generated app):

```
uv run python -m evals.harnesses.claude_code \
  evals/scenarios/greenfield/node_sdk__parse__chatwithmypdf.yaml \
  --model sonnet \
  [--bare]       # use --bare for strict isolation (requires ANTHROPIC_API_KEY)
  [--verbose]    # stream events live
```

artifacts land at `evals/reports/<run_id>/<scenario>__claude_code__<model>/`:
- `transcript.json` — canonical event stream
- `raw_events.jsonl` — raw stream-json from claude cli
- `meta.json` — session id, model, cost, duration, exit code
- `generated_app/` — snapshot of what the agent produced

## scenario format

see `scenarios/greenfield/node_sdk__parse.yaml` for the canonical example.
