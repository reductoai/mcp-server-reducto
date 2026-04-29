"""Hand-written SDK templates for the Reducto docs bundle.

These contain language-specific patterns the OpenAPI spec doesn't express:
- Install commands
- Auth setup (.env vs reducto login)
- The Node SDK toFile() workaround for byte uploads
- form_schema caching pattern for edits
- jobid:// chaining

Combined with auto-extracted endpoint info (from openapi.json) by
update_reducto_docs.py to produce src/mcp_server_reducto/docs_bundle.py.

Update these by hand when SDK conventions change. The /update-documentation
skill does NOT regenerate this file — it only refreshes the OpenAPI portion.
"""

# Each topic maps to a per-language code example. The example is markdown
# with a fenced code block and short prose. Keep them concise — agents skim.

QUICKSTART = {
    "node": """## Quickstart — Node.js

```bash
npm install reductoai
```

Auth: set `REDUCTO_API_KEY` in `.env.local`. Generated apps must read it from `process.env`.

```typescript
import Reducto, { toFile } from 'reductoai';
import fs from 'fs';

const client = new Reducto({ apiKey: process.env.REDUCTO_API_KEY });

const bytes = fs.readFileSync('document.pdf');
// toFile() is REQUIRED for byte uploads. Without it, upload returns a file_id
// but the file is never stored, and parse/extract will 404.
const file = await toFile(bytes, 'document.pdf');

// SDK types declare `file: string | null` but the runtime accepts Uploadable.
// The cast is required to satisfy TypeScript:
const upload = await client.upload({ file: file as unknown as string });

const result = await client.parse.run({ input: upload.file_id });
console.log(`got ${result.result.chunks.length} chunks`);
```
""",

    "python": """## Quickstart — Python

```bash
pip install reductoai
```

Auth: set `REDUCTO_API_KEY` in `.env`. The SDK reads it automatically.

```python
import reducto

client = reducto.Reducto()  # reads REDUCTO_API_KEY from env

with open('document.pdf', 'rb') as f:
    upload = client.upload(file=f.read(), extension='.pdf')

result = client.parse.run(input=upload.file_id)
print(f"got {len(result.result.chunks)} chunks")
```
""",

    "http": """## Quickstart — REST / cURL

Auth: pass `Authorization: Bearer $REDUCTO_API_KEY` on every request.

```bash
# 1. upload
UPLOAD=$(curl -s -X POST https://platform.reducto.ai/upload \\
  -H "Authorization: Bearer $REDUCTO_API_KEY" \\
  -F "file=@document.pdf")
FILE_ID=$(echo $UPLOAD | jq -r .file_id)

# 2. parse
curl -X POST https://platform.reducto.ai/parse \\
  -H "Authorization: Bearer $REDUCTO_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d "{\\"input\\": \\"$FILE_ID\\"}"
```

The base URL is `https://platform.reducto.ai`. Endpoints: `/upload`, `/parse`, `/extract`, `/split`, `/edit`, `/classify`.
""",
}

