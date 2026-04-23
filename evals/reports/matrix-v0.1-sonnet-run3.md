# matrix run 3 — with setup prelude prepended

same 5 scenarios, same model (sonnet), same harness. only change: every seed prompt now starts with the reducto mcp setup/usage doc (install instructions + tools table + chaining tips).

## scorecard

| scenario | run2 (no prelude) | run3 (prelude) | signals tripped (run3) |
|---|---|---|---|
| node_sdk × parse | 0.33 / 0.33 / 0.00 | 0.33 / 0.33 / 0.00 | — |
| node_sdk × extract | — (harness miss) | 1.00 / 0.60 / 0.25 | `file_param_cast_hack` |
| python_sdk × extract | 0.33 / 0.75 / 0.25 | 0.50 / 0.50 / 0.00 | `hand_parsed_config_yaml` |
| http × split | 0.25 / 0.40 / 0.00 | 0.25 / 0.33 / 0.25 | `wrong_base_url_platform`, `one_chapter_bug` |
| http × edit | 0.67 / 0.60 / 0.00 | 0.33 / 0.60 / 0.00 | `no_form_schema_caching` |
| **mean** | **0.40 / 0.52 / 0.06** (n=4) | **0.48 / 0.47 / 0.10** (n=5) | |

cost: ~$4.14, ~12 min wall.

## verdict: prelude alone did not move the needle materially

- **mcp_usage**: 0.06 → 0.10. not statistically meaningful. the agent still isn't calling `mcp__reducto__*` tools as its main path. it's writing code from memory and occasionally name-checking the mcp.
- **stand_up**: 0.40 → 0.48. small lift but within run-to-run variance observed earlier.
- **config_knowledge**: 0.52 → 0.47. slight regression, within noise.

## why the prelude wasn't enough

the prelude has **what tools exist** and **how to install**. it does not have **how to avoid the failures we've been catching**:

1. **urlresult handling** — never mentioned. every extract/parse scenario still assumes inline response.
2. **form_schema caching on edit** — not in the prelude. pythonchatwithpdf still tripped this.
3. **node sdk upload typing quirk** — not in the prelude. invoice_tracker cast `as unknown as string` this run.
4. **auth resolution** — the prelude says api key is saved to config.yaml by login, but doesn't say *"the sdk reads this automatically; don't parse it yourself."* pythoninvoices still tripped `hand_parsed_config_yaml`.
5. **wrong base url** — not in the prelude. restsplit tripped `wrong_base_url_platform` again.
6. **use the mcp tools, don't write raw http / sdk equivalents** — the prelude implies this via the tools table but never says it directly. chatwithmypdf and restsplit still didn't.

## what should be in a v2 prelude

move from "what exists" to "what to do + what NOT to do":

```
## DO NOT
- do not write raw http / fetch against api.reducto.ai or platform.reducto.ai — always call the mcp tools
- do not hand-parse ~/.reducto/config.yaml — the sdk reads REDUCTO_API_KEY or the config automatically
- do not hardcode api keys in source

## DO
- for uploads: call upload_file(), pass the returned reducto:// URL to other tools
- for chaining: pass jobid://<id> to skip re-parsing
- for edits: cache form_schema across calls to the same doc
- parse/extract can return {type: "url"} — branch on result.type and fetch when needed
- Reducto's base URL is api.reducto.ai, never platform.reducto.ai
```

## next step options

1. **ship the stricter prelude and rerun.** see if this actually moves the needle.
2. **pack the same guidance into mcp tool descriptions.** the agent sees tool descriptions at call sites, not just in the seed. might have more lift.
3. **accept that the intervention class of "put docs in front of the agent" has a ceiling here, and try something structurally different.** e.g. have the mcp tools *actually guide* (e.g. parse_document returns a hint in its response about URLResult handling; edit_document bakes in form_schema).

my read: (1) is worth one more $5 run. if it still doesn't move mcp_usage, that's strong signal that (3) is needed.
