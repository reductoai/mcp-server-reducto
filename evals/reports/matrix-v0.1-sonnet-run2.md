# matrix run 2 — v0.1, claude code × sonnet

fresh run of all 5 scenarios, same harness + model + scenarios as run1.

## scorecard

| scenario | stand_up | config_knowledge | mcp_usage | signals tripped | run1 delta |
|---|---|---|---|---|---|
| node_sdk × parse | 0.33 | 0.33 | 0.00 | — | same |
| node_sdk × extract | **—** | **—** | **—** | — | ⚠️ agent scaffolded at `/tmp/invoice-app` (outside harness workdir) — snapshot empty |
| python_sdk × extract | 0.33 | 0.75 | 0.25 | — | stand_up dropped 0.67→0.33 |
| http × split | 0.25 | 0.40 | 0.00 | `wrong_base_url_platform` | worse across all axes, new signal trip |
| http × edit | 0.67 | 0.60 | 0.00 | `no_form_schema_caching` | same |
| **mean (4 graded)** | **0.40** | **0.52** | **0.06** | | |

## cost / time

~$4.93 total, ~10 min wall (parallelized). comparable to run1.

## biggest trends vs run1

1. **mcp_usage remains catastrophically low, confirmed across 2 independent runs.** 0.00 in 3 of 4 graded scenarios. sonnet still doesn't call `mcp__reducto__*` tools even when they're exposed and would answer exactly the question the agent has.

2. **run-to-run variance is real.** restsplit went from 0.67/0.60 to 0.25/0.40 and newly tripped `wrong_base_url_platform`. pythoninvoices stand_up dropped 0.67→0.33. same seed prompt, different outcomes. this is a sampling concern we'll need to address before drawing strong conclusions per-cell — probably n>=3 runs per cell for v0.2 stats.

3. **same failure modes, different surface forms.** URLResult unhandled in every extract scenario across both runs. `form_schema` not cached in pythonchatwithpdf across both runs. `wrong_base_url_platform` tripped on restsplit in run2 but not run1.

4. **harness bug surfaced.** invoice-tracker's run: agent said "App is at `/private/var/folders/.../T/invoice-app`" and mkdir'd outside the working directory. our `generated_app/` snapshot is empty. `--dangerously-skip-permissions` removes the cwd barrier, and nothing in the seed prompt tells the agent to stay put. needs fix (seed prompt hint, or post-hoc scan for scaffolded-app paths in the transcript).

## what this doesn't change

the flagship finding from run1 holds: **mcp is loaded, advertised, ignored.** feature-specific best practices (form_schema caching, urlresult handling) are missed regardless of run.
