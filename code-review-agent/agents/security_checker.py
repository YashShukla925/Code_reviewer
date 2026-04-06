"""
agents/security_checker.py

Scans the diff for security issues:
  - Hardcoded secrets / API keys
  - SQL injection vectors
  - OWASP Top 10 patterns
  - Unsafe deserialization
  - Exposed debug/admin endpoints
"""

from __future__ import annotations

import json
import logging

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

from graph.state import SecurityFinding, ReviewState
from utils.config import settings

logger = logging.getLogger(__name__)

_llm = ChatGoogleGenerativeAI(
    model=settings.model_name,
    google_api_key=settings.google_api_key,
    temperature=0,
)

_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are an application security engineer doing a security-focused code review.

Analyse the diff for these issue categories (OWASP Top 10 + common mistakes):
- hardcoded-secret   : API keys, passwords, tokens in code
- sql-injection      : string-concatenated queries
- xss               : unescaped user input in HTML/templates
- insecure-deserial  : pickle.loads, yaml.load without Loader
- path-traversal     : unsanitised file paths from user input
- weak-crypto        : MD5, SHA1 for security purposes
- debug-exposure     : debug=True, exposed stack traces
- broken-auth        : missing auth checks on endpoints

Return a JSON array of findings. Each finding:
{{
  "severity": "critical|high|medium|low",
  "category": "<one of the categories above>",
  "file": "<filename>",
  "line": <line number or null>,
  "description": "<what the issue is>",
  "suggestion": "<how to fix it>"
}}

Return [] if no issues found. Return ONLY the JSON array, no prose.""",
    ),
    (
        "human",
        "PR diff:\n{raw_diff}",
    ),
])


def security_checker_node(state: ReviewState) -> dict:
    """LangGraph node — runs security analysis on the diff."""
    logger.info("SecurityChecker: analysing diff")

    if not state.get("diff_summary"):
        return {"errors": ["SecurityChecker: no diff_summary in state"]}

    raw_diff = state["diff_summary"][0]["raw_diff"]

    try:
        chain = _PROMPT | _llm
        response = chain.invoke({"raw_diff": raw_diff[:12_000]})

        # parse JSON — strip markdown fences if the model adds them
        text = response.content.strip().removeprefix("```json").removesuffix("```").strip()
        raw_findings: list[dict] = json.loads(text)

        findings: list[SecurityFinding] = [
            {
                "severity": f.get("severity", "medium"),
                "category": f.get("category", "unknown"),
                "file": f.get("file", "unknown"),
                "line": f.get("line"),
                "description": f.get("description", ""),
                "suggestion": f.get("suggestion", ""),
            }
            for f in raw_findings
        ]

        logger.info("SecurityChecker: found %d issues", len(findings))
        return {"security_findings": findings}

    except json.JSONDecodeError as exc:
        logger.error("SecurityChecker: failed to parse LLM JSON: %s", exc)
        return {"errors": [f"SecurityChecker JSON parse error: {exc}"]}
    except Exception as exc:
        logger.error("SecurityChecker failed: %s", exc)
        return {"errors": [f"SecurityChecker: {exc}"]}
