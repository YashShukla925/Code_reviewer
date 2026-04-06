"""
agents/diff_reader.py

Reads the raw PR diff from GitHub and produces a structured DiffSummary.
This is the first node in the graph — all other agents depend on its output.
"""

from __future__ import annotations

import logging

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

from graph.state import DiffSummary, ReviewState
from tools.github_tools import fetch_pr_diff
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
        "You are a senior engineer reviewing a pull request diff. "
        "Summarise the changes clearly and concisely. "
        "Focus on: what changed, why it likely changed, and the overall scope.",
    ),
    (
        "human",
        "PR: {pr_title} by {pr_author}\n"
        "Branch: {head_branch} → {base_branch}\n\n"
        "Diff:\n{raw_diff}",
    ),
])


def diff_reader_node(state: ReviewState) -> dict:
    """LangGraph node — fetches diff from GitHub and summarises it."""
    logger.info("DiffReader: fetching diff for %s#%d", state["repo_full_name"], state["pr_number"])

    try:
        raw_diff, meta = fetch_pr_diff(state["repo_full_name"], state["pr_number"])

        # Ask the LLM for a plain-English summary (stored in raw_diff field for downstream agents)
        chain = _PROMPT | _llm
        response = chain.invoke({
            "pr_title": state["pr_title"],
            "pr_author": state["pr_author"],
            "head_branch": state["head_branch"],
            "base_branch": state["base_branch"],
            "raw_diff": raw_diff[:12_000],  # stay within context window
        })

        summary: DiffSummary = {
            "files_changed": meta["files_changed"],
            "additions": meta["additions"],
            "deletions": meta["deletions"],
            "language_breakdown": meta["language_breakdown"],
            "raw_diff": raw_diff,  # full diff passed to downstream agents
        }

        logger.info(
            "DiffReader: %d files, +%d/-%d",
            meta["files_changed"], meta["additions"], meta["deletions"],
        )
        return {"diff_summary": [summary]}

    except Exception as exc:
        logger.error("DiffReader failed: %s", exc)
        return {"errors": [f"DiffReader: {exc}"]}
