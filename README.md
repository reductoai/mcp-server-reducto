<p align="center">
  <a href="https://reducto.ai">
    <img src="assets/reducto-logo.svg" alt="Reducto" width="320" />
  </a>
</p>

<h1 align="center">Reducto MCP Server</h1>

<p align="center">
  <strong>The complete agentic document platform — wired into your MCP client.</strong><br/>
  Parse, extract, classify, split, and edit documents from any MCP-compatible agent, backed by the platform leading AI teams use in production.
</p>

<p align="center">
  <a href="https://pypi.org/project/mcp-server-reducto/"><img src="https://img.shields.io/pypi/v/mcp-server-reducto.svg?color=9D17A0" alt="PyPI version" /></a>
  <a href="https://pypi.org/project/mcp-server-reducto/"><img src="https://img.shields.io/pypi/pyversions/mcp-server-reducto.svg" alt="Python versions" /></a>
  <a href="https://github.com/reductoai/mcp-server-reducto/blob/main/LICENSE"><img src="https://img.shields.io/pypi/l/mcp-server-reducto.svg" alt="License" /></a>
  <a href="https://modelcontextprotocol.io"><img src="https://img.shields.io/badge/MCP-compatible-blue" alt="MCP compatible" /></a>
</p>

---

## What is Reducto?

