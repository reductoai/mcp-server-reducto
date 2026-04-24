# n=3 matrix — claude code × sonnet

8 scenarios × 3 runs each = 24 total runs. judges live (anthropic api, with dual-evidence support — judge sees both generated files and agent transcript).

cost: ~$20.50 across all batches. ~3 hrs wall total.

## priority cells (parse + extract across all environments)

these are the 6 cells we care most about — parse and extract are the two core reducto operations.

| scenario | stand_up | config_knowledge | mcp_usage | signals (count out of 3) |
|---|---|---|---|---|
| python_sdk × parse | 0.44 [0.33..0.67] | 0.67 [0.67..0.67] | 0.25 [0.25..0.25] | — |
| python_sdk × extract | 0.61 [0.50..0.67] | 0.75 [0.75..0.75] | 0.23 [0.20..0.25] | hand_parsed_config_yaml 1/3 |
| node_sdk × parse | 0.22 [0.00..0.33] | 0.56 [0.33..0.67] | 0.50 [0.25..0.75] | — |
| node_sdk × extract | **1.00** [1.00..1.00] | 0.77 [0.75..0.80] | 0.42 [0.25..0.75] | file_param_cast_hack 1/3 |
| http × parse | 0.58 [0.25..1.00] | **0.85** [0.75..1.00] | 0.42 [0.00..1.00] | hand_parsed_config_yaml 1/3, wrong_base_url_platform 1/3 |
| http × extract | 0.72 [0.50..1.00] | 0.53 [0.50..0.60] | 0.08 [0.00..0.25] | wrong_base_url_platform 1/3 |
| **priority mean (n=18)** | **0.60** | **0.69** | **0.32** | |

## non-priority cells (split + edit, http only)

ported from existing testapps; not the focus of v0.1 going forward.

| scenario | stand_up | config_knowledge | mcp_usage | signals (count out of 3) |
|---|---|---|---|---|
| http × split | 0.42 [0.25..0.67] | 0.30 [0.20..0.50] | 0.00 [0.00..0.00] | **one_chapter_bug 3/3**, wrong_base_url_platform 1/3 |
| http × edit | 0.25 [0.25..0.25] | 0.70 [0.50..0.80] | 0.08 [0.00..0.25] | **wrong_base_url_platform 3/3**, no_form_schema_caching 1/3 |

## headlines

1. **http × parse is the surprise winner.** config_knowledge mean 0.85, with one run hitting a perfect 1.00 / 1.00 / 1.00. agents who chose to use the rest API for parse used it correctly more often than node_sdk × parse agents used the SDK.

2. **node_sdk × extract is the most reliable.** stand_up locked at 1.00 across all 3 runs, config 0.77. when sonnet recognizes the use case, it knows exactly what shape to produce.

3. **deterministic failures (3/3 runs)** in the non-priority cells point to specific mcp gaps:
   - `wrong_base_url_platform` in pythonchatwithpdf — sonnet's training memory for the reducto host is just wrong, every run
   - `one_chapter_bug` in restsplit — assumes split always returns multiple sections

4. **mcp_usage is bimodal.** chatwithmypdf range 0.25..0.75, http × parse range 0.00..1.00. some runs reach for the mcp constantly; others never touch it. the seed prompt language meaningfully affects this.

5. **priority-cell means (0.60 / 0.69 / 0.32)** are noticeably better than the full-matrix means (0.50 / 0.62 / 0.25). the cells we care about are the ones the mcp helps with most — at least for sonnet today.

## what's open

- this is single-shot data. no multi-turn (`prompts_to_success` requires the user simulator).
- claude code only. no codex / opus comparison yet.
- greenfield only. no brownfield (existing app needing reducto added).
