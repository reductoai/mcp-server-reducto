# n=3 matrix — defensible numbers

5 scenarios × 3 runs each = 15 total runs. claude code × sonnet. judges live (now with dual-evidence support — can see both generated files and agent transcript). after iterating on tool descriptions through run5.

cost: ~$15 across all batches. ~2 hrs wall (3 batches of 5, mostly in parallel).

## per-scenario (mean [min..max])

| scenario | n | stand_up | config_knowledge | mcp_usage |
|---|---|---|---|---|
| node_sdk × parse (chatwithmypdf) | 3 | **0.22** [0.00..0.33] | **0.56** [0.33..0.67] | **0.50** [0.25..0.75] |
| node_sdk × extract (invoice_tracker) | 3 | **1.00** [1.00..1.00] | **0.77** [0.75..0.80] | **0.42** [0.25..0.75] |
| python_sdk × extract (pythoninvoices) | 3 | **0.61** [0.50..0.67] | **0.75** [0.75..0.75] | **0.23** [0.20..0.25] |
| http × split (restsplit) | 3 | **0.42** [0.25..0.67] | **0.30** [0.20..0.50] | **0.00** [0.00..0.00] |
| http × edit (pythonchatwithpdf) | 3 | **0.25** [0.25..0.25] | **0.70** [0.50..0.80] | **0.08** [0.00..0.25] |
| **overall mean** | 15 | **0.50** | **0.62** | **0.25** |

## failure signals across 3 runs (N/3 trips)

| scenario | signals |
|---|---|
| chatwithmypdf | — |
| invoice_tracker | file_param_cast_hack 1/3 |
| pythoninvoices | hand_parsed_config_yaml 1/3 |
| restsplit | **one_chapter_bug 3/3**, wrong_base_url_platform 1/3 |
| pythonchatwithpdf | **wrong_base_url_platform 3/3**, no_form_schema_caching 1/3 |

## key findings

1. **the http scenarios (restsplit + pythonchatwithpdf) don't touch the mcp.** 0.00 and 0.08 mcp_usage across 6 runs total. the prelude + tool descriptions aren't enough — when the user seed-prompt says "use the rest api", the agent reads that as "do not use the mcp" and rolls raw `requests`/`httpx`. this is the most addressable cell.

2. **2 signals are consistent across all 3 runs, not noise**:
   - `one_chapter_bug` in restsplit (every run)
   - `wrong_base_url_platform` in pythonchatwithpdf (every run — sonnet's training memory for the reducto host is wrong and stable)
   
   these aren't sampling issues; they're stable mcp-communication gaps.

3. **stand_up has huge variance in some cells.** chatwithmypdf 0.00..0.33 and restsplit 0.25..0.67. the "did the agent set up correctly" axis is more noisy than the others — makes sense since one bad choice (e.g. agent decides to use raw http this run) cascades through the whole axis.

4. **config_knowledge is the most stable axis.** tight ranges across all 5 cells (≤0.30 span). tool descriptions have meaningfully landed — agents that use reducto at all use it reasonably correctly.

5. **sonnet's ceiling on mcp_usage for this scenario set looks like ~0.25-0.50** for sdk-oriented scenarios, ~0 for rest-oriented scenarios. tool descriptions alone hit a ceiling.

## what this replaces

previous best single-run result (run5) was 0.43 / 0.61 / 0.34. the n=3 mean is 0.50 / 0.62 / 0.25 — run5's 0.34 mcp_usage was above trend (one scenario hit 1.00 that day). the defensible number is 0.25 mean.

## what to try next

the research agent flagged **next-step hints in tool responses** (intervention #5) as medium-effort/medium-lift. specifically: after `parse_document` returns, append guidance text like "for structured fields, call `extract_data` with `jobid://<id>`; if `result_type` is 'url', fetch the presigned URL." these hints show up AFTER the agent has already called the mcp, reinforcing the habit.

but the bigger lever for http scenarios (where mcp_usage is 0.00) is the seed-prompt ambiguity: "use the rest api" is taken literally by the agent. we should either:
  - rephrase prelude to clarify that the mcp is the dev-time tool even if the final app uses rest
  - or accept that http-scenarios will naturally deprioritize the mcp and focus improvements on the sdk scenarios

## recommended next iteration

1. add next-step hints to response formatters in `src/mcp_server_reducto/response.py` — cheap, uniform
2. also strengthen the prelude's "when to call the mcp" framing for http scenarios
3. rerun n=3 to measure
