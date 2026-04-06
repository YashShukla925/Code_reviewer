"""
agents/review_writer.py

Final agent in the pipeline.
Receives all upstream findings and writes a polished, structured
markdown review comment ready to post to GitHub.
"""

from __future__ import annotations

import logging

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

from graph.state import ReviewState
from utils.config import settings

logger = logging.getLogger(__name__)

_llm = ChatGoogleGenerativeAI(
    model=settings.model_name,
    google_api_key=settings.google_api_key,
    temperature=0.2,
)

_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a senior engineer writing a thorough but constructive PR review comment.

Rules:
- Be specific, cite file names and line numbers when available
- Lead with a brief overall impression (1-2 sentences)
- Group findings under clear headings
- Use ⛔ for critical security issues, ⚠️ for warnings, 💡 for suggestions
- End with a summary verdict: APPROVE / REQUEST CHANGES / NEEDS DISCUSSION
- Write in GitHub-flavoured markdown
- Tone: collegial, direct, never condescending""",
    ),
    (
        "human",
        """Write a PR review comment from these findings.

## PR Info
Title: {pr_title}
Author: {pr_author}
Files changed: {files_changed} | +{additions} / -{deletions}
Languages: {language_breakdown}

## Security findings
{security_findings}

## Optimisation suggestions
{optimization_suggestions}

## Errors encountered by agents (mention if any)
{errors}""",
    ),
])


def _format_security(findings: list) -> str:
    if not findings:
        return "None found ✅"
    lines = []
    for f in findings:
        loc = f"{f['file']}" + (f":{f['line']}" if f["line"] else "")
        lines.append(
            f"- **[{f['severity'].upper()}]** `{loc}` — {f['description']}  \n"
            f"  Fix: {f['suggestion']}"
        )
    return "\n".join(lines)


def _format_optimizations(suggestions: list) -> str:
    if not suggestions:
        return "Code looks clean ✅"
    lines = []
    for s in suggestions:
        loc = f"{s['file']}" + (f":{s['line']}" if s["line"] else "")
        lines.append(
            f"- **[{s['category']}]** `{loc}` — {s['description']}  \n"
            f"  Suggestion: {s['suggestion']}"
        )
    return "\n".join(lines)


def review_writer_node(state: ReviewState) -> dict:
    """LangGraph node — writes the final markdown PR review comment."""
    logger.info("ReviewWriter: composing final review")

    diff = state["diff_summary"][0] if state.get("diff_summary") else {}
    security = state.get("security_findings", [])
    optimizations = state.get("optimization_suggestions", [])
    errors = state.get("errors", [])

    try:
        chain = _PROMPT | _llm
        response = chain.invoke({
            "pr_title": state["pr_title"],
            "pr_author": state["pr_author"],
            "files_changed": diff.get("files_changed", "?"),
            "additions": diff.get("additions", 0),
            "deletions": diff.get("deletions", 0),
            "language_breakdown": diff.get("language_breakdown", {}),
            "security_findings": _format_security(security),
            "optimization_suggestions": _format_optimizations(optimizations),
            "errors": "\n".join(errors) if errors else "None",
        })

        review_comment = response.content
        logger.info("ReviewWriter: comment written (%d chars)", len(review_comment))
        return {"review_comment": review_comment}

    except Exception as exc:
        logger.error("ReviewWriter failed: %s", exc)
        return {"errors": [f"ReviewWriter: {exc}"], "review_comment": ""}
