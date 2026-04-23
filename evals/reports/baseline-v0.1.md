# v0.1 baseline

first real eval run against the reducto mcp. one scenario × one harness × one model, judges unwired.

## setup

- scenario: `greenfield/node_sdk__parse__chatwithmypdf`
- harness: claude code (non-bare, user OAuth auth, sonnet)
- mcp: `uv run --project . mcp-server-reducto` via `--mcp-config --strict-mcp-config`
- mcp loaded cleanly at session init — 8 `mcp__reducto__*` tools exposed
- duration: 270.7s, cost: $0.44

## scores (judges live)

```
stand_up_score:             0.33   (1/3 graded)
config_knowledge_score:     0.33   (1/3 graded)
mcp_usage_score:            0.00   (0/4 graded)
failure_signals_tripped:    []

tag scores:
  auth            1/1
    ✓ no_hardcoded_api_key
    ! hand_parsed_config_yaml (signal, clear)
  params_shape    0/2
    ✗ uses_upload_then_parse — raw fetch calls to the Reducto HTTP API instead of the Node SDK
    ✗ used_upload_tool — no mcp call
    ! file_param_cast_hack (signal, clear)
  response_shape  0/1
    ✗ handles_urlresult — blindly accesses data.result.chunks without checking result.type
    ! urlresult_bailout (signal, clear)
  urlresult       0/1
    ✗ handles_urlresult (same as above)
    ! urlresult_bailout (signal, clear)
```

judge verdicts (detail):
- `uses_upload_then_parse` ✗ — raw fetch calls to the Reducto HTTP API instead of the Node SDK
- `handles_urlresult` ✗ — blindly accesses data.result.chunks without checking result.type
- `chat_uses_parsed_text` ✓ — injects parsedText into system prompt as `<document>${parsedText}</document>`
- `judge_engagement` (transcript) ✗ — single ToolSearch at the very beginning, then coded from memory

## what happened

sonnet ignored the node sdk entirely and rolled raw HTTP — with the wrong hostname:

```ts
const REDUCTO_BASE = "https://platform.reducto.ai";   // wrong — it's api.reducto.ai
...
await fetch(`${REDUCTO_BASE}/upload`, ...)            // wrong endpoint shape
await fetch(`${REDUCTO_BASE}/parse`, { body: JSON.stringify({ document_url: ... }) })  // wrong — /parse/run, takes file_id as input
```

- `package.json` has no `reductoai` dep
- no `new Reducto()` client instantiation anywhere
- zero `mcp__reducto__*` tool calls across the entire 19-tool-use transcript (just Bash / ToolSearch / Write)
- failure signals didn't trip because the agent didn't write sdk code at all — different failure mode than the one the signals were tuned for

## what this tells us

the mcp provided zero value here. not because it was broken — it was loaded and advertised — but because the agent never reached for it. classic "code from memory" pattern, and the code from memory is wrong (wrong host, wrong endpoints, wrong request shapes).

signal-wise the rubric did its job: **stand_up 0.33 + mcp_usage 0.00** is an honest read on this run. once the judges are wired, config_knowledge will also show red (`handles_urlresult` and `uses_upload_then_parse` would both fail — the agent isn't using the upload/parse.run pattern at all).

## followups surfaced by this run

- **app root detection**: agent created a `chatWithMyPDF/` subdirectory rather than writing at the working-dir root. rubric had to be pointed at the subdir manually. the orchestrator (run.py) should detect the root (e.g., first dir containing `package.json`) rather than assuming it.
- **stop hook noise**: `"Stop hook error occurred"` events leak in from user-level hooks. would go away under `--bare`, tolerable for now.
- **add more failure signals for this pattern**: current signals assume the agent wrote sdk code. we should add a signal for "agent wrote raw fetch against `platform.reducto.ai`" or similar wrong-endpoint patterns.
