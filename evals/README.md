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

tbd — harness lands in v0.1.

## scenario format

see `scenarios/greenfield/node_sdk__parse.yaml` for the canonical example.
