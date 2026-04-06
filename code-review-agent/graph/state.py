"""
graph/state.py

Shared state flowing through every node in the review graph.
Each agent appends to its own list — parallel agents never conflict.
"""

from __future__ import annotations

import operator
from typing import Annotated, Any

from typing_extensions import TypedDict


# ── per-agent result payloads ──────────────────────────────────────────────

class DiffSummary(TypedDict):
    files_changed: int
    additions: int
    deletions: int
    language_breakdown: dict[str, int]  # {"python": 3, "yaml": 1}
    raw_diff: str


class SecurityFinding(TypedDict):
    severity: str          # "critical" | "high" | "medium" | "low"
    category: str          # e.g. "hardcoded-secret", "sql-injection"
    file: str
    line: int | None
    description: str
    suggestion: str


class OptimizationSuggestion(TypedDict):
    category: str          # "performance" | "complexity" | "design" | "dry"
    file: str
    line: int | None
    description: str
    suggestion: str


# ── main graph state ───────────────────────────────────────────────────────

class ReviewState(TypedDict):
    # ── input (set once by the webhook handler) ──
    repo_full_name: str          # "owner/repo"
    pr_number: int
    pr_title: str
    pr_author: str
    base_branch: str
    head_branch: str

    # ── agent outputs (Annotated → list append, safe for parallel nodes) ──
    diff_summary: Annotated[list[DiffSummary], operator.add]
    security_findings: Annotated[list[SecurityFinding], operator.add]
    optimization_suggestions: Annotated[list[OptimizationSuggestion], operator.add]

    # ── final output ──
    review_comment: str          # markdown written by ReviewWriterAgent
    review_posted: bool          # True once GitHub comment is posted

    # ── metadata ──
    errors: Annotated[list[str], operator.add]   # non-fatal errors per agent
    run_id: str                                   # LangSmith trace ID
