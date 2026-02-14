# MYME — Automated MCP Generator + Blaxel Deploy

Fully automated pipeline: give it a spec file or URL, get a complete MCP server deployed to Blaxel. No user interaction required.

## Usage

Run from inside the `blaxel/` directory:

```bash
# From a local OpenAPI/Swagger file (auto-deploys to Blaxel)
python generate.py ../examples/petstore.yaml

# From a URL
python generate.py https://petstore.swagger.io/v2/swagger.json

# Custom output directory and server name
python generate.py ../path/to/spec.yaml --output ./my-server --name my-api

# Generate only, skip deploy
python generate.py ../path/to/spec.json --no-deploy

# Verbose logging
python generate.py ../path/to/spec.json -v
```

## Pipeline

```
  Source (file or URL)
         │
         ▼
  ┌──────────────┐
  │  1. INGEST   │  Parse OpenAPI 3.x / Swagger 2.x / Postman v2.1
  └──────┬───────┘
         ▼
  ┌──────────────┐
  │  2. DISCOVER │  Group endpoints into high-level MCP tools
  └──────┬───────┘
         ▼
  ┌──────────────┐
  │  3. POLICY   │  Classify safety (read/write/destructive), apply rules
  └──────┬───────┘
         ▼
  ┌──────────────┐
  │  4. GENERATE │  DeepSeek-V3 via Featherless → FastMCP server code
  └──────┬───────┘
         ▼
  ┌──────────────┐
  │  5. DEPLOY   │  bl deploy → Blaxel serverless hosting
  └──────┬───────┘
         ▼
  Live MCP endpoint: https://run.blaxel.ai/<workspace>/functions/<name>
```

## Output

```
output/<server-name>/
├── src/
│   └── server.py      # Complete MCP server (FastMCP, LLM-generated)
├── blaxel.toml        # Blaxel deployment config
├── test_server.py     # Auto-generated test suite
├── pyproject.toml     # Project config
├── requirements.txt   # Python dependencies
└── .env.example       # Environment variable template
```

## Environment Variables (.env)

```bash
# Required for deploy
BL_API_KEY=your-blaxel-api-key
BL_WORKSPACE=your-workspace-name

# Required for code generation
FEATHERLESS_API_KEY=your-featherless-key

# Optional (Gemini fallback for messy specs)
GEMINI_API_KEY=your-gemini-key
```

## Requirements

- **Python 3.11+** with `httpx`, `pyyaml`, `pydantic`, `python-dotenv`
- **Blaxel CLI**: `brew tap blaxel-ai/blaxel && brew install blaxel`
- **`FEATHERLESS_API_KEY`** in `.env` (code generation)
- **`BL_API_KEY`** in `.env` (deployment)
