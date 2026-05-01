# mcp-server-reducto

MCP server for the [Reducto](https://reducto.ai) document processing API. Gives any MCP-compatible agent (Claude Desktop, Cursor, VS Code, Windsurf, OpenAI Agents SDK, etc.) native document processing capabilities — parse PDFs, extract structured data, split documents, classify, and edit forms.

## Prerequisites

1. **Python 3.11+** — required for the MCP SDK
2. **uv** (recommended) — for fast dependency management. Install: `curl -LsSf https://astral.sh/uv/install.sh | sh`

## Quick Start

### Option A: Remote server (easiest — no install)

Use the hosted server at `mcp.reducto.ai`. No Python, no local install — just add your API key:

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

Get your API key at [app.reducto.ai](https://studio.reducto.ai/api-keys).

### Option B: Local server (runs on your machine)

#### 1. Authenticate (one-time)

```bash
# Opens your browser — click to approve, and you're done.
uvx mcp-server-reducto --login
```

This saves your API key to `~/.reducto/config.yaml`. If you already use the [Reducto CLI](https://github.com/reductoai/reducto-cli) (`reducto login`), you're already authenticated — the MCP server shares the same credential store.

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

> **Alternatively**, if you prefer to pass the key explicitly (e.g., CI environments, shared machines), you can still use the `env` field:
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

### HTTP Transport (Remote Deployment)

For shared/remote deployments, run the server in HTTP mode:

```bash
REDUCTO_API_KEY=your-key \
REDUCTO_MCP_TRANSPORT=http \
REDUCTO_MCP_PORT=8000 \
mcp-server-reducto
```

Then connect MCP clients to `http://your-host:8000/mcp`.

## Tools

### `parse_document`

Parse a document into structured text, tables, and figures. Supports PDFs, images, spreadsheets, and 30+ formats.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `document_url` | string | Yes | URL, `reducto://`, or `jobid://` reference |
| `table_output_format` | string | No | `html`, `json`, `md`, `csv`, `dynamic` (default: `dynamic`) |
| `page_range` | string | No | e.g. `"1-5"` or `"3,7,10-12"` |
| `chunk_mode` | string | No | `disabled`, `variable`, `section`, `page` |
| `agentic` | list[string] | No | Enable agentic modes: `["table", "figure", "text", "layout"]` |
| `add_page_markers` | bool | No | Add page boundary markers |
| `return_images` | list[string] | No | `["figure", "table", "page"]` |
| `options` | dict/string | No | Full `ParseOptions` override (accepts JSON string) |

### `extract_data`

Extract structured data from a document using a JSON schema.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `document_url` | string | Yes | Accepts `jobid://` to skip re-parsing |
| `schema` | dict/string | Yes | JSON Schema describing target fields |
| `system_prompt` | string | No | Custom extraction instructions |
| `citations` | bool | No | Include source references |
| `array_extract` | bool | No | For repeating items (invoices, tables) |
| `deep_extract` | bool | No | Iterative agentic refinement |
| `include_images` | bool | No | Add page images to LLM context |
| `page_range` | string | No | Limit pages to process |
| `options` | dict/string | No | Full `ExtractOptions` override |

### `split_document`

Segment a document into labeled sections by topic.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `document_url` | string | Yes | Document to split |
| `categories` | list/string | Yes | `[{"name": "...", "description": "..."}]` |
| `split_rules` | string | No | Natural language splitting guidance |
| `page_range` | string | No | Limit pages |
| `options` | dict/string | No | Full `SplitOptions` override |

### `classify_document`

Categorize a document into one of the provided categories.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `document_url` | string | Yes | Document to classify |
| `categories` | list/string | Yes | `[{"category": "...", "criteria": ["..."]}]` |
| `page_range` | string | No | Default: first 5 pages |
| `document_metadata` | string | No | Additional context for classification |

### `edit_document`

Fill forms or modify a document (PDF/DOCX).

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `document_url` | string | Yes | Document to edit |
| `edit_instructions` | string | Yes | Natural language instructions |
| `options` | dict/string | No | `edit_options`, `form_schema`, `priority` |

### `upload_file`

Upload a file to Reducto's temporary storage (24-hour TTL).

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `file_url` | string | Yes | Public URL to fetch and store |

**Returns** a `reducto://` URL for use in other tools.

### `get_job`

Get status and result of a processing job.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `job_id` | string | Yes | Job ID from a previous tool call |

### `list_jobs`

List recent processing jobs.

**Parameters:**
| Name | Type | Required | Description |
|------|------|----------|-------------|
| `limit` | int | No | Max jobs to return (default: 10) |

## Usage Patterns

### Basic Parse

> "Parse this PDF and show me the content"
>
> The agent calls `parse_document(document_url="https://example.com/report.pdf")`

### Extract with Schema

> "Extract the invoice number, date, and total from this document"
>
> The agent calls `extract_data` with an appropriate JSON schema

### Chain Operations with `jobid://`

Parse once, then extract and split without re-processing:

1. `parse_document("https://example.com/report.pdf")` → returns `job_id: "abc123"`
2. `extract_data("jobid://abc123", schema={...})` → skips re-parsing
3. `split_document("jobid://abc123", categories=[...])` → skips re-parsing

### Handle Large Documents

Responses over 50KB are automatically truncated with guidance:

> "Response truncated (showing 20 of 150 blocks). Use get_job(job_id='abc123') for full results, or narrow with page_range."

## Authentication

The server resolves API keys in this order:

1. **`REDUCTO_API_KEY` environment variable** — highest priority, useful for CI or explicit config
2. **`~/.reducto/config.yaml`** — shared credential store with the Reducto CLI

To authenticate:

```bash
# Option A: Browser login (recommended)
mcp-server-reducto --login

# Option B: If you have the Reducto CLI
reducto login

# Option C: Set env var directly
export REDUCTO_API_KEY=your-key
```

Options A and B save the key to `~/.reducto/config.yaml` so you never need to set env vars.

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDUCTO_API_KEY` | No* | — | API key (or authenticate via `--login`) |
| `REDUCTO_BASE_URL` | No | `https://platform.reducto.ai` | For EU (`https://eu.reducto.ai`) or on-prem deployments |
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
- Environment fingerprint on every event: client name and version, transport (`stdio` or `hosted`), Python version, OS platform.

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

### Logs

The server logs to stderr (never stdout — that's the MCP transport). Set `LOG_LEVEL=DEBUG` for verbose output.

### Common Issues

- **"No Reducto API key found"** — run `mcp-server-reducto --login` to authenticate, or set `REDUCTO_API_KEY`
- **Tools not appearing** — restart your MCP client after config changes; test the server directly with `mcp-server-reducto` in your terminal
- **Timeout errors on large documents** — increase `REDUCTO_MCP_TIMEOUT` or use `page_range` to process fewer pages

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
