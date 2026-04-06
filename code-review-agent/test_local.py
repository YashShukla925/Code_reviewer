"""
test_local.py

Run the full review pipeline locally against a real GitHub PR.
No webhook needed — just set your .env and run:

    python test_local.py
"""

import asyncio
import os
from dotenv import load_dotenv

load_dotenv()

from graph.review_graph import run_review


async def main():
    # ── edit these to point at a real PR ──────────────────────────────────
    REPO = "torvalds/linux"          # any public repo
    PR_NUMBER = 1                    # any open PR number
    # ──────────────────────────────────────────────────────────────────────

    print(f"\n🔍  Running review on {REPO}#{PR_NUMBER} ...\n")

    state = await run_review(
        repo_full_name=REPO,
        pr_number=PR_NUMBER,
        pr_title="Test PR",
        pr_author="test-user",
        base_branch="main",
        head_branch="feature/test",
    )

    print("\n" + "═" * 60)
    print("SECURITY FINDINGS:", len(state.get("security_findings", [])))
    for f in state.get("security_findings", []):
        print(f"  [{f['severity'].upper()}] {f['file']} — {f['description']}")

    print("\nOPTIMIZATION SUGGESTIONS:", len(state.get("optimization_suggestions", [])))
    for s in state.get("optimization_suggestions", []):
        print(f"  [{s['category']}] {s['file']} — {s['description']}")

    print("\n" + "═" * 60)
    print("FINAL REVIEW COMMENT:\n")
    print(state.get("review_comment", "(none)"))

    if state.get("errors"):
        print("\n⚠️  ERRORS:")
        for e in state["errors"]:
            print(f"  {e}")

    print(f"\nPosted to GitHub: {state.get('review_posted')}")


asyncio.run(main())