PARSE = {
    "node": """## Parse — Node.js

```typescript
const result = await client.parse.run({
  input: upload.file_id,         // or "https://..." or "jobid://<id>"
  enhance: { agentic: [{ scope: 'text' }] },        // for handwriting/complex layouts
  formatting: { table_output_format: 'md' },        // 'html' | 'md' | 'json' | 'csv'
  settings: { page_range: { start: 1, end: 5 } },
});
```

Response branches on `result.result.type`:
- `'full'` → `result.result.chunks` is inline (small/medium docs)
- `'url'` → `result.result.url` is a presigned URL you must fetch (large docs)

```typescript
if (result.result.type === 'full') {
  for (const chunk of result.result.chunks) console.log(chunk.content);
} else {
  const r = await fetch(result.result.url);
  const data = await r.json();
  // data.chunks
}
```

Save `result.job_id` — pass `"jobid://<id>"` as `input` to extract/split to skip re-parsing.
""",

    "python": """## Parse — Python

```python
result = client.parse.run(
    input=upload.file_id,                  # or "https://..." or "jobid://<id>"
    enhance={"agentic": [{"scope": "text"}]},
    formatting={"table_output_format": "md"},
    settings={"page_range": {"start": 1, "end": 5}},
)
```

Response branches on `result.result.type`:
- `"full"` → `result.result.chunks` is inline
- `"url"` → `result.result.url` is a presigned URL you must fetch

```python
if result.result.type == "full":
    for chunk in result.result.chunks:
        print(chunk.content)
else:
    import requests
    chunks = requests.get(result.result.url).json()["chunks"]
```

Save `result.job_id` — pass `f"jobid://{result.job_id}"` to extract/split to skip re-parsing.
""",

    "http": """## Parse — REST

```bash
curl -X POST https://platform.reducto.ai/parse \\
  -H "Authorization: Bearer $REDUCTO_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "input": "reducto://abc123.pdf",
    "enhance": {"agentic": [{"scope": "text"}]},
    "formatting": {"table_output_format": "md"},
    "settings": {"page_range": {"start": 1, "end": 5}}
  }'
```

Response: `{job_id, result: {type: "full"|"url", chunks?: [...], url?: "..."}}`. Branch on `result.type`. For large docs you must GET `result.url` to fetch chunks.
""",
}

EXTRACT = {
    "node": """## Extract — Node.js

Schema-driven JSON extraction. Pass a JSON Schema in `instructions.schema`.

```typescript
const result = await client.extract.run({
  input: upload.file_id,                  // or "jobid://<parse_job_id>" to reuse a parse
  instructions: {
    schema: {
      type: 'object',
      properties: {
        vendor: { type: 'string' },
        total: { type: 'number' },
        date: { type: 'string' },
      },
      required: ['vendor', 'total'],
    },
  },
  settings: {
    array_extract: { enabled: true },     // for line items / repeating rows
    citations: { enabled: true },         // attach source page/bbox to each value
  },
});

const data = Array.isArray(result.result) ? result.result[0] : result.result;
console.log(data);  // { vendor: "...", total: 42, date: "..." }
```

Extract runs parse internally. If parse can't see the value (e.g. handwriting without `agentic`), extract can't find it either.
""",

    "python": """## Extract — Python

```python
result = client.extract.run(
    input=upload.file_id,                  # or f"jobid://{parse_job_id}"
    instructions={
        "schema": {
            "type": "object",
            "properties": {
                "vendor": {"type": "string"},
                "total": {"type": "number"},
                "date": {"type": "string"},
            },
            "required": ["vendor", "total"],
        },
    },
    settings={
        "array_extract": {"enabled": True},
        "citations": {"enabled": True},
    },
)

data = result.result[0] if isinstance(result.result, list) else result.result
print(data)
```
""",

    "http": """## Extract — REST

```bash
curl -X POST https://platform.reducto.ai/extract \\
  -H "Authorization: Bearer $REDUCTO_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "input": "reducto://abc123.pdf",
    "instructions": {
      "schema": {
        "type": "object",
        "properties": {
          "vendor": {"type": "string"},
          "total": {"type": "number"}
        },
        "required": ["vendor", "total"]
      }
    },
    "settings": {"array_extract": {"enabled": true}}
  }'
```

Response: `{job_id, result: {...} | [{...}]}`. Result may be a single object or an array depending on the schema.
""",
}

