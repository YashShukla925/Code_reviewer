"""
agents/optimizer.py

Analyses the diff for code quality and performance issues:
  - Algorithm complexity (O(n²) loops, nested DB calls)
  - Design patterns (DRY violations, God functions)
  - Python-specific anti-patterns
  - Missing error handling
"""

from __future__ import annotations

import json
import logging

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

from graph.state import OptimizationSuggestion, ReviewState
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
        """You are a senior software engineer focused on code quality and performance.

Analyse the diff for these issue categories:
- performance    : O(n²) loops, N+1 queries, unnecessary re-computation
- complexity     : functions > 20 lines, deeply nested conditionals
- dry            : copy-pasted logic that should be extracted
- design         : God classes/functions, missing abstractions, tight coupling
- error-handling : bare except, swallowed exceptions, missing retries
- naming         : unclear variable/function names that hurt readability

Return a JSON array of suggestions. Each suggestion:
{{
  "category": "<one of the categories above>",
  "file": "<filename>",
  "line": <line number or null>,
  "description": "<what the issue is>",
  "suggestion": "<concrete improvement>"
}}

Return [] if the code looks solid. Return ONLY the JSON array, no prose.
Limit to the top 5 most impactful suggestions.""",
    ),
    (
        "human",
        "PR diff:\n{raw_diff}",
    ),
])


def optimizer_node(state: ReviewState) -> dict:
    """LangGraph node — runs code quality analysis on the diff."""
    logger.info("Optimizer: analysing code quality")

    if not state.get("diff_summary"):
        return {"errors": ["Optimizer: no diff_summary in state"]}

    raw_diff = state["diff_summary"][0]["raw_diff"]

    try:
        chain = _PROMPT | _llm
        response = chain.invoke({"raw_diff": raw_diff[:12_000]})

        text = response.content.strip().removeprefix("```json").removesuffix("```").strip()
        raw_suggestions: list[dict] = json.loads(text)

        suggestions: list[OptimizationSuggestion] = [
            {
                "category": s.get("category", "general"),
                "file": s.get("file", "unknown"),
                "line": s.get("line"),
                "description": s.get("description", ""),
                "suggestion": s.get("suggestion", ""),
            }
            for s in raw_suggestions
        ]

        logger.info("Optimizer: found %d suggestions", len(suggestions))
        return {"optimization_suggestions": suggestions}

    except json.JSONDecodeError as exc:
        logger.error("Optimizer: failed to parse LLM JSON: %s", exc)
        return {"errors": [f"Optimizer JSON parse error: {exc}"]}
    except Exception as exc:
        logger.error("Optimizer failed: %s", exc)
        return {"errors": [f"Optimizer: {exc}"]}
