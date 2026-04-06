# Code Review Agent

An AI-powered GitHub pull request review service built with FastAPI, LangGraph, Gemini, and Redis.

It listens for GitHub `pull_request` webhooks, analyzes the PR diff, generates security and code-quality feedback, and posts the final review back to GitHub.

## What It Does

- Receives GitHub PR webhooks at `/webhook/github`
- Verifies webhook signatures using `X-Hub-Signature-256`
- Fetches the PR diff from GitHub
- Runs a LangGraph review pipeline with:
  - `diff_reader`
  - `security_checker`
  - `optimizer`
  - `review_writer`
- Posts the generated review comment directly on the PR

## Project Structure

```text
code-review-agent/
|-- agents/              # LLM-powered review agents
|-- api/                 # FastAPI webhook app
|-- graph/               # LangGraph workflow + shared state
|-- tools/               # GitHub API helpers
|-- utils/               # App settings/config
|-- main.py              # Local entrypoint
|-- test_local.py        # Manual local test runner
|-- Dockerfile
|-- docker-compose.yml
`-- requirements.txt
```

## Requirements

- Python 3.11+ recommended
- Redis running locally or remotely
- A GitHub personal access token with repo access
- A GitHub webhook secret
- A Google AI Studio API key for Gemini

## Environment Variables

Create a `.env` file in the project root.

You can start from:

```powershell
Copy-Item .env.example .env
```

Example values:

```env
GOOGLE_API_KEY=your_google_api_key
MODEL_NAME=gemini-2.5-flash

GITHUB_TOKEN=your_github_token
GITHUB_WEBHOOK_SECRET=your_webhook_secret

LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=your_langsmith_key
LANGCHAIN_PROJECT=code-review-agent

REDIS_URL=redis://localhost:6379

APP_ENV=development
LOG_LEVEL=INFO
```

## Setup Locally

### 1. Open the project

```powershell
cd code-review-agent
```

### 2. Create and activate a virtual environment

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

On macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Start Redis

If you already have Redis installed locally, start it and keep it running.

Or run Redis with Docker:

```powershell
docker run -p 6379:6379 redis:7-alpine
```

### 5. Configure `.env`

Fill in the values in `.env`:

- `GOOGLE_API_KEY`
- `GITHUB_TOKEN`
- `GITHUB_WEBHOOK_SECRET`
- `REDIS_URL`

Optional:

- `MODEL_NAME`
- `LANGCHAIN_TRACING_V2`
- `LANGCHAIN_API_KEY`
- `LANGCHAIN_PROJECT`
- `APP_ENV`
- `LOG_LEVEL`

### 6. Run the app

Using Python:

```powershell
python main.py
```

Or using Uvicorn directly:

```powershell
uvicorn main:app --reload
```

The API will be available at:

- `http://localhost:8000/health`
- `http://localhost:8000/webhook/github`

## Run With Docker Compose

This starts both the app and Redis.

```powershell
docker compose up --build
```

App endpoint:

- `http://localhost:8000`

## GitHub Webhook Setup

In your GitHub repository:

1. Go to `Settings -> Webhooks`
2. Click `Add webhook`
3. Set:
   - Payload URL: `https://your-public-url/webhook/github`
   - Content type: `application/json`
   - Secret: same value as `GITHUB_WEBHOOK_SECRET`
4. Choose `Let me select individual events`
5. Enable `Pull requests`

The service currently handles these PR actions:

- `opened`
- `synchronize`

## Local Testing Without Webhooks

You can test the review pipeline directly:

```powershell
python test_local.py
```

Before running it, update the repo and PR number inside `test_local.py`.

## API Endpoints

- `GET /health` -> basic health check
- `POST /webhook/github` -> GitHub webhook receiver

## Notes

- The webhook route validates the GitHub HMAC signature before processing.
- Reviews are triggered in a FastAPI background task, so the webhook returns quickly.
- The app posts a GitHub PR review using your configured `GITHUB_TOKEN`.
- Redis is configured in the environment, though the current workflow code mainly uses LangGraph orchestration and GitHub posting.

## Quick Start

```powershell
cd code-review-agent
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python main.py
```

Then open:

```text
http://localhost:8000/health
```

## Troubleshooting

### Missing environment variables

If startup fails with a settings or validation error, check that `.env` exists and includes the required keys:

- `GOOGLE_API_KEY`
- `GITHUB_TOKEN`
- `GITHUB_WEBHOOK_SECRET`

### GitHub webhook returns 401

Make sure the webhook secret in GitHub exactly matches `GITHUB_WEBHOOK_SECRET`.

### Review is not posted to GitHub

Check:

- the token has access to the repository
- the PR exists and is accessible
- the webhook event is `pull_request`
- the action is `opened` or `synchronize`

### Redis connection issues

Verify your `REDIS_URL` and make sure Redis is running on that address.

## License

Add your preferred license here.