SPLIT = {
    "node": """## Split — Node.js

Segment a document into named sections.

```typescript
const result = await client.split.run({
  input: upload.file_id,                  // or "jobid://<parse_job_id>"
  split_description: [
    { name: 'Terms', description: 'Terms and conditions section' },
    { name: 'Pricing', description: 'Pricing tables and totals' },
  ],
  split_rules: 'Split at major section headings. Each section gets one entry.',
});

for (const section of result.result.splits) {
  console.log(`${section.name}: pages ${section.pages.join(',')} (conf: ${section.confidence})`);
}
```

If you expect multiple sections but get one, refine `split_description` (richer descriptions) or `split_rules`.
""",

    "python": """## Split — Python

```python
result = client.split.run(
    input=upload.file_id,
    split_description=[
        {"name": "Terms", "description": "Terms and conditions section"},
        {"name": "Pricing", "description": "Pricing tables and totals"},
    ],
    split_rules="Split at major section headings.",
)

for section in result.result.splits:
    print(f"{section.name}: pages {section.pages} (conf: {section.confidence})")
```
""",

    "http": """## Split — REST

```bash
curl -X POST https://platform.reducto.ai/split \\
  -H "Authorization: Bearer $REDUCTO_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "input": "reducto://abc123.pdf",
    "split_description": [
      {"name": "Terms", "description": "Terms and conditions"},
      {"name": "Pricing", "description": "Pricing tables"}
    ],
    "split_rules": "Split at major section headings."
  }'
```
""",
}

EDIT = {
    "node": """## Edit — Node.js

Fill PDF forms or modify documents via natural language.

```typescript
// First edit on a document — discover the form
const first = await client.edit.run({
  document_url: upload.file_id,
  edit_instructions: 'Fill Name with Jane Doe and Date with 2025-01-15',
});

// IMPORTANT: cache first.form_schema for subsequent edits to the SAME document.
// Without this, the model rediscovers the form layout each time (slow + less accurate).
const cachedSchema = first.form_schema;

const second = await client.edit.run({
  document_url: upload.file_id,
  edit_instructions: 'Now fill Signature with X',
  options: { form_schema: cachedSchema },
});

console.log(second.document_url);  // download the edited PDF
```
""",

    "python": """## Edit — Python

```python
# First edit — discover the form
first = client.edit.run(
    document_url=upload.file_id,
    edit_instructions="Fill Name with Jane Doe and Date with 2025-01-15",
)

# Cache form_schema for subsequent edits on the same document
cached = first.form_schema

second = client.edit.run(
    document_url=upload.file_id,
    edit_instructions="Now fill Signature with X",
    options={"form_schema": cached},
)

print(second.document_url)
```
""",

    "http": """## Edit — REST

```bash
# First edit
RESP=$(curl -s -X POST https://platform.reducto.ai/edit \\
  -H "Authorization: Bearer $REDUCTO_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{"document_url": "reducto://abc.pdf", "edit_instructions": "Fill Name with Jane Doe"}')

# Cache form_schema, pass it on subsequent edits
SCHEMA=$(echo $RESP | jq .form_schema)

curl -X POST https://platform.reducto.ai/edit \\
  -H "Authorization: Bearer $REDUCTO_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d "{
    \\"document_url\\": \\"reducto://abc.pdf\\",
    \\"edit_instructions\\": \\"Now fill Signature with X\\",
    \\"options\\": {\\"form_schema\\": $SCHEMA}
  }"
```
""",
}

UPLOAD = {
    "node": """## Upload — Node.js

```typescript
import Reducto, { toFile } from 'reductoai';
import fs from 'fs';

const client = new Reducto({ apiKey: process.env.REDUCTO_API_KEY });

// FROM A FILE PATH:
const upload1 = await client.upload({
  file: fs.createReadStream('document.pdf') as unknown as string,
});

// FROM BYTES (e.g. from request.formData()):
const bytes = Buffer.from(await file.arrayBuffer());
const wrapped = await toFile(bytes, file.name);
const upload2 = await client.upload({ file: wrapped as unknown as string });

console.log(upload2.file_id);  // "reducto://abc123.pdf" — pass to other tools
```

CRITICAL gotcha: the SDK declares `UploadParams.file: string | null` but the runtime
accepts an `Uploadable`. Without `toFile()` for byte input, upload returns a
file_id but the file is never stored — every downstream call 404s.

The `as unknown as string` cast satisfies TypeScript without changing runtime behavior.
""",

    "python": """## Upload — Python

```python
import reducto

client = reducto.Reducto()

# FROM A FILE PATH:
with open('document.pdf', 'rb') as f:
    upload = client.upload(file=f.read(), extension='.pdf')

# OR from bytes directly:
upload = client.upload(file=pdf_bytes, extension='.pdf')

print(upload.file_id)  # "reducto://abc123.pdf"
```

The Python SDK accepts raw bytes directly. No wrapper needed.
""",

    "http": """## Upload — REST

```bash
curl -X POST https://platform.reducto.ai/upload \\
  -H "Authorization: Bearer $REDUCTO_API_KEY" \\
  -F "file=@document.pdf"
```

Response: `{"file_id": "reducto://abc123.pdf"}`. Pass `file_id` as `input` to other endpoints.
""",
}

