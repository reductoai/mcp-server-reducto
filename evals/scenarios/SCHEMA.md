# scenario schema

each scenario is a yaml file describing one eval. the runner loads it, drives the harness to attempt the goal, then grades the rubric against the generated app and (optionally) the agent transcript.

## fields

- `id` — stable slug, matches the filename
- `environment` — `python_sdk` | `node_sdk` | `http`
- `feature` — `parse` | `extract` | `split` | `edit`
- `mode` — `greenfield` | `brownfield`
- `source` — provenance, e.g. `ported from testapps/chatwithmypdf`
- `seed_prompt` — the user's first message to the agent
- `fixture` — list of input files (relative to `evals/fixtures/`)
- `rubric` — four lists of checks: `stand_up`, `config_knowledge`, `mcp_usage`, `outcome_success`
- `known_failure_signals` — list of checks that, when tripped, dock the axes listed in each signal's `penalizes` field
- `pass_threshold` — default 0.8 (tunable per scenario)
- `notes` — free text

## axes

| axis               | measures                                                                                                     |
| ------------------ | ------------------------------------------------------------------------------------------------------------ |
| `stand_up`         | did the reducto integration get set up correctly — sdk/http client installed, auth wired (keys reachable, not hardcoded), reducto client instantiated, reducto-touching code compiles |
| `config_knowledge` | does the generated reducto code use the api correctly — right tool, right params, response shapes handled    |
| `mcp_usage`        | did the agent actually consult the mcp (graded against the transcript — `null` if no transcript)             |
| `outcome_success`  | does the generated integration actually work against the Reducto API with real fixtures; these checks should make live Reducto calls using `REDUCTO_API_KEY`, validate useful parse/extract output, and avoid grading cosmetic UI details |

## check format

```yaml
- id: short_slug
  desc: human-readable description
  kind: file_exists | grep | not_grep | shell | judge | tool_used | tool_not_used | judge_transcript
  tags: [auth, urlresult, ...] # optional, for cross-scenario reporting
  # one of the following, per kind:
  path: app/api/upload/route.ts # file_exists
  pattern: "client\\.parse\\.run" # grep / not_grep / tool_used / tool_not_used
  in: "app/api/**/*.ts" # grep / not_grep target glob
  cmd: "pnpm build" # shell (must exit 0)
  timeout: 60 # shell, seconds
  min_count: 1 # tool_used, default 1
  prompt: "does the generated app..." # judge / judge_transcript
  paths: ["app/api/**/*.ts"] # judge — file globs to include as context (default: all source files)
```

## check kinds

| kind               | operates on | passes when                              |
| ------------------ | ----------- | ---------------------------------------- |
| `file_exists`      | app dir     | path exists                              |
| `grep`             | app dir     | pattern matches any file in `in` glob    |
| `not_grep`         | app dir     | pattern matches no file                  |
| `shell`            | app dir     | command exits 0                          |
| `judge`            | app dir     | llm judge (unwired — stubbed in v0.1)    |
| `tool_used`        | transcript  | ≥ `min_count` tool calls match `pattern` |
| `tool_not_used`    | transcript  | no tool calls match `pattern`            |
| `judge_transcript` | transcript  | llm judge (unwired — stubbed in v0.1)    |

transcript-based checks return `null` (skipped) when no transcript is provided.

## outcome_success checks

`outcome_success` is the most important axis. It should use `kind: shell` checks
that install the generated app's dependencies, write a small standalone test
script into the app directory, and exercise the app's Reducto integration with
the scenario fixture. Parse checks should verify non-empty document text or
chunks and print `SUCCESS`; extract checks should verify structured invoice
fields such as vendor, date, total, and category and print `SUCCESS`.

These checks should be realistic but tolerant of different generated file
layouts. Prefer discovering generated integration files, helper functions, or
API route handlers over asserting exact paths. They should use
`REDUCTO_API_KEY` from the environment and fail when it is missing.

## failure signals

each signal has the same shape as a check, plus:

```yaml
- id: ...
  kind: ...
  penalizes: [stand_up, mcp_usage] # default [config_knowledge] if omitted
  tags: [auth]
```

tripped signals add a failed check to each listed axis's bucket when scoring.

## scoring

- `<axis>_score` = `passed / (graded + tripped_signals_penalizing_this_axis)` per axis
- `<axis>_score_raw` = pre-penalty score for diagnostics
- `failure_signals_tripped` = list of tripped signal ids
- `tag_scores` = `{tag: (passed, total)}` aggregated across all axes — for slicing reports by concern (auth, urlresult, etc.)
- `goal_achieved` = all axes ≥ `pass_threshold`
- `prompts_to_success` = user turns until goal_achieved, null if cap (10) hit

## transcript format

canonical transcript json — harnesses normalize their native format to this:

```json
{
  "events": [
    {"type": "user", "text": "..."},
    {"type": "assistant", "text": "..."},
    {"type": "tool_use", "name": "mcp__reducto__upload_file", "input": {...}},
    {"type": "tool_result", "name": "mcp__reducto__upload_file", "content": "..."}
  ]
}
```

order preserved. `tool_result` content truncated to 2000 chars per event (by the harness) for judge_transcript cost control.
