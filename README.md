# Glass Box PII Guardrail

A privacy layer for AI applications that protects sensitive information through **reversible anonymization** - with full transparency into the process.

**[Live Demo](https://pii-guardrails.vercel.app)** | **[Project Analysis](./ANALYSIS.md)**

## Why "Glass Box"?

Most AI systems are **black boxes** - you can't see what happens to your data. This project takes the opposite approach:

| Black Box | Glass Box |
|-----------|-----------|
| Hidden processing | Real-time visibility |
| "Trust us" | "Verify yourself" |
| Log files for debugging | Visual inspection UI |

The split-screen interface shows exactly what PII is detected, how it's anonymized, and what gets sent to the LLM - building trust through transparency.

## How It Works

```
"Email john@acme.com about his $85k salary"
                    ↓
            [Detect & Anonymize]
                    ↓
"Email <EMAIL_1> about his <SALARY_1> salary"  →  LLM
                    ↓
            [Deanonymize Response]
                    ↓
"Here's the email for john@acme.com..."
```

The **Inspector Panel** reveals each step in real-time.

## Key Results

| Metric | Value |
|--------|-------|
| Best Detector F1 | **89%** (Presidio) |
| Latency Overhead | **2-3ms** |
| PII Leakage Rate | **6%** |
| Entity Types | **10** |

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

**Split-screen UI:**
- **Left Panel**: Application interface (shows deanonymized output)
- **Right Panel**: Inspector (PII mapping, anonymized prompts, metrics)

## Stack

| Component | Technology |
|-----------|------------|
| Frontend | Next.js 14, Tailwind, Vercel AI SDK |
| Backend | FastAPI, Microsoft Presidio, GLiNER |
| LLM | OpenRouter (configurable) |

## Supported PII Types

`PERSON` `EMAIL` `PHONE` `SSN` `CREDIT_CARD` `DATE` `LOCATION` `BANK_NUMBER` `SALARY`

## Configuration

```bash
# backend/.env
OPENROUTER_API_KEY=sk-or-v1-...  # Optional - demo mode works without
```

## API Endpoints

| Route | Description |
|-------|-------------|
| `POST /api/chat` | Streaming completion with PII protection |
| `GET /api/scenarios` | Test prompts for demo |
| `GET /api/employees` | Sample employee data for RAG |
| `POST /api/benchmark/run` | Run detector benchmarks |

## Learn More

See [ANALYSIS.md](./ANALYSIS.md) for detailed evaluation of detector performance, methodology, and key insights from the project.
