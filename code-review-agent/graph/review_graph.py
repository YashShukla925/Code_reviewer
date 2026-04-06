"""
graph/review_graph.py

Builds and compiles the LangGraph StateGraph.

Flow:
  START
    └── diff_reader          (sequential — everyone needs the diff)
          ├── security_checker  ─┐
          └── optimizer         ─┤  (parallel fan-out)
                                 ▼
                           review_writer
                                 └── post_to_github
                                           └── END
"""

from __future__ import annotations

import logging
import uuid

from langgraph.graph import END, START, StateGraph

from agents.diff_reader import diff_reader_node
from agents.optimizer import optimizer_node
from agents.review_writer import review_writer_node
from agents.security_checker import security_checker_node
from graph.state import ReviewState
from tools.github_tools import post_pr_review

logger = logging.getLogger(__name__)


# ── GitHub poster node (not an LLM agent, just a side-effect) ─────────────

def post_to_github_node(state: ReviewState) -> dict:
    """Posts the finished review comment to GitHub."""
    if not state.get("review_comment"):
        logger.warning("post_to_github: no review_comment in state, skipping")
        return {"review_posted": False}

    try:
        post_pr_review(
            repo_full_name=state["repo_full_name"],
            pr_number=state["pr_number"],
            body=state["review_comment"],
            event="COMMENT",
        )
        return {"review_posted": True}
    except Exception as exc:
        logger.error("post_to_github failed: %s", exc)
        return {"errors": [f"post_to_github: {exc}"], "review_posted": False}


# ── Graph builder ──────────────────────────────────────────────────────────

def build_graph():
    """Builds and compiles the review StateGraph."""
    builder = StateGraph(ReviewState)

    # Register nodes
    builder.add_node("diff_reader", diff_reader_node)
    builder.add_node("security_checker", security_checker_node)
    builder.add_node("optimizer", optimizer_node)
    builder.add_node("review_writer", review_writer_node)
    builder.add_node("post_to_github", post_to_github_node)

    # Sequential start → diff_reader
    builder.add_edge(START, "diff_reader")

    # Parallel fan-out: diff_reader → [security_checker, optimizer]
    builder.add_edge("diff_reader", "security_checker")
    builder.add_edge("diff_reader", "optimizer")

    # Fan-in: both parallel agents → review_writer
    builder.add_edge("security_checker", "review_writer")
    builder.add_edge("optimizer", "review_writer")

    # review_writer → post → END
    builder.add_edge("review_writer", "post_to_github")
    builder.add_edge("post_to_github", END)

    return builder.compile()


# Singleton — compiled once at import time
review_graph = build_graph()


# ── Convenience runner ─────────────────────────────────────────────────────

async def run_review(
    repo_full_name: str,
    pr_number: int,
    pr_title: str,
    pr_author: str,
    base_branch: str,
    head_branch: str,
) -> ReviewState:
    """
    Entry point called by the FastAPI webhook handler.
    Returns the final state after the full graph run.
    """
    run_id = str(uuid.uuid4())
    logger.info("Starting review run %s for %s#%d", run_id, repo_full_name, pr_number)

    initial_state: ReviewState = {
        "repo_full_name": repo_full_name,
        "pr_number": pr_number,
        "pr_title": pr_title,
        "pr_author": pr_author,
        "base_branch": base_branch,
        "head_branch": head_branch,
        "diff_summary": [],
        "security_findings": [],
        "optimization_suggestions": [],
        "review_comment": "",
        "review_posted": False,
        "errors": [],
        "run_id": run_id,
    }

    final_state = await review_graph.ainvoke(initial_state)
    logger.info(
        "Review run %s complete. Posted: %s. Errors: %s",
        run_id, final_state.get("review_posted"), final_state.get("errors"),
    )
    return final_state
