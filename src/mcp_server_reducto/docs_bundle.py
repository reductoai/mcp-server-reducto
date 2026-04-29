"""Reducto documentation bundle for the get_documentation MCP tool.

GENERATED FILE — do not edit by hand.
Run: `uv run python scripts/update_reducto_docs.py` (or use the
`/update-documentation` skill) to regenerate from the OpenAPI spec
and the templates in scripts/docs_templates.py.
"""

from __future__ import annotations

META = {
    "openapi_version": "3.1.0",
    "api_title": "Reducto API",
    "api_version": "v1.11.66-20-gb7660dad9",
    "fetched_at": "2026-04-29T00:32:08.120022+00:00",
    "source": "https://platform.reducto.ai/openapi.json",
    "topics": ["auth", "classify", "edit", "extract", "parse", "quickstart", "split", "upload"],
    "languages": ["node", "python", "http"],
}

DOCS = {
    "quickstart": {
        "summary": "Install, auth, and your first Reducto call",
        "languages": {
            "node": "## Quickstart — Node.js\n"
            "\n"
            "```bash\n"
            "npm install reductoai\n"
            "```\n"
            "\n"
            "Auth: set `REDUCTO_API_KEY` in `.env.local`. Generated apps must read it "
            "from `process.env`.\n"
            "\n"
            "```typescript\n"
            "import Reducto, { toFile } from 'reductoai';\n"
            "import fs from 'fs';\n"
            "\n"
            "const client = new Reducto({ apiKey: process.env.REDUCTO_API_KEY });\n"
            "\n"
            "const bytes = fs.readFileSync('document.pdf');\n"
            "// toFile() is REQUIRED for byte uploads. Without it, upload returns a "
            "file_id\n"
            "// but the file is never stored, and parse/extract will 404.\n"
            "const file = await toFile(bytes, 'document.pdf');\n"
            "\n"
            "// SDK types declare `file: string | null` but the runtime accepts "
            "Uploadable.\n"
            "// The cast is required to satisfy TypeScript:\n"
            "const upload = await client.upload({ file: file as unknown as string });\n"
            "\n"
            "const result = await client.parse.run({ input: upload.file_id });\n"
            "console.log(`got ${result.result.chunks.length} chunks`);\n"
            "```\n",
            "python": "## Quickstart — Python\n"
            "\n"
            "```bash\n"
            "pip install reductoai\n"
            "```\n"
            "\n"
            "Auth: set `REDUCTO_API_KEY` in `.env`. The SDK reads it automatically.\n"
            "\n"
            "```python\n"
            "import reducto\n"
            "\n"
            "client = reducto.Reducto()  # reads REDUCTO_API_KEY from env\n"
            "\n"
            "with open('document.pdf', 'rb') as f:\n"
            "    upload = client.upload(file=f.read(), extension='.pdf')\n"
            "\n"
            "result = client.parse.run(input=upload.file_id)\n"
            'print(f"got {len(result.result.chunks)} chunks")\n'
            "```\n",
            "http": "## Quickstart — REST / cURL\n"
            "\n"
            "Auth: pass `Authorization: Bearer $REDUCTO_API_KEY` on every request.\n"
            "\n"
            "```bash\n"
            "# 1. upload\n"
            "UPLOAD=$(curl -s -X POST https://platform.reducto.ai/upload \\\n"
            '  -H "Authorization: Bearer $REDUCTO_API_KEY" \\\n'
            '  -F "file=@document.pdf")\n'
            "FILE_ID=$(echo $UPLOAD | jq -r .file_id)\n"
            "\n"
            "# 2. parse\n"
            "curl -X POST https://platform.reducto.ai/parse \\\n"
            '  -H "Authorization: Bearer $REDUCTO_API_KEY" \\\n'
            '  -H "Content-Type: application/json" \\\n'
            '  -d "{\\"input\\": \\"$FILE_ID\\"}"\n'
            "```\n"
            "\n"
            "The base URL is `https://platform.reducto.ai`. Endpoints: `/upload`, "
            "`/parse`, `/extract`, `/split`, `/edit`, `/classify`.\n",
        },
    },
    "parse": {
        "summary": "Parse",
        "languages": {
            "node": "## Parse — Node.js\n"
            "\n"
            "```typescript\n"
            "const result = await client.parse.run({\n"
            '  input: upload.file_id,         // or "https://..." or "jobid://<id>"\n'
            "  enhance: { agentic: [{ scope: 'text' }] },        // for handwriting/complex "
            "layouts\n"
            "  formatting: { table_output_format: 'md' },        // 'html' | 'md' | 'json' | "
            "'csv'\n"
            "  settings: { page_range: { start: 1, end: 5 } },\n"
            "});\n"
            "```\n"
            "\n"
            "Response branches on `result.result.type`:\n"
            "- `'full'` → `result.result.chunks` is inline (small/medium docs)\n"
            "- `'url'` → `result.result.url` is a presigned URL you must fetch (large docs)\n"
            "\n"
            "```typescript\n"
            "if (result.result.type === 'full') {\n"
            "  for (const chunk of result.result.chunks) console.log(chunk.content);\n"
            "} else {\n"
            "  const r = await fetch(result.result.url);\n"
            "  const data = await r.json();\n"
            "  // data.chunks\n"
            "}\n"
            "```\n"
            "\n"
            'Save `result.job_id` — pass `"jobid://<id>"` as `input` to extract/split to skip '
            "re-parsing.\n",
            "python": "## Parse — Python\n"
            "\n"
            "```python\n"
            "result = client.parse.run(\n"
            '    input=upload.file_id,                  # or "https://..." or '
            '"jobid://<id>"\n'
            '    enhance={"agentic": [{"scope": "text"}]},\n'
            '    formatting={"table_output_format": "md"},\n'
            '    settings={"page_range": {"start": 1, "end": 5}},\n'
            ")\n"
            "```\n"
            "\n"
            "Response branches on `result.result.type`:\n"
            '- `"full"` → `result.result.chunks` is inline\n'
            '- `"url"` → `result.result.url` is a presigned URL you must fetch\n'
            "\n"
            "```python\n"
            'if result.result.type == "full":\n'
            "    for chunk in result.result.chunks:\n"
            "        print(chunk.content)\n"
            "else:\n"
            "    import requests\n"
            '    chunks = requests.get(result.result.url).json()["chunks"]\n'
            "```\n"
            "\n"
            'Save `result.job_id` — pass `f"jobid://{result.job_id}"` to extract/split to '
            "skip re-parsing.\n",
            "http": "## Parse — REST\n"
            "\n"
            "```bash\n"
            "curl -X POST https://platform.reducto.ai/parse \\\n"
            '  -H "Authorization: Bearer $REDUCTO_API_KEY" \\\n'
            '  -H "Content-Type: application/json" \\\n'
            "  -d '{\n"
            '    "input": "reducto://abc123.pdf",\n'
            '    "enhance": {"agentic": [{"scope": "text"}]},\n'
            '    "formatting": {"table_output_format": "md"},\n'
            '    "settings": {"page_range": {"start": 1, "end": 5}}\n'
            "  }'\n"
            "```\n"
            "\n"
            'Response: `{job_id, result: {type: "full"|"url", chunks?: [...], url?: "..."}}`. '
            "Branch on `result.type`. For large docs you must GET `result.url` to fetch "
            "chunks.\n",
        },
        "endpoint": "POST /parse",
        "description": "",
        "request_fields": {
            "input": "() For parse/split/extract pipelines, the URL of the document to be "
            "processed. You can provide one of the following:\n"
            "            1. A publicly available URL\n"
            "            2. A presigned S3 URL\n"
            "         ",
            "enhance": "(Enhance)",
            "retrieval": "(Retrieval)",
            "formatting": "(Formatting)",
            "spreadsheet": "(Spreadsheet)",
            "settings": "(Settings)",
        },
        "response_fields": {
            "job_id": "(string)",
            "duration": "(number) The duration of the parse request in seconds.",
            "pdf_url": "() The storage URL of the converted PDF file.",
            "studio_link": "() The link to the studio pipeline for the document.",
            "usage": "(ParseUsage)",
            "result": "() The response from the document processing service. Note that there can "
            "be two types of responses, Full Result and URL Result. This is due to "
            "limitations on the max return size on HTTPS. If the resp",
        },
    },
    "extract": {
        "summary": "Extract",
        "languages": {
            "node": "## Extract — Node.js\n"
            "\n"
            "Schema-driven JSON extraction. Pass a JSON Schema in `instructions.schema`.\n"
            "\n"
            "```typescript\n"
            "const result = await client.extract.run({\n"
            '  input: upload.file_id,                  // or "jobid://<parse_job_id>" to '
            "reuse a parse\n"
            "  instructions: {\n"
            "    schema: {\n"
            "      type: 'object',\n"
            "      properties: {\n"
            "        vendor: { type: 'string' },\n"
            "        total: { type: 'number' },\n"
            "        date: { type: 'string' },\n"
            "      },\n"
            "      required: ['vendor', 'total'],\n"
            "    },\n"
            "  },\n"
            "  settings: {\n"
            "    array_extract: { enabled: true },     // for line items / repeating rows\n"
            "    citations: { enabled: true },         // attach source page/bbox to each "
            "value\n"
            "  },\n"
            "});\n"
            "\n"
            "const data = Array.isArray(result.result) ? result.result[0] : result.result;\n"
            'console.log(data);  // { vendor: "...", total: 42, date: "..." }\n'
            "```\n"
            "\n"
            "Extract runs parse internally. If parse can't see the value (e.g. handwriting "
            "without `agentic`), extract can't find it either.\n",
            "python": "## Extract — Python\n"
            "\n"
            "```python\n"
            "result = client.extract.run(\n"
            '    input=upload.file_id,                  # or f"jobid://{parse_job_id}"\n'
            "    instructions={\n"
            '        "schema": {\n'
            '            "type": "object",\n'
            '            "properties": {\n'
            '                "vendor": {"type": "string"},\n'
            '                "total": {"type": "number"},\n'
            '                "date": {"type": "string"},\n'
            "            },\n"
            '            "required": ["vendor", "total"],\n'
            "        },\n"
            "    },\n"
            "    settings={\n"
            '        "array_extract": {"enabled": True},\n'
            '        "citations": {"enabled": True},\n'
            "    },\n"
            ")\n"
            "\n"
            "data = result.result[0] if isinstance(result.result, list) else "
            "result.result\n"
            "print(data)\n"
            "```\n",
            "http": "## Extract — REST\n"
            "\n"
            "```bash\n"
            "curl -X POST https://platform.reducto.ai/extract \\\n"
            '  -H "Authorization: Bearer $REDUCTO_API_KEY" \\\n'
            '  -H "Content-Type: application/json" \\\n'
            "  -d '{\n"
            '    "input": "reducto://abc123.pdf",\n'
            '    "instructions": {\n'
            '      "schema": {\n'
            '        "type": "object",\n'
            '        "properties": {\n'
            '          "vendor": {"type": "string"},\n'
            '          "total": {"type": "number"}\n'
            "        },\n"
            '        "required": ["vendor", "total"]\n'
            "      }\n"
            "    },\n"
            '    "settings": {"array_extract": {"enabled": true}}\n'
            "  }'\n"
            "```\n"
            "\n"
            "Response: `{job_id, result: {...} | [{...}]}`. Result may be a single object or "
            "an array depending on the schema.\n",
        },
        "endpoint": "POST /extract",
        "description": "",
        "request_fields": {
            "input": "() For parse/split/extract pipelines, the URL of the document to be "
            "processed. You can provide one of the following:\n"
            "            1. A publicly available URL\n"
            "            2. A presigned S3 URL\n"
            "         ",
            "parsing": "(ParseOptions) The configuration options for parsing the document. If "
            "you are passing in a jobid:// URL for the file, then this configuration "
            "will be ignored.",
            "instructions": "(Instructions) The instructions to use for the extraction.",
            "settings": "(ExtractSettings) The settings to use for the extraction.",
        },
        "response_fields": {},
    },
    "split": {
        "summary": "Split",
        "languages": {
            "node": "## Split — Node.js\n"
            "\n"
            "Segment a document into named sections.\n"
            "\n"
            "```typescript\n"
            "const result = await client.split.run({\n"
            '  input: upload.file_id,                  // or "jobid://<parse_job_id>"\n'
            "  split_description: [\n"
            "    { name: 'Terms', description: 'Terms and conditions section' },\n"
            "    { name: 'Pricing', description: 'Pricing tables and totals' },\n"
            "  ],\n"
            "  split_rules: 'Split at major section headings. Each section gets one entry.',\n"
            "});\n"
            "\n"
            "for (const section of result.result.splits) {\n"
            "  console.log(`${section.name}: pages ${section.pages.join(',')} (conf: "
            "${section.confidence})`);\n"
            "}\n"
            "```\n"
            "\n"
            "If you expect multiple sections but get one, refine `split_description` (richer "
            "descriptions) or `split_rules`.\n",
            "python": "## Split — Python\n"
            "\n"
            "```python\n"
            "result = client.split.run(\n"
            "    input=upload.file_id,\n"
            "    split_description=[\n"
            '        {"name": "Terms", "description": "Terms and conditions section"},\n'
            '        {"name": "Pricing", "description": "Pricing tables and totals"},\n'
            "    ],\n"
            '    split_rules="Split at major section headings.",\n'
            ")\n"
            "\n"
            "for section in result.result.splits:\n"
            '    print(f"{section.name}: pages {section.pages} (conf: '
            '{section.confidence})")\n'
            "```\n",
            "http": "## Split — REST\n"
            "\n"
            "```bash\n"
            "curl -X POST https://platform.reducto.ai/split \\\n"
            '  -H "Authorization: Bearer $REDUCTO_API_KEY" \\\n'
            '  -H "Content-Type: application/json" \\\n'
            "  -d '{\n"
            '    "input": "reducto://abc123.pdf",\n'
            '    "split_description": [\n'
            '      {"name": "Terms", "description": "Terms and conditions"},\n'
            '      {"name": "Pricing", "description": "Pricing tables"}\n'
            "    ],\n"
            '    "split_rules": "Split at major section headings."\n'
            "  }'\n"
            "```\n",
        },
        "endpoint": "POST /split",
        "description": "",
        "request_fields": {
            "input": "() For parse/split/extract pipelines, the URL of the document to be "
            "processed. You can provide one of the following:\n"
            "            1. A publicly available URL\n"
            "            2. A presigned S3 URL\n"
            "         ",
            "parsing": "(ParseOptions) The configuration options for parsing the document. If you "
            "are passing in a jobid:// URL for the file, then this configuration will "
            "be ignored.",
            "split_description": "(array<SplitCategory>) The configuration options for processing the document.",
            "split_rules": "(string) The prompt that describes rules for splitting the document.",
            "settings": "(SplitTableOptions) The settings for split processing.",
        },
        "response_fields": {"usage": "(ParseUsage)", "result": "() The split result."},
    },
    "edit": {
        "summary": "Edit",
        "languages": {
            "node": "## Edit — Node.js\n"
            "\n"
            "Fill PDF forms or modify documents via natural language.\n"
            "\n"
            "```typescript\n"
            "// First edit on a document — discover the form\n"
            "const first = await client.edit.run({\n"
            "  document_url: upload.file_id,\n"
            "  edit_instructions: 'Fill Name with Jane Doe and Date with 2025-01-15',\n"
            "});\n"
            "\n"
            "// IMPORTANT: cache first.form_schema for subsequent edits to the SAME document.\n"
            "// Without this, the model rediscovers the form layout each time (slow + less "
            "accurate).\n"
            "const cachedSchema = first.form_schema;\n"
            "\n"
            "const second = await client.edit.run({\n"
            "  document_url: upload.file_id,\n"
            "  edit_instructions: 'Now fill Signature with X',\n"
            "  options: { form_schema: cachedSchema },\n"
            "});\n"
            "\n"
            "console.log(second.document_url);  // download the edited PDF\n"
            "```\n",
            "python": "## Edit — Python\n"
            "\n"
            "```python\n"
            "# First edit — discover the form\n"
            "first = client.edit.run(\n"
            "    document_url=upload.file_id,\n"
            '    edit_instructions="Fill Name with Jane Doe and Date with 2025-01-15",\n'
            ")\n"
            "\n"
            "# Cache form_schema for subsequent edits on the same document\n"
            "cached = first.form_schema\n"
            "\n"
            "second = client.edit.run(\n"
            "    document_url=upload.file_id,\n"
            '    edit_instructions="Now fill Signature with X",\n'
            '    options={"form_schema": cached},\n'
            ")\n"
            "\n"
            "print(second.document_url)\n"
            "```\n",
            "http": "## Edit — REST\n"
            "\n"
            "```bash\n"
            "# First edit\n"
            "RESP=$(curl -s -X POST https://platform.reducto.ai/edit \\\n"
            '  -H "Authorization: Bearer $REDUCTO_API_KEY" \\\n'
            '  -H "Content-Type: application/json" \\\n'
            '  -d \'{"document_url": "reducto://abc.pdf", "edit_instructions": "Fill Name with '
            "Jane Doe\"}')\n"
            "\n"
            "# Cache form_schema, pass it on subsequent edits\n"
            "SCHEMA=$(echo $RESP | jq .form_schema)\n"
            "\n"
            "curl -X POST https://platform.reducto.ai/edit \\\n"
            '  -H "Authorization: Bearer $REDUCTO_API_KEY" \\\n'
            '  -H "Content-Type: application/json" \\\n'
            '  -d "{\n'
            '    \\"document_url\\": \\"reducto://abc.pdf\\",\n'
            '    \\"edit_instructions\\": \\"Now fill Signature with X\\",\n'
            '    \\"options\\": {\\"form_schema\\": $SCHEMA}\n'
            '  }"\n'
            "```\n",
        },
        "endpoint": "POST /edit",
        "description": "",
        "request_fields": {
            "document_url": "() The URL of the document to be processed. You can provide one of "
            "the following:\n"
            "1. A publicly available URL\n"
            "2. A presigned S3 URL\n"
            "3. A reducto:// prefixed URL obtained from the /upload endpoint afte",
            "edit_instructions": "(string) The instructions for the edit.",
            "edit_options": "(EditOptions)",
            "form_schema": "() Form schema for PDF forms. List of widgets with their types, "
            "descriptions, and bounding boxes. Only works for PDFs.",
            "priority": "(boolean) If True, attempts to process the job with priority if the user "
            "has priority processing budget available; by default, sync jobs are "
            "prioritized above async jobs.",
        },
        "response_fields": {
            "document_url": "(string) Presigned URL to download the edited document.",
            "form_schema": "() Form schema for PDF forms. List of widgets with their types, "
            "descriptions, and bounding boxes.",
            "usage": "() Usage information for the edit operation, including number of pages and credits charged.",
        },
    },
    "upload": {
        "summary": "Upload",
        "languages": {
            "node": "## Upload — Node.js\n"
            "\n"
            "```typescript\n"
            "import Reducto, { toFile } from 'reductoai';\n"
            "import fs from 'fs';\n"
            "\n"
            "const client = new Reducto({ apiKey: process.env.REDUCTO_API_KEY });\n"
            "\n"
            "// FROM A FILE PATH:\n"
            "const upload1 = await client.upload({\n"
            "  file: fs.createReadStream('document.pdf') as unknown as string,\n"
            "});\n"
            "\n"
            "// FROM BYTES (e.g. from request.formData()):\n"
            "const bytes = Buffer.from(await file.arrayBuffer());\n"
            "const wrapped = await toFile(bytes, file.name);\n"
            "const upload2 = await client.upload({ file: wrapped as unknown as string });\n"
            "\n"
            'console.log(upload2.file_id);  // "reducto://abc123.pdf" — pass to other tools\n'
            "```\n"
            "\n"
            "CRITICAL gotcha: the SDK declares `UploadParams.file: string | null` but the "
            "runtime\n"
            "accepts an `Uploadable`. Without `toFile()` for byte input, upload returns a\n"
            "file_id but the file is never stored — every downstream call 404s.\n"
            "\n"
            "The `as unknown as string` cast satisfies TypeScript without changing runtime "
            "behavior.\n",
            "python": "## Upload — Python\n"
            "\n"
            "```python\n"
            "import reducto\n"
            "\n"
            "client = reducto.Reducto()\n"
            "\n"
            "# FROM A FILE PATH:\n"
            "with open('document.pdf', 'rb') as f:\n"
            "    upload = client.upload(file=f.read(), extension='.pdf')\n"
            "\n"
            "# OR from bytes directly:\n"
            "upload = client.upload(file=pdf_bytes, extension='.pdf')\n"
            "\n"
            'print(upload.file_id)  # "reducto://abc123.pdf"\n'
            "```\n"
            "\n"
            "The Python SDK accepts raw bytes directly. No wrapper needed.\n",
            "http": "## Upload — REST\n"
            "\n"
            "```bash\n"
            "curl -X POST https://platform.reducto.ai/upload \\\n"
            '  -H "Authorization: Bearer $REDUCTO_API_KEY" \\\n'
            '  -F "file=@document.pdf"\n'
            "```\n"
            "\n"
            'Response: `{"file_id": "reducto://abc123.pdf"}`. Pass `file_id` as `input` to '
            "other endpoints.\n",
        },
        "endpoint": "POST /upload",
        "description": "",
        "request_fields": {"file": "()"},
        "response_fields": {"file_id": "(string)", "presigned_url": "()"},
    },
    "classify": {
        "summary": "Classify",
        "languages": {
            "node": "## Classify — Node.js\n"
            "\n"
            "```typescript\n"
            "const result = await client.classify.run({\n"
            "  document_url: upload.file_id,\n"
            "  categories: [\n"
            "    { category: 'invoice', criteria: ['has billing info', 'has line items'] "
            "},\n"
            "    { category: 'contract', criteria: ['has legal terms', 'has signatures'] "
            "},\n"
            "  ],\n"
            "});\n"
            "\n"
            "console.log(result.result.category);              // top match\n"
            "console.log(result.result.category_confidences);  // all categories with "
            "scores\n"
            "```\n",
            "python": "## Classify — Python\n"
            "\n"
            "```python\n"
            "result = client.classify.run(\n"
            "    document_url=upload.file_id,\n"
            "    categories=[\n"
            '        {"category": "invoice", "criteria": ["has billing info", "has line '
            'items"]},\n'
            '        {"category": "contract", "criteria": ["has legal terms", "has '
            'signatures"]},\n'
            "    ],\n"
            ")\n"
            "\n"
            "print(result.result.category)\n"
            "print(result.result.category_confidences)\n"
            "```\n",
            "http": "## Classify — REST\n"
            "\n"
            "```bash\n"
            "curl -X POST https://platform.reducto.ai/classify \\\n"
            '  -H "Authorization: Bearer $REDUCTO_API_KEY" \\\n'
            '  -H "Content-Type: application/json" \\\n'
            "  -d '{\n"
            '    "document_url": "reducto://abc.pdf",\n'
            '    "categories": [\n'
            '      {"category": "invoice", "criteria": ["has billing info"]},\n'
            '      {"category": "contract", "criteria": ["has legal terms"]}\n'
            "    ]\n"
            "  }'\n"
            "```\n",
        },
        "endpoint": "POST /classify",
        "description": "",
        "request_fields": {
            "persist_results": "(boolean) If True, persist the results indefinitely. Defaults to False.",
            "input": "() For parse/split/extract pipelines, the URL of the document to be "
            "processed. You can provide one of the following:\n"
            "            1. A publicly available URL\n"
            "            2. A presigned S3 URL\n"
            "         ",
            "classification_schema": "(array<ClassificationCategory>) A list of classification "
            "categories and their matching criteria.",
            "page_range": "() The page range to process (1-indexed). By default, the first 5 "
            "pages are used. If more than 25 pages are selected, only the first "
            "25 (after sorting) are used. Only applies to PDFs; ignored for othe",
            "document_metadata": "() Optional document-level metadata to include in classification prompts.",
        },
        "response_fields": {
            "job_id": "(string)",
            "result": "(ClassifyResponseCategory)",
            "response_confidence": "()",
            "duration": "() The duration of the classify request in seconds.",
        },
    },
    "auth": {
        "summary": "Authentication setup for generated apps",
        "languages": {
            "node": "## Auth — Node.js\n"
            "\n"
            "The Reducto SDK reads `REDUCTO_API_KEY` from environment. Generated apps need this "
            "in `.env.local`:\n"
            "\n"
            "```\n"
            "REDUCTO_API_KEY=your_key_here\n"
            "```\n"
            "\n"
            "```typescript\n"
            "// Either via env (preferred):\n"
            "const client = new Reducto();  // reads REDUCTO_API_KEY automatically\n"
            "\n"
            "// Or explicitly:\n"
            "const client = new Reducto({ apiKey: process.env.REDUCTO_API_KEY });\n"
            "```\n"
            "\n"
            "Do NOT hardcode keys in source. Do NOT parse `~/.reducto/config.yaml` from app "
            "code (that's the MCP server's path, not your app's).\n",
            "python": "## Auth — Python\n"
            "\n"
            "The Python SDK reads `REDUCTO_API_KEY` from environment.\n"
            "\n"
            "```python\n"
            "# Set in .env:\n"
            "# REDUCTO_API_KEY=your_key_here\n"
            "\n"
            "import reducto\n"
            "client = reducto.Reducto()  # reads REDUCTO_API_KEY automatically\n"
            "\n"
            "# Or explicitly:\n"
            "import os\n"
            'client = reducto.Reducto(api_key=os.environ["REDUCTO_API_KEY"])\n'
            "```\n"
            "\n"
            "Do NOT hardcode keys in source. Do NOT parse `~/.reducto/config.yaml` from app "
            "code.\n",
            "http": "## Auth — REST\n"
            "\n"
            "Every request needs the `Authorization: Bearer <key>` header.\n"
            "\n"
            "```bash\n"
            'export REDUCTO_API_KEY="your_key_here"\n'
            "\n"
            'curl -H "Authorization: Bearer $REDUCTO_API_KEY" https://platform.reducto.ai/...\n'
            "```\n"
            "\n"
            "Set `REDUCTO_API_KEY` in your shell or load from `.env`. Do NOT hardcode in "
            "source.\n",
        },
    },
}
