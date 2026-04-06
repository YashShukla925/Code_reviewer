"""
api/webhook.py

FastAPI app with a single GitHub webhook endpoint.

Security:
  - Validates X-Hub-Signature-256 on every request
  - Only processes "pull_request" events with action "opened" or "synchronize"
  - Returns 200 immediately; review runs in a BackgroundTask
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request

from graph.review_graph import run_review
from utils.config import settings

logger = logging.getLogger(__name__)
app = FastAPI(title="Code Review Agent", version="0.1.0")


# ── HMAC signature verification ────────────────────────────────────────────

def _verify_signature(body: bytes, signature_header: str | None) -> None:
    """Raises HTTPException 401 if the webhook signature is invalid."""
    if not signature_header:
        raise HTTPException(status_code=401, detail="Missing X-Hub-Signature-256")

    expected = "sha256=" + hmac.new(
        settings.github_webhook_secret.encode(),
        body,
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature_header):
        raise HTTPException(status_code=401, detail="Invalid signature")


# ── Background review task ─────────────────────────────────────────────────

async def _trigger_review(payload: dict) -> None:
    pr = payload["pull_request"]
    repo = payload["repository"]
    try:
        await run_review(
            repo_full_name=repo["full_name"],
            pr_number=pr["number"],
            pr_title=pr["title"],
            pr_author=pr["user"]["login"],
            base_branch=pr["base"]["ref"],
            head_branch=pr["head"]["ref"],
        )
    except Exception:
        logger.exception("Unhandled error in review pipeline")


# ── Endpoints ──────────────────────────────────────────────────────────────

@app.post("/webhook/github", status_code=202)
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: str | None = Header(default=None),
    x_github_event: str | None = Header(default=None),
):
    body = await request.body()
    _verify_signature(body, x_hub_signature_256)

    if x_github_event != "pull_request":
        return {"status": "ignored", "reason": f"event={x_github_event}"}

    payload = await request.json()
    action = payload.get("action")

    if action not in ("opened", "synchronize"):
        return {"status": "ignored", "reason": f"action={action}"}

    pr_number = payload["pull_request"]["number"]
    repo_name = payload["repository"]["full_name"]
    logger.info("Queuing review for %s#%d (action=%s)", repo_name, pr_number, action)

    background_tasks.add_task(_trigger_review, payload)
    return {"status": "accepted", "pr": pr_number, "repo": repo_name}


@app.get("/health")
async def health():
    return {"status": "ok"}
