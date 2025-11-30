# Glass Box PII Guardrail

Privacy-preserving RAG chatbot with reversible anonymization.

## Quick Start

```bash
./setup.sh   # Install dependencies (requires Python 3.9-3.12)
./start.sh   # Run both servers
```

Open http://localhost:3000

## Architecture

```
User Input → Retrieve Context → Anonymize PII → LLM → Deanonymize → Display
```

Split-screen UI:
- **Left**: Chat (deanonymized output)
- **Right**: Inspector (PII mapping, anonymized prompts)

## Stack

| Component | Tech |
|-----------|------|
| Frontend | Next.js 14, Tailwind, Vercel AI SDK |
| Backend | FastAPI, Microsoft Presidio |
| LLM | OpenRouter (gpt-oss-120b) |

## PII Types

PERSON, EMAIL, PHONE, SSN, CREDIT_CARD, DATE, LOCATION, BANK_NUMBER, SALARY

## Config

```bash
# backend/.env
OPENROUTER_API_KEY=sk-or-v1-...  # Optional - demo mode works without
```

## Endpoints

| Route | Description |
|-------|-------------|
| `POST /api/chat` | Streaming chat |
| `GET /api/scenarios` | Test prompts |
| `GET /api/employees` | Employee list |
