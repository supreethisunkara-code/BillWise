# BillWise — AI-Powered Hospital Bill Assistant (Local Version)

BillWise reads a photo or PDF of a hospital bill, breaks it down by category,
flags charges that look inflated compared to typical reference rates,
estimates rough insurance coverage, and checks eligibility for major
government health schemes (like Ayushman Bharat PM-JAY) — all through a
simple chat interface.

This version runs **entirely on your own laptop** — no AWS account, no cloud
deployment, no WhatsApp Business setup required.

---

## How it works

1. You send a bill photo/PDF through the local chat UI
2. Claude reads and extracts every line item (room rent, procedures,
   diagnostics, medicines, consumables, etc.)
3. The app compares charges against reference rates and flags anything that
   looks overcharged or duplicated
4. It asks if you have insurance and gives a rough covered/excluded estimate
5. It asks a few quick questions (income, state, employment) and checks
   eligibility against PM-JAY, CGHS, and state schemes

---

## Tools used

| Layer | Tool |
|---|---|
| Frontend | Plain HTML/JS chat widget (`static/index.html`) |
| Backend | FastAPI + Uvicorn (`src/main.py`) |
| Storage (bill files) | Amazon S3, emulated locally by **LocalStack** |
| Database (sessions) | Amazon DynamoDB, emulated locally by **LocalStack** |
| AI extraction | Anthropic API (Claude) directly |
| Extra requirement | **Docker Desktop** (to run LocalStack) |

**Why not real AWS or WhatsApp?** LocalStack (open-source) emulates AWS
services on your own machine for free, so no AWS account or billing is
needed. WhatsApp always requires a public webhook URL reachable by Meta's
servers, which isn't compatible with a fully local setup — the included
chat UI replicates the same conversation flow instead.

---

## Project structure

```
BillWise/
├── data/
│   ├── reference_rates.json      # sample reference prices for overcharge detection
│   └── scheme_rules.json         # government scheme eligibility rules
├── src/
│   ├── config.py                 # env config, points boto3 at LocalStack
│   ├── bill_parser.py            # Claude-based bill extraction
│   ├── overcharge_checker.py     # flags inflated/duplicate charges
│   ├── insurance.py              # rough coverage estimate
│   ├── schemes.py                # government scheme eligibility check
│   ├── session_store.py          # DynamoDB-backed conversation state
│   ├── conversation.py           # multi-turn chat logic
│   ├── s3_storage.py             # stores uploaded bills
│   └── main.py                   # FastAPI app tying it all together
├── static/
│   └── index.html                # local chat interface
├── docker-compose.yml            # starts LocalStack
├── setup_localstack.sh           # creates the S3 bucket + DynamoDB table
├── requirements.txt
└── .env.example
```

---

## Setup

### Prerequisites
- Python 3.10+
- [Docker Desktop](https://www.docker.com/products/docker-desktop)
- An [Anthropic API key](https://console.anthropic.com)

### Steps

```bash
# 1. Start LocalStack (emulates S3 + DynamoDB on your machine)
docker compose up -d

# 2. Create the S3 bucket and DynamoDB table (one-time)
chmod +x setup_localstack.sh   # skip on Windows PowerShell
./setup_localstack.sh

# 3. Install Python dependencies
pip install -r requirements.txt

# 4. Set up your environment file
cp .env.example .env
# open .env and paste in your real ANTHROPIC_API_KEY

# 5. Run the app
uvicorn src.main:app --reload --port 8000
```

### Try it
Open **http://localhost:8000** in your browser. Type a message or upload a
bill photo/PDF and follow the conversation.

---

## Verifying LocalStack is working

```bash
export AWS_ACCESS_KEY_ID=test AWS_SECRET_ACCESS_KEY=test AWS_DEFAULT_REGION=us-east-1
aws --endpoint-url=http://localhost:4566 s3 ls
aws --endpoint-url=http://localhost:4566 dynamodb list-tables
```
You should see `billwise-bills` and `billwise-sessions` listed.

---

## Known limitations

- **Reference rates and scheme rules are illustrative placeholders**
  (`data/reference_rates.json`, `data/scheme_rules.json`), not verified
  current CGHS/PM-JAY government data.
- **Insurance and scheme eligibility are heuristics, not determinations** —
  always confirm with your insurer/TPA or the official scheme portal.
- **Session data lives only in your local Docker volume** — not meant as
  durable, production storage.

---

## Team

| Part | Owner |
|---|---|
| Bill extraction, overcharge/insurance/scheme logic | Hamsini |
| Conversation logic & session store | Mohanapriya |
| Config, Docker/LocalStack setup | Supreethi |
| Backend integration, WhatsApp client, frontend | Sruthi |