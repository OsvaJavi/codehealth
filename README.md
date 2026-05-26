# Agente de IA: Analizador de Calidad de Código

An AI agent that analyzes Python code quality using the **Google Gemini API** with function calling. The agent reasons about which analysis tools to call, executes them via a manual tool-use loop, and synthesizes a final report with a quality score.

> **Free tier:** Gemini 2.5 Flash — 60 requests/minute, no credit card required.

## Architecture

```
POST /analyze
    │
    ▼
FastAPI (main.py)
    │
    ▼
Agent (agent.py)  ─────────────────────────────────────────────────┐
    │                                                               │
    │  1. Send code + analysis_type to Gemini                       │
    │  2. Gemini reasons → returns function_call(s)                 │
    │  3. Agent executes tools locally (real AST analysis)          │
    │  4. Agent sends FunctionResponse back to Gemini               │
    │  5. Repeat until Gemini returns text only (final report)      │
    │                                                               │
    ▼                                                               ▼
Tools (tools.py)                                      Gemini 2.5 Flash
    ├── analyze_code_style()    — PEP 8 violations
    ├── detect_code_smells()   — Anti-patterns + severity
    └── suggest_improvements() — Refactoring by focus area
```

## Setup

### 1. Get a free Google API key

1. Go to **[https://ai.google.dev](https://ai.google.dev)** and click **"Get API key in Google AI Studio"**
2. Sign in with your Google account
3. Click **"Create API key"** → select or create a project
4. Copy the generated key (starts with `AIza...`)

> The free tier gives you **60 requests/minute** with no billing required.

### 2. Configure the API key

Edit the `.env` file in the project directory:

```
GOOGLE_API_KEY=AIzaSy...your-key-here
```

Or export it directly:

```bash
export GOOGLE_API_KEY=AIzaSy...   # Linux/Mac
$env:GOOGLE_API_KEY="AIzaSy..."   # Windows PowerShell
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the server

```bash
uvicorn main:app --reload
```

The API will be available at `http://localhost:8000`.

## API Usage

### Endpoints

| Method | Path       | Description              |
|--------|------------|--------------------------|
| GET    | `/`        | Service info             |
| POST   | `/analyze` | Analyze Python code      |

### Request body

```json
{
  "code": "def myFunc():\n    x=1\n    return x",
  "analysis_type": "auto",
  "focus_area": "readability"
}
```

| Field           | Type   | Required | Values                               |
|-----------------|--------|----------|--------------------------------------|
| `code`          | string | Yes      | Python source code                   |
| `analysis_type` | string | No       | `auto` (default), `style`, `smells`, `improve` |
| `focus_area`    | string | No       | `performance`, `readability`, `maintainability` |

### Response

```json
{
  "agent_reasoning": "I'll run all three analysis tools to get a complete picture...",
  "tools_used": ["analyze_code_style", "detect_code_smells", "suggest_improvements"],
  "analysis_results": [
    {
      "tool_name": "analyze_code_style",
      "results": [
        {"line": 1, "rule": "N802", "description": "Function name 'myFunc' should be snake_case"}
      ],
      "count": 1
    }
  ],
  "final_report": "The code has several style issues...",
  "code_quality_score": 7.5
}
```

### Example with curl

```bash
curl -X POST http://localhost:8000/analyze \
  -H "Content-Type: application/json" \
  -d '{
    "code": "def myFunc(x,y):\n    Result=x+y\n    return Result",
    "analysis_type": "auto"
  }'
```

### Analysis types

| Type      | Tools called                | Best for                        |
|-----------|-----------------------------|---------------------------------|
| `auto`    | All three tools             | General review                  |
| `style`   | `analyze_code_style`        | PEP 8 / naming checks           |
| `smells`  | `detect_code_smells`        | Design issues / complexity      |
| `improve` | `suggest_improvements`      | Refactoring recommendations     |

## Example files

The `examples/` directory contains 5 Python files you can test with:

| File                        | Content                                  |
|-----------------------------|------------------------------------------|
| `example1_bad_style.py`     | Naming violations, missing spaces, wrong indentation |
| `example2_code_smells.py`   | Long functions, too many params, deep nesting, bare `except` |
| `example3_unoptimized.py`   | For-loops with append, string concat in loops, `len() > 0` |
| `example4_mixed_issues.py`  | All of the above combined                |
| `example5_clean_code.py`    | Well-structured code — high quality score |

Browse the interactive API docs at `http://localhost:8000/docs` to paste example code and test live.

## Quality score

The score starts at **10.0** and penalties are applied per finding:

| Finding type             | Penalty |
|--------------------------|---------|
| HIGH severity smell      | −1.5    |
| MEDIUM severity smell    | −0.8    |
| LOW severity smell       | −0.3    |
| Style violation          | −0.25   |
| HIGH/CRITICAL suggestion | −0.5    |
| MEDIUM suggestion        | −0.2    |
| LOW suggestion           | −0.1    |

Minimum score is **0.0**.

## Project structure

```
.
├── main.py          # FastAPI app — /analyze endpoint
├── agent.py         # Gemini agentic loop + function-calling definitions
├── tools.py         # 3 real AST-based analysis tools
├── models.py        # Pydantic request/response models
├── requirements.txt
├── .env             # GOOGLE_API_KEY goes here
├── README.md
└── examples/
    ├── example1_bad_style.py
    ├── example2_code_smells.py
    ├── example3_unoptimized.py
    ├── example4_mixed_issues.py
    └── example5_clean_code.py
```