[Reducto](https://reducto.ai) is the agentic document platform for leading AI teams who need enterprise performance at scale. **Billions of pages** processed and counting for teams like Harvey, Scale AI, Vanta, and Toast. We provide a comprehensive toolkit for working with documents the way a human would — combining custom in-house and frontier models to handle messy real-world inputs (scanned PDFs, handwritten forms, dense financial filings, multi-language contracts, faxed medical records) and turn them into reliable, agent-ready output.

The platform is organized around three promises:

- **Performance for you** — zero-shot accuracy on long-tail complexity (tables, charts, figures, handwriting, scans), with 12+ models orchestrated under the hood and continuously updated so you don't have to chase the frontier.
- **Enterprise ready** — hosted, VPC, on-premises, and air-gapped deployment; SOC 2 and HIPAA compliant; zero data retention by default; autoscaling and custom SLAs for bursty production workloads.
- **Complete toolkit** — one platform covering the full lifecycle of document work — parse, extract, classify, split, edit, and more — across 30+ file types, not just PDFs.

The core APIs exposed through this MCP server:

- **Parse** — layout-aware OCR + VLM pipeline that captures text, tables, figures, and bounding boxes
- **Extract** — schema-driven structured data extraction with citations
- **Split** — segment multi-document files into individual units
- **Classify** — route incoming files into your own taxonomy
- **Edit** — fill forms and modify PDFs/DOCX without templates

If you're a developer or AI team building anything that touches documents — invoice automation, contract analysis, knowledge-base ingestion, claims processing, RAG over PDFs, agentic workflows over filings — Reducto handles the messy parts so you don't have to stitch together OCR, parsers, extractors, and form engines yourself.

## Why an MCP server?

The [Model Context Protocol](https://modelcontextprotocol.io) is the open standard for connecting AI agents to tools and data. This server lets any MCP-compatible client — Claude Desktop, Claude Code, Cursor, VS Code (Copilot), Windsurf, the OpenAI Agents SDK, and others — call Reducto's platform directly, so your agent gets every document task it needs (reading, understanding, extracting, routing, filling) handled by one toolkit, without writing glue code.

That means you can:

- **Drop document understanding into Claude Desktop** and ask plain-English questions about a 200-page 10-K, an invoice batch, or a stack of insurance claims.
- **Build agents in Cursor or VS Code** that read PDFs, extract structured fields, and write code against the result — all inside the same loop.
- **Skip boilerplate** when prototyping. The agent decides which tool to call, when to chain results, and how to handle paging — you just describe what you want.
- **Code against the latest API surface** — the server exposes a `get_documentation` tool that hands the agent up-to-date Reducto SDK examples, parameter shapes, and response formats on demand, so it doesn't have to fall back on stale training data.

### Example use cases

- *"Pull the vendor, line items, and total from every invoice in this folder."*
- *"Split this 1,200-page mortgage packet into the deed, appraisal, and disclosure sections."*
- *"Extract the effective date, parties, and termination clauses from each of these contracts, with citations."*
- *"Classify these scanned medical records by document type and flag anything that looks like a lab report."*
- *"Fill out this W-9 form using the company info from `vendor.json`."*
- *"Read this earnings deck and summarize the YoY revenue change for each business segment."*

## Prerequisites

1. **Python 3.11+** — required for the MCP SDK
2. **uv** (recommended) — for fast dependency management. Install: `curl -LsSf https://astral.sh/uv/install.sh | sh`

## Quick Start

### Option A: Remote server (easiest — no install)

Use the hosted server at `https://mcp.reducto.ai/mcp`. No Python, no local install — just add your API key:

```json
{
  "mcpServers": {
    "reducto": {
      "type": "http",
      "url": "https://mcp.reducto.ai/mcp",
      "headers": {
        "Authorization": "Bearer your-api-key"
      }
    }
  }
}
```

Get your API key at [studio.reducto.ai/api-keys](https://studio.reducto.ai/api-keys).

> **Heads up — `upload_file` and local paths.** The hosted server runs in the cloud, so it has no view of your local filesystem — `upload_file` will only accept public URLs when used through it. To upload files directly from your machine, use **Option B** below, or pre-upload via the [Reducto API](https://docs.reducto.ai) and pass the returned `reducto://` URL to the hosted server.

### Option B: Local server (runs on your machine)

#### 1. Authenticate (one-time)

```bash
# Opens your browser via OAuth device flow — click to approve, and you're done.
uvx mcp-server-reducto --login
```

This saves your API key to `~/.reducto/config.yaml`. If you already use the [Reducto CLI](https://docs.reducto.ai/cli) (`reducto login`), you're already authenticated — the MCP server shares the same credential store.

#### 2. Add to your MCP client

Once authenticated, your MCP client config needs **no API key** — the server reads it from `~/.reducto/config.yaml` automatically:

```json
{
  "mcpServers": {
    "reducto": {
      "command": "uvx",
      "args": ["mcp-server-reducto"]
    }
  }
}
```

That's it. See below for client-specific config file locations.

> **Alternatively**, if you prefer to pass the key explicitly (e.g., CI environments, shared machines), use the `env` field:
> ```json
> {
>   "mcpServers": {
>     "reducto": {
>       "command": "uvx",
>       "args": ["mcp-server-reducto"],
>       "env": { "REDUCTO_API_KEY": "your-api-key" }
>     }
>   }
> }
> ```

### Hosted vs local — which should I use?

| | **Hosted** (`mcp.reducto.ai`) | **Local** (`uvx mcp-server-reducto`) |
|---|---|---|
| Install | None | Python 3.11+, `uvx` |
| Auth | Bearer token in headers | Browser login or env var |
| Local file uploads | ❌ public URLs only | ✅ pass paths directly |
| Shares creds with Reducto CLI | — | ✅ |
| Best for | Web/Studio users, quick demos | Desktop agents (Claude Desktop, Cursor, etc.) |

## Client Setup

### Claude Desktop

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "reducto": {
      "command": "uvx",
      "args": ["mcp-server-reducto"]
    }
  }
}
```

After saving, restart Claude Desktop. You should see "Reducto" in the MCP servers list.

### Claude Code

Add to your project's `.mcp.json` or `~/.claude/mcp.json`:

```json
{
  "mcpServers": {
    "reducto": {
      "command": "uvx",
      "args": ["mcp-server-reducto"]
    }
  }
}
```

### Cursor

Add to `.cursor/mcp.json` in your project root:

```json
{
  "mcpServers": {
    "reducto": {
      "command": "uvx",
      "args": ["mcp-server-reducto"]
    }
  }
}
```

### VS Code (Copilot)

Add to `.vscode/mcp.json` in your project root:

```json
{
  "servers": {
    "reducto": {
      "command": "uvx",
      "args": ["mcp-server-reducto"]
    }
  }
}
```

### Windsurf

Add to `~/.codeium/windsurf/mcp_config.json`:

```json
{
  "mcpServers": {
    "reducto": {
      "command": "uvx",
      "args": ["mcp-server-reducto"]
    }
  }
}
```

### HTTP Transport (single-tenant self-host)

To run the server in HTTP mode for shared local use:

```bash
REDUCTO_API_KEY=your-key \
REDUCTO_MCP_TRANSPORT=http \
REDUCTO_MCP_PORT=8000 \
mcp-server-reducto
```

Then connect MCP clients to `http://your-host:8000/mcp`.

## Concepts

A few small ideas to internalize before reading the tool reference. Most chained operations rely on these.

### Document URL schemes

Every `document_url` parameter accepts one of four schemes:

| Scheme | Meaning | Where it comes from |
|---|---|---|
| `https://` / `http://` | A public URL Reducto can fetch | You provide it |
| `reducto://` | A file in Reducto's temporary storage (24-hour TTL) | Returned by `upload_file` |
| `jobid://` | A reference to a previous processing job | Returned by `parse_document`, `extract_data`, `split_document`, `classify_document`, `edit_document` |

Anything else (`s3://`, `file://`, raw paths) will be rejected with a validation error. Use `upload_file` to bring in local files or to convert any input into a `reducto://` URL.

### Jobs and `jobid://` chaining

Every processing tool returns a `job_id` in its response. You can pass `jobid://<job_id>` as the `document_url` to a subsequent tool to reuse the work — no re-upload, no re-parse:

```
upload_file('./report.pdf')        →  reducto://abc       (file_id)
parse_document('reducto://abc')    →  jobid://xyz123      (job_id)
extract_data('jobid://xyz123', …)  →  reuses parsed text
split_document('jobid://xyz123', …)→  reuses parsed text
```

This is the cheapest and fastest way to run multiple operations against the same document.

### Response shape

Every tool returns a JSON-serialized object with a consistent set of fields. A representative parse response:

```json
{
  "job_id": "xyz123",
  "duration_seconds": 4.1,
  "studio_link": "https://studio.reducto.ai/jobs/xyz123",
  "usage": { "num_pages": 12, "credits": 12 },
  "num_blocks": 42,
  "block_type_counts": { "Text": 30, "Table": 6, "Figure": 6 },
  "blocks": [ … ],
  "next_steps": "Use jobid://xyz123 as document_url for extract_data, split_document, or classify_document."
}
```

Fields you'll see across most responses:

- **`job_id`** — pass to `get_job` later, or chain via `jobid://<job_id>`.
- **`studio_link`** — open in [Reducto Studio](https://studio.reducto.ai) to inspect the result visually. Great for debugging.
- **`usage`** — pages and credits consumed.
- **`next_steps`** — a hint the server adds describing the recommended follow-up call.

### Large or async results: `result_type: "url"`

When a result is too large to inline, Reducto returns a URL-backed result. You'll see this in the response payload:

```json
{
  "job_id": "xyz123",
  "result_type": "url",
  "result_url": "https://…",
  "result_access_warning": "Result content is URL-backed; call get_job(job_id='xyz123') before reading it."
}
```

**Recovery rule:** when `result_type` is `"url"`, call `get_job(job_id=...)` to fetch the materialized result before reading any fields. Don't try to read `result` directly.

### Response truncation

If a response (typically the `blocks` array from `parse_document`) exceeds `REDUCTO_MCP_MAX_RESPONSE_SIZE` (default 50,000 characters), the server truncates it and adds:

```json
{
  "truncated": true,
  "truncation_note": "Response truncated (showing 20 of 150 blocks). Use get_job(job_id='xyz123') for full results, or narrow with page_range."
}
```

**Recovery rule:** when `truncated: true` is present, call `get_job(job_id=...)` for the complete result, or re-run with a narrower `page_range`.

### The `options` escape hatch

Most tools accept an `options` parameter for any [Reducto API field](https://docs.reducto.ai) not directly exposed as a top-level argument. Two notes:

- **Top-level params win.** When a top-level argument and `options` set the same key, the top-level value takes precedence. Nested config dicts get a one-level shallow merge.
- **JSON strings are accepted.** Some MCP clients struggle to pass nested JSON; `options`, `schema`, and `categories` therefore all accept either a native object or a JSON-encoded string. Both work identically.

### Page range syntax

`page_range` accepts a string with **1-based** page numbers:

- `"1-5"` — pages 1 through 5
- `"3,7,10-12"` — pages 3, 7, 10, 11, and 12

## Tools

### Which tool to use

| If you need to… | Use |
|---|---|
| Look up working SDK / REST examples for any Reducto endpoint | `get_documentation` |
| Bring a local file or arbitrary URL into Reducto | `upload_file` |
| Get text, tables, figures, and layout from a document | `parse_document` |
| Pull specific fields into JSON using a schema | `extract_data` |
| Divide a document into named page-range sections | `split_document` |
| Categorize a document into one of N labels | `classify_document` |
| Fill a form or modify a PDF/DOCX | `edit_document` |
| Fetch a full, URL-backed, truncated, or async result | `get_job` |
| Inspect recent jobs | `list_jobs` |

### `get_documentation`

Return Reducto SDK and REST documentation — install commands, auth setup, working code examples, response shapes — for a specific topic. Recommended **before** writing any Reducto integration code so the agent works from current API surface, not training memory.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `topic` | string | Yes | One of: `quickstart`, `parse`, `extract`, `split`, `classify`, `edit`, `upload`, `auth` |
| `language` | string | No | `node`, `python`, or `http`. Omit to receive all three. |

### `parse_document`

Parse a document into structured text, tables, and figures. Supports PDFs, images, spreadsheets, DOCX, PPTX, and 30+ formats.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `document_url` | string | Yes | `https://`, `reducto://`, or `jobid://` URL |
| `table_output_format` | string | No | `html`, `json`, `md`, `csv`, `dynamic`, `jsonbbox` (default: `dynamic`) |
| `page_range` | string | No | e.g. `"1-5"` or `"3,7,10-12"` (1-based) |
| `chunk_mode` | string | No | `disabled`, `variable`, `section`, `page` — see [docs](https://docs.reducto.ai/api-reference/parse) |
| `agentic` | list[string] | No | Subset of `["text", "table", "figure", "layout"]`. Improves quality on hard documents (handwriting, complex tables). See [docs](https://docs.reducto.ai/api-reference/parse). |
| `add_page_markers` | bool | No | Insert page-boundary markers in the output |
| `return_images` | list[string] | No | Subset of `["figure", "table", "page"]` to return as images |
| `options` | dict / JSON string | No | Any other `ParseOptions` field |

### `extract_data`

Extract structured data from a document using a JSON schema.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `document_url` | string | Yes | Pass `jobid://<parse_job_id>` to skip re-parsing |
| `schema` | dict / JSON string | Yes | JSON Schema describing the target fields |
| `system_prompt` | string | No | Custom extraction instructions |
| `citations` | bool | No | Include source references for each extracted field |
| `array_extract` | bool | No | Legacy flag for repeating items — prefer modeling the array directly in your schema |
| `deep_extract` | bool | No | Iterative agentic refinement for harder documents |
| `include_images` | bool | No | Add page images to the LLM context |
| `page_range` | string | No | Limit pages to process |
| `options` | dict / JSON string | No | Any other `ExtractOptions` field |

### `split_document`

Segment a document into labeled sections by topic. Returns each section's name, page range, and a confidence score.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `document_url` | string | Yes | Document to split |
| `categories` | list / JSON string | Yes | `[{"name": "Disclosures", "description": "Legal and risk disclosures"}, …]` |
| `split_rules` | string | No | Natural-language splitting guidance |
| `page_range` | string | No | Limit pages |
| `options` | dict / JSON string | No | Any other `SplitOptions` field |

### `classify_document`

Categorize a document into one of the provided categories.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `document_url` | string | Yes | Document to classify |
| `categories` | list / JSON string | Yes | `[{"category": "invoice", "criteria": ["has billing info", "has line items"]}, …]` |
| `page_range` | string | No | Default: first 5 pages |
| `document_metadata` | string | No | Additional context to bias classification |

### `edit_document`

Fill forms or modify a document (PDF/DOCX). Returns a download URL for the edited file plus a `form_schema` describing the fields it found.

**Form-filling pattern.** The first edit on a new form returns a `form_schema` and a hint:

```json
{
  "document_url": "https://…/edited.pdf",
  "form_schema": { … },
  "form_schema_note": "Cache this form_schema and pass it via options.form_schema for repeated edits."
}
```

For repeated edits to the same form template, cache the `form_schema` and pass it back via `options.form_schema` to skip re-detection.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `document_url` | string | Yes | Document to edit |
| `edit_instructions` | string | Yes | Natural-language instructions |
| `options` | dict / JSON string | No | `edit_options`, `form_schema`, `priority` |

### `upload_file`

Upload a document to Reducto's temporary storage (24-hour TTL) and get a `reducto://` URL for use in other tools.

**Accepts:**
- **Local file paths** — `./report.pdf`, `/Users/me/docs/x.pdf`, `~/inbox/y.pdf` (local server only).
- **Public URLs** — `https://example.com/report.pdf` (downloaded server-side, then uploaded).

> The hosted server (`mcp.reducto.ai`) does **not** support local paths. Use a public URL or run the server locally.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `file_url` | string | Yes | Local file path **or** public URL |

### `get_job`

Get the status and result of a previous processing job. Use this to fetch URL-backed results, full content for truncated responses, or to poll an async job.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `job_id` | string | Yes | Job ID returned by any processing tool |

### `list_jobs`

List recent processing jobs.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `limit` | int | No | Max jobs to return (default: 10) |

## Usage Patterns

### Basic parse

> "Parse this PDF and show me the content."
>
> The agent calls `parse_document(document_url="https://example.com/report.pdf")`.

### Extract with schema

> "Extract the invoice number, date, and total from this document."
>
> The agent calls `extract_data` with a JSON schema describing the three fields.

### End-to-end chain

A full workflow using `upload_file`, `parse_document`, and chained `extract_data`:

```text
1. upload_file("./contracts/q4-msa.pdf")
   → { "file_id": "reducto://abc", "next_steps": "Pass reducto://abc as document_url …" }

2. parse_document("reducto://abc", agentic=["text"])
   → { "job_id": "xyz123", "studio_link": "…", "next_steps": "Use jobid://xyz123 …" }

3. extract_data(
     "jobid://xyz123",
     schema={
       "type": "object",
       "properties": {
         "effective_date": {"type": "string"},
         "parties": {"type": "array", "items": {"type": "string"}},
         "termination_clauses": {"type": "array", "items": {"type": "string"}}
       },
       "required": ["effective_date", "parties"]
     },
     citations=True
   )
   → structured fields, with citations
```

The same `jobid://xyz123` can also be reused by `split_document` or `classify_document` without re-parsing.

### Triage a mixed document set

> "Classify each of these PDFs as `invoice`, `contract`, or `lab_report`, then run the right extraction schema for each."
>
> The agent calls `classify_document` per file, then routes each to `extract_data` with a category-specific schema.

### Fill a recurring form

> "Fill out a W-9 for each of these vendors using the data in `vendors.json`."
>
> First call: `edit_document(...)` returns a `form_schema`. Subsequent calls: pass the cached `form_schema` via `options` to skip re-detection.

### Handle large or async results

If a response includes `result_type: "url"`, **call `get_job` before reading fields**:

```text
parse_document("reducto://big-doc")
  → { "job_id": "j1", "result_type": "url", "result_url": "…",
      "result_access_warning": "Result content is URL-backed; call get_job(job_id='j1') before reading it." }
get_job(job_id="j1")
  → full materialized result
```

If a response includes `truncated: true`, either call `get_job(job_id=...)` for the full result or re-run with a narrower `page_range`.

## Authentication

The server resolves API keys in this order:

1. **`REDUCTO_API_KEY` environment variable** — highest priority. Useful for CI or explicit config.
2. **`~/.reducto/config.yaml`** — shared credential store with the Reducto CLI.

To authenticate:

```bash
# Option A: Browser login (recommended)
mcp-server-reducto --login

# Option B: If you have the Reducto CLI
reducto login

# Option C: Set env var directly
export REDUCTO_API_KEY=your-key
```

`--login` runs an OAuth device-code flow: it prints a code, opens your browser to the verification page, and waits for you to approve. Once approved, the key is written to `~/.reducto/config.yaml` (`chmod 600`). Use `--login --force` to replace an existing saved key.

The hosted server (`mcp.reducto.ai`) does not use this flow — pass your key as `Authorization: Bearer <key>` in your client config instead.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDUCTO_API_KEY` | No* | — | API key (or authenticate via `--login`) |
| `REDUCTO_BASE_URL` | No | `https://platform.reducto.ai` | Override the API base URL (EU region, on-prem) |
| `REDUCTO_MCP_MAX_RESPONSE_SIZE` | No | `50000` | Response truncation threshold in characters |
| `REDUCTO_MCP_TIMEOUT` | No | `300` | Request timeout in seconds |
| `REDUCTO_MCP_TRANSPORT` | No | `stdio` | Transport mode: `stdio` or `http` |
| `REDUCTO_MCP_PORT` | No | `8000` | Port when using HTTP transport |
| `REDUCTO_TELEMETRY` | No | `1` | Set to `0` to opt out of anonymous usage telemetry |

*Required only if you haven't run `mcp-server-reducto --login` or `reducto login`.

## Telemetry

The MCP server sends a small amount of anonymous usage telemetry to PostHog so we can understand which tools are used, how often, and from which transport. This helps us prioritize improvements.

**What we collect**

- Server lifecycle events: `mcp.installed` (once per machine, on first run) and `mcp.start` (once per server boot).
- Per-tool invocation events: `tool.<name>.invoked` with `tool` name, `status` (`ok`/`error`/`exception`), and `latency_ms`.
- Environment fingerprint on every event: product surface, client name and version, transport (`stdio` or `hosted`), Python version, OS platform.

**What we never collect**

- Tool arguments (document URLs, file IDs, schemas, prompts, page ranges).
- Tool responses or document content.
- API keys. The user identifier on each event is `sha256(api_key)[:16]`, which is one-way — there is no way to recover the key from an event.

**How to opt out**

Set `REDUCTO_TELEMETRY=0` in the environment that runs the MCP server. The server gracefully no-ops every PostHog call when this is set.

## Debugging

### MCP Inspector

Test the server interactively:

```bash
npx @modelcontextprotocol/inspector -- uvx mcp-server-reducto
```

This opens a web UI where you can discover tools, call them, and inspect responses. (Requires prior authentication via `--login`.)

### Studio links

Most parse and extract responses include a `studio_link` field — open it to inspect the same job interactively in [Reducto Studio](https://studio.reducto.ai). This is the fastest way to compare parser output side-by-side with the original document.

### Logs

The server logs to stderr (never stdout — that's the MCP transport). Set `LOG_LEVEL=DEBUG` for verbose output.

### Common Issues

- **"No Reducto API key found"** — run `mcp-server-reducto --login`, or set `REDUCTO_API_KEY` in your client config.
- **"Invalid URL scheme"** — `document_url` must start with `https://`, `http://`, `reducto://`, or `jobid://`. For local files, call `upload_file` first.
- **"Local file paths are not supported on the hosted server"** — switch to the local server (Option B) or pass a public URL.
- **Tools not appearing** — restart your MCP client after config changes; test the server directly with `mcp-server-reducto` in your terminal.
- **Timeout on large documents** — increase `REDUCTO_MCP_TIMEOUT`, or narrow with `page_range`.
- **Result not visible in the response** — check for `result_type: "url"` or `truncated: true` and follow the recovery rule (call `get_job(job_id=...)`).

## Development

```bash
# Clone and setup
git clone https://github.com/reductoai/mcp-server-reducto.git
cd mcp-server-reducto
uv sync

# Run unit tests (120 tests, <10s)
.venv/bin/python -m pytest tests/ -v --ignore=tests/integration

# Run integration tests (requires API key)
REDUCTO_API_KEY=your-key .venv/bin/python -m pytest tests/integration/ -v

# Lint
.venv/bin/ruff check src/ tests/
```

## Resources

- 📚 **Docs** — [docs.reducto.ai](https://docs.reducto.ai)
- 🧪 **Studio** — [studio.reducto.ai](https://studio.reducto.ai) (interactive playground for parse/extract/split/edit)
- 🛠️ **CLI** — [docs.reducto.ai/cli](https://docs.reducto.ai/cli)
- 🔑 **API keys** — [studio.reducto.ai/api-keys](https://studio.reducto.ai/api-keys)
- 🌐 **MCP spec** — [modelcontextprotocol.io](https://modelcontextprotocol.io)

---

<p align="center">
  <strong>Document work starts here.</strong><br/>
  Built by <a href="https://reducto.ai">Reducto</a> — we're hiring. <a href="https://x.com/reductoai">Follow @reductoai on X</a> · <a href="https://reducto.ai/careers">Open roles →</a>
</p>
