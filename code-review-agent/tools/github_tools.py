"""
tools/github_tools.py

Thin wrapper around PyGithub for the two things we need:
  1. fetch_pr_diff  → raw unified diff text
  2. post_pr_review → post markdown comment to a PR
"""

from __future__ import annotations

import logging

from github import Github, GithubException

from utils.config import settings

logger = logging.getLogger(__name__)

_client = Github(settings.github_token)


def fetch_pr_diff(repo_full_name: str, pr_number: int) -> tuple[str, dict]:
    """
    Returns (raw_diff_text, metadata_dict).

    metadata_dict keys:
        files_changed, additions, deletions, language_breakdown
    """
    try:
        repo = _client.get_repo(repo_full_name)
        pr = repo.get_pull(pr_number)
        files = pr.get_files()

        language_breakdown: dict[str, int] = {}
        diff_parts: list[str] = []
        total_additions = 0
        total_deletions = 0
        files_changed = 0

        for f in files:
            files_changed += 1
            total_additions += f.additions
            total_deletions += f.deletions

            # rough language detection from extension
            ext = f.filename.rsplit(".", 1)[-1] if "." in f.filename else "other"
            language_breakdown[ext] = language_breakdown.get(ext, 0) + 1

            if f.patch:
                diff_parts.append(
                    f"### {f.filename} (+{f.additions} / -{f.deletions})\n"
                    f"```diff\n{f.patch}\n```"
                )

        return "\n\n".join(diff_parts), {
            "files_changed": files_changed,
            "additions": total_additions,
            "deletions": total_deletions,
            "language_breakdown": language_breakdown,
        }

    except GithubException as e:
        logger.error("GitHub API error fetching diff: %s", e)
        raise


def post_pr_review(
    repo_full_name: str,
    pr_number: int,
    body: str,
    event: str = "COMMENT",
) -> str:
    """
    Posts a review comment to the PR.

    event: "COMMENT" | "APPROVE" | "REQUEST_CHANGES"
    Returns the HTML URL of the posted review.
    """
    try:
        repo = _client.get_repo(repo_full_name)
        pr = repo.get_pull(pr_number)
        review = pr.create_review(body=body, event=event)
        logger.info("Posted review to %s#%d: %s", repo_full_name, pr_number, review.html_url)
        return review.html_url
    except GithubException as e:
        logger.error("GitHub API error posting review: %s", e)
        raise