CLASSIFY = {
    "node": """## Classify — Node.js

```typescript
const result = await client.classify.run({
  document_url: upload.file_id,
  categories: [
    { category: 'invoice', criteria: ['has billing info', 'has line items'] },
    { category: 'contract', criteria: ['has legal terms', 'has signatures'] },
  ],
});

console.log(result.result.category);              // top match
console.log(result.result.category_confidences);  // all categories with scores
```
""",

    "python": """## Classify — Python

```python
result = client.classify.run(
    document_url=upload.file_id,
    categories=[
        {"category": "invoice", "criteria": ["has billing info", "has line items"]},
        {"category": "contract", "criteria": ["has legal terms", "has signatures"]},
    ],
)

print(result.result.category)
print(result.result.category_confidences)
```
""",

    "http": """## Classify — REST

```bash
curl -X POST https://platform.reducto.ai/classify \\
  -H "Authorization: Bearer $REDUCTO_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "document_url": "reducto://abc.pdf",
    "categories": [
      {"category": "invoice", "criteria": ["has billing info"]},
      {"category": "contract", "criteria": ["has legal terms"]}
    ]
  }'
```
""",
}

AUTH = {
    "node": """## Auth — Node.js

The Reducto SDK reads `REDUCTO_API_KEY` from environment. Generated apps need this in `.env.local`:

```
REDUCTO_API_KEY=your_key_here
```

```typescript
// Either via env (preferred):
const client = new Reducto();  // reads REDUCTO_API_KEY automatically

// Or explicitly:
const client = new Reducto({ apiKey: process.env.REDUCTO_API_KEY });
```

Do NOT hardcode keys in source. Do NOT parse `~/.reducto/config.yaml` from app code (that's the MCP server's path, not your app's).
""",

    "python": """## Auth — Python

The Python SDK reads `REDUCTO_API_KEY` from environment.

```python
# Set in .env:
# REDUCTO_API_KEY=your_key_here

import reducto
client = reducto.Reducto()  # reads REDUCTO_API_KEY automatically

# Or explicitly:
import os
client = reducto.Reducto(api_key=os.environ["REDUCTO_API_KEY"])
```

Do NOT hardcode keys in source. Do NOT parse `~/.reducto/config.yaml` from app code.
""",

    "http": """## Auth — REST

Every request needs the `Authorization: Bearer <key>` header.

```bash
export REDUCTO_API_KEY="your_key_here"

curl -H "Authorization: Bearer $REDUCTO_API_KEY" https://platform.reducto.ai/...
```

Set `REDUCTO_API_KEY` in your shell or load from `.env`. Do NOT hardcode in source.
""",
}

# Topic registry — maps topic key to (one-line summary, per-language content)
TEMPLATES = {
    "quickstart": ("Install, auth, and your first Reducto call", QUICKSTART),
    "parse": ("Parse a document into structured chunks (text, tables, figures)", PARSE),
    "extract": ("Extract structured JSON fields from a document via schema", EXTRACT),
    "split": ("Segment a document into named sections", SPLIT),
    "edit": ("Fill forms or modify a PDF/DOCX (with form_schema caching)", EDIT),
    "upload": ("Upload a file and get a reducto:// URL", UPLOAD),
    "classify": ("Categorize a document against provided categories", CLASSIFY),
    "auth": ("Authentication setup for generated apps", AUTH),
}
