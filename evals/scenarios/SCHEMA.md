# scenario schema

each scenario is a yaml file describing one eval. the runner loads it, drives the harness to attempt the goal, then grades the rubric.

## fields

- `id` — stable slug, matches the filename (e.g. `node_sdk__parse__chatwithmypdf`)
- `environment` — `python_sdk` | `node_sdk` | `http`
- `feature` — `parse` | `extract` | `split` | `edit`
- `mode` — `greenfield` | `brownfield`
- `source` — provenance, e.g. `ported from testapps/chatwithmypdf`
- `seed_prompt` — the user's first message to the agent, verbatim-style
- `fixture` — list of input files (relative to `evals/fixtures/`) the simulator can attach / reference
- `rubric` — two lists of checks:
  - `stand_up` — setup/install/auth/client-init
  - `config_knowledge` — reducto-usage correctness
- `known_failure_signals` — specific mistakes observed in prior runs; tripping any flags but doesn't hard-fail
- `notes` — free text

## check format

each rubric entry is one of:

```yaml
- id: short_slug
  desc: human-readable description
  kind: file_exists | grep | not_grep | shell | judge
  # one of the following, per kind:
  path: app/api/upload/route.ts             # file_exists
  pattern: "client\\.parse\\.run"           # grep / not_grep
  in: app/api/**/*.ts                       # grep target glob
  cmd: "pnpm build"                         # shell (must exit 0)
  prompt: "does the generated app handle..." # judge
```

automated checks (`file_exists`, `grep`, `not_grep`, `shell`) run against the generated repo. `judge` calls an llm with the prompt + relevant file contents.

## scoring

- `stand_up_score` = passed(stand_up) / total(stand_up)
- `config_knowledge_score` = passed(config_knowledge) / total(config_knowledge)
- `goal_achieved` = both scores ≥ 0.8 (tunable per scenario via `pass_threshold`)
- `prompts_to_success` = number of simulator turns until `goal_achieved`, or null if never within cap=10
- `failure_signals_tripped` = list of triggered ids from `known_failure_signals`
