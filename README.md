# AI Code Review Assistant

A FastAPI service that reviews Python code for bugs, security issues, and inefficiencies.
It combines a rule-based static analyzer (built on Python's `ast` module — code is parsed, never executed)
with an AI review powered by Groq, and stores review history in PostgreSQL.

## Features

- **Static analysis**: bare `except`, mutable default arguments, `eval`/`exec`, `shell=True`,
  `== None` comparisons, hardcoded secrets, unsafe `pickle`/`yaml` deserialization, syntax errors
- **AI review** via Groq (optional — static results are still returned if the AI is disabled or fails)
- **Review history** saved to PostgreSQL, with listing, detail, delete, and aggregate stats

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
```

Create a `.env` file in the project root:

```env
DATABASE_URL=postgresql+psycopg://postgres:<password>@localhost:5432/code_review
GROQ_API_KEY=<your-groq-api-key>   # leave empty to disable AI review
# Optional
GROQ_MODEL=llama-3.3-70b-versatile
LOG_LEVEL=INFO
```

Tables are created automatically on startup.

## Run

```bash
uvicorn app.main:app --reload
```

Interactive API docs: http://localhost:8000/docs

## API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | API and database status |
| POST | `/analyze` | Static analysis only (no AI, nothing saved) |
| POST | `/review` | Static + AI review, saved to history |
| GET | `/reviews` | List saved reviews (`limit`, `offset`) |
| GET | `/reviews/stats` | Totals by severity and most common rules |
| GET | `/reviews/{id}` | Full review with code and issues |
| DELETE | `/reviews/{id}` | Delete a review |

Example:

```bash
curl -X POST http://localhost:8000/review \
  -H "Content-Type: application/json" \
  -d '{"code": "x = eval(input())\n", "filename": "demo.py"}'
```

## Tests

```bash
pytest
```

Tests use an in-memory SQLite database and mock the Groq API, so no Postgres or API key is needed.
