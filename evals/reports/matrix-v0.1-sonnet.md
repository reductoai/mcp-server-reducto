# matrix baseline — v0.1, claude code × sonnet

5 scenarios × claude code × sonnet. judges live (sonnet-4-6 via anthropic direct api). mcp loaded cleanly in all runs (8 `mcp__reducto__*` tools advertised at session init).

## cost / time

| scenario | duration | run cost | judge cost (est) |
|---|---|---|---|
| node_sdk × parse (chatwithmypdf) | 270s | $0.44 | ~$0.03 |
| node_sdk × extract (invoice_tracker) | 690s | $2.19 | ~$0.03 |
| python_sdk × extract (pythoninvoices) | 361s | $1.32 | ~$0.03 |
| http × split (restsplit) | 186s | $0.51 | ~$0.03 |
| http × edit (pythonchatwithpdf) | 284s | $0.46 | ~$0.03 |
| **total** | **30 min** | **$4.92** | **~$0.15** |

## scorecard

| scenario | stand_up | config_knowledge | mcp_usage | signals tripped |
|---|---|---|---|---|
| node_sdk × parse | **0.33** | **0.33** | **0.00** | — |
| node_sdk × extract | **1.00** | **0.75** | **0.25** | — |
| python_sdk × extract | **0.67** | **0.75** | **0.25** | — |
| http × split | **0.67** | **0.60** | **0.25** | `one_chapter_bug` |
| http × edit | **0.67** | **0.60** | **0.00** | `no_form_schema_caching` |
| **mean** | **0.67** | **0.61** | **0.15** | — |

## five observations

1. **mcp_usage is catastrophically low.** 0.00 or 0.25 in every single run. sonnet consistently scaffolds from training memory, touching the mcp at most once (e.g. a `ToolSearch` at start). none of the agents called `mcp__reducto__extract_data`, `mcp__reducto__split_document`, `mcp__reducto__edit_document`, etc. even when those were the core operation of the scenario. **this is the flagship finding: mcp is loaded, advertised, ignored.**

2. **urlresult handling fails universally.** 4 of 5 scenarios failed `handles_urlresult`. every agent assumes the parse/extract result is inline. this is a consistent, high-value cell to address in mcp docs/prompts.

3. **node sdk × parse collapsed hardest.** the only scenario where the agent ditched the sdk and wrote raw `fetch` against `platform.reducto.ai` (wrong host) with invented endpoints. matrix low across all three axes.

4. **extract was sonnet's strongest feature.** right tool (`extract.run`), right params, reasonable invoice schema in both node and python. it's the cell where training memory is closest to reality.

5. **feature-specific best practices go missing.** restsplit tripped `one_chapter_bug` (naive assumption that split returns multiple chapters with no fallback). pythonchatwithpdf tripped `no_form_schema_caching` (never stashed form_schema across edit calls). these are exactly the kind of details the mcp should teach, and agents miss them when they code from memory.

## cell-level color

<details>
<summary>node_sdk × parse — 0.33 / 0.33 / 0.00</summary>

rolled raw fetch to `platform.reducto.ai/upload` and `/parse` (both wrong — host is `api.reducto.ai`, endpoint is `/parse/run`). no `reductoai` dep. zero mcp tool calls. the worst run in the matrix.
</details>

<details>
<summary>node_sdk × extract — 1.00 / 0.75 / 0.25</summary>

used the sdk correctly, good invoice schema, quarterly aggregation present. failed only on `handles_urlresult` (assumes inline) and on mcp tool usage.
</details>

<details>
<summary>python_sdk × extract — 0.67 / 0.75 / 0.25</summary>

correct `client.extract.run(input=..., instructions={schema: ...})` pattern. required fields present. missing: urlresult handling, mcp engagement.
</details>

<details>
<summary>http × split — 0.67 / 0.60 / 0.25</summary>

used correct base url (`api.reducto.ai`), implemented `jobid://` reuse for split → parse, got endpoint shapes right. tripped `one_chapter_bug` judge (naive assumption of multiple chapters) and failed urlresult handling.
</details>

<details>
<summary>http × edit — 0.67 / 0.60 / 0.00</summary>

correct base url, correct `/edit` call, file_id passed correctly. tripped `no_form_schema_caching` signal — each edit starts fresh, which is both slower and less accurate. zero mcp engagement.
</details>

## biggest v0.2 wedges (from this data)

1. wire prompts/docs/examples in the mcp that push the agent to **actually call mcp tools for discovery** — even one call to `mcp__reducto__parse_document` would get the response shape right.
2. make URLResult handling unmissable — either prominent in tool docs or as a code sample in the scenario-setup response.
3. feature-specific best practices should ship as advice from the relevant mcp tool's response (e.g. `edit_document` tool response should mention `form_schema` caching).

## what this doesn't tell us yet

- no opus comparison (v0.2 — model variation)
- no codex (v0.2 — harness variation)
- no multi-turn — these are single-shot runs (v0.3 — user simulator)
- no brownfield (v0.3)
