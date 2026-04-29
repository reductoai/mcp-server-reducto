"""Generate src/mcp_server_reducto/docs_bundle.py from the Reducto OpenAPI spec
combined with hand-written SDK templates in docs_templates.py.

The /update-documentation skill invokes this script. Run it manually with:

    uv run python scripts/update_reducto_docs.py

Inputs:
- https://platform.reducto.ai/openapi.json (live fetch)
- scripts/docs_templates.py (hand-written SDK examples per topic × language)

Output:
- src/mcp_server_reducto/docs_bundle.py (a Python module the get_documentation
  tool reads from)

The bundle has:
- META: openapi version, fetch timestamp, etc.
- DOCS: {topic: {summary, endpoint?, request_fields?, response_fields?,
                 languages: {node|python|http: markdown}, gotchas: [...]}}

Auto-extracted from OpenAPI: endpoint paths, request/response schema fields, descriptions.
Hand-written from templates: per-language code examples, install commands, gotchas.
"""
from __future__ import annotations

import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
OPENAPI_URL = "https://platform.reducto.ai/openapi.json"
BUNDLE_PATH = REPO_ROOT / "src" / "mcp_server_reducto" / "docs_bundle.py"

# Map topic keys to the openapi path that backs them. None = cross-cutting topic.
TOPIC_TO_PATH = {
    "quickstart": None,
    "parse": "/parse",
    "extract": "/extract",
    "split": "/split",
    "edit": "/edit",
    "upload": "/upload",
    "classify": "/classify",
    "auth": None,
}


def fetch_openapi(url: str = OPENAPI_URL) -> dict[str, Any]:
    """Fetch the OpenAPI spec from platform.reducto.ai."""
    print(f"fetching {url}...", flush=True)
    with urllib.request.urlopen(url, timeout=30) as resp:
        spec = json.loads(resp.read())
    print(f"  got openapi {spec.get('openapi')} ({len(spec.get('paths', {}))} paths, {len(spec.get('components', {}).get('schemas', {}))} schemas)")
    return spec


def resolve_ref(spec: dict, ref: str) -> dict:
    """Resolve a $ref pointer like '#/components/schemas/Foo'."""
    parts = ref.lstrip("#/").split("/")
    node: Any = spec
    for p in parts:
        node = node[p]
    return node


def schema_summary(spec: dict, schema: dict, depth: int = 0, max_depth: int = 2) -> dict[str, str]:
    """Walk a schema (resolving refs) and return {field_name: short_description}.

    Trims nested objects past max_depth to keep the bundle small.
    """
    if "$ref" in schema:
        schema = resolve_ref(spec, schema["$ref"])

    out: dict[str, str] = {}
    props = schema.get("properties", {})
    for name, pdef in props.items():
        if "$ref" in pdef:
            target = resolve_ref(spec, pdef["$ref"])
            type_label = target.get("title") or pdef["$ref"].rsplit("/", 1)[-1]
            desc = target.get("description", "") or pdef.get("description", "")
        else:
            type_label = pdef.get("type", "")
            if type_label == "array":
                items = pdef.get("items", {})
                inner = items.get("$ref", "").rsplit("/", 1)[-1] or items.get("type", "")
                type_label = f"array<{inner}>"
            desc = pdef.get("description", "")
        out[name] = (f"({type_label}) {desc}".strip())[:200]
    return out


def extract_endpoint_info(spec: dict, path: str) -> dict[str, Any]:
    """Pull the most useful info for one endpoint."""
    if path not in spec.get("paths", {}):
        return {}
    op = spec["paths"][path].get("post") or spec["paths"][path].get("get") or {}
    info: dict[str, Any] = {
        "endpoint": f"POST {path}" if "post" in spec["paths"][path] else f"GET {path}",
        "summary": op.get("summary", ""),
        "description": (op.get("description") or "")[:500],
    }

    # Request body schema fields
    req = (op.get("requestBody", {}).get("content", {}).get("application/json", {}).get("schema", {}))
    if req:
        if "oneOf" in req:
            # use first option (sync variant)
            req = resolve_ref(spec, req["oneOf"][0]["$ref"]) if "$ref" in req["oneOf"][0] else req["oneOf"][0]
        elif "$ref" in req:
            req = resolve_ref(spec, req["$ref"])
        info["request_fields"] = schema_summary(spec, req)

    # Response schema fields (200)
    resp = op.get("responses", {}).get("200", {}).get("content", {}).get("application/json", {}).get("schema", {})
    if resp:
        if "anyOf" in resp:
            resp = resolve_ref(spec, resp["anyOf"][0]["$ref"]) if "$ref" in resp["anyOf"][0] else resp["anyOf"][0]
        elif "$ref" in resp:
            resp = resolve_ref(spec, resp["$ref"])
        info["response_fields"] = schema_summary(spec, resp)

    return info


def build_bundle(spec: dict) -> dict[str, Any]:
    """Combine OpenAPI extractions with templates into the final bundle."""
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from docs_templates import TEMPLATES  # type: ignore

    docs: dict[str, Any] = {}
    for topic, (summary, langs) in TEMPLATES.items():
        entry: dict[str, Any] = {"summary": summary, "languages": langs}
        api_path = TOPIC_TO_PATH.get(topic)
        if api_path:
            entry.update(extract_endpoint_info(spec, api_path))
        docs[topic] = entry

    return {
        "META": {
            "openapi_version": spec.get("openapi"),
            "api_title": spec.get("info", {}).get("title"),
            "api_version": spec.get("info", {}).get("version"),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "source": OPENAPI_URL,
            "topics": sorted(docs.keys()),
            "languages": ["node", "python", "http"],
        },
        "DOCS": docs,
    }


def write_bundle(bundle: dict[str, Any], path: Path) -> None:
    """Write the bundle as a Python module with literal dicts."""
    import pprint

    header = '''"""Reducto documentation bundle for the get_documentation MCP tool.

GENERATED FILE — do not edit by hand.
Run: `uv run python scripts/update_reducto_docs.py` (or use the
`/update-documentation` skill) to regenerate from the OpenAPI spec
and the templates in scripts/docs_templates.py.
"""
from __future__ import annotations

'''

    pp = pprint.PrettyPrinter(indent=2, width=120, sort_dicts=False)
    body = f"META = {pp.pformat(bundle['META'])}\n\nDOCS = {pp.pformat(bundle['DOCS'])}\n"

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(header + body)
    print(f"wrote {path} ({path.stat().st_size:,} bytes)")


def main() -> None:
    spec = fetch_openapi()
    bundle = build_bundle(spec)
    write_bundle(bundle, BUNDLE_PATH)
    print()
    print("topics in bundle:")
    for topic, entry in bundle["DOCS"].items():
        langs = list(entry.get("languages", {}).keys())
        endpoint = entry.get("endpoint", "(no endpoint)")
        print(f"  {topic:<12} {endpoint:<20} languages={langs}")


if __name__ == "__main__":
    main()
