---
name: update-documentation
description: Refreshes the Reducto docs bundle that the MCP's get_documentation tool serves. Fetches the latest OpenAPI spec from platform.reducto.ai, combines with hand-written SDK templates, and regenerates src/mcp_server_reducto/docs_bundle.py. Use when the Reducto API surface changes (new endpoints, new params) or after editing scripts/docs_templates.py. Triggers on /update-documentation.
---

# update-documentation

You are refreshing the Reducto MCP's documentation bundle. The bundle is what powers the `get_documentation` MCP tool — it's how agents using this MCP discover SDK patterns, auth setup, and endpoint shapes.

## What this skill does

Runs `scripts/update_reducto_docs.py`, which:

1. Fetches the live OpenAPI spec from `https://platform.reducto.ai/openapi.json`
2. Extracts endpoint paths, request/response schema fields, and field descriptions
3. Combines with hand-written SDK templates from `scripts/docs_templates.py` (these contain code examples, install commands, gotchas — things the OpenAPI spec doesn't express)
4. Writes the combined output to `src/mcp_server_reducto/docs_bundle.py`

## How to run it

1. Run the update script:

```bash
uv run python scripts/update_reducto_docs.py
```

2. Verify the output:

```bash
uv run python -c "from mcp_server_reducto.docs_bundle import META, DOCS; print(META); print(sorted(DOCS.keys()))"
```

You should see the META block (with `fetched_at` showing a recent timestamp) and a list of topics.

3. Verify the MCP still boots:

```bash
uv run python -c "from mcp_server_reducto.server import create_server; create_server(); print('ok')"
```

4. Show the diff to the user — call `git diff src/mcp_server_reducto/docs_bundle.py | head -100` and summarize what changed in the bundle: new endpoints, new fields, removed fields, etc. Do NOT show the entire diff (it's large) — just the meaningful parts.

## When to update templates instead

If the user is asking about a SDK pattern that isn't quite right (e.g. "the Node example shows the wrong upload pattern"), the fix is in `scripts/docs_templates.py`, not in the OpenAPI spec. Edit that file directly, then re-run this skill to regenerate the bundle.

The OpenAPI spec gives us:
- Endpoint paths, methods
- Request/response schema fields with descriptions
- Field types

It does NOT give us:
- Code examples
- Install commands  
- The Node SDK's `toFile()` workaround
- Auth setup (`.env.local` patterns)
- `form_schema` caching for edits
- `jobid://` chaining

Those live in `scripts/docs_templates.py` and must be updated by hand when SDK conventions change.

## Constraints

- Do NOT edit `src/mcp_server_reducto/docs_bundle.py` by hand — it's regenerated. Edit `scripts/docs_templates.py` and re-run.
- Do NOT modify the script itself unless asked — it's the contract between OpenAPI and the bundle.
- The bundle should be checked in (it's loaded at import time by the MCP).
