"""Measure how fast a repository's maintainers answer and merge outside contributions.

Same method for every repo, so the numbers are comparable: pull requests and issues opened in
the last N days by authors who are not maintainers, the time to the first maintainer response,
and what became of them. Reads GitHub through the authenticated `gh` CLI; writes nothing.

A response is a comment or a review. A maintainer who merges a small pull request without
writing anything leaves no response, so "no response %" overstates neglect for such projects;
the time to merge is the figure to read for them.

    uv run python scripts/maintainer_responsiveness.py owner/repo [owner/repo ...] --days 90
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta

MAINTAINER = {"OWNER", "MEMBER", "COLLABORATOR"}


def parse(ts: str) -> datetime:
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def hours_between(start: str, end: str) -> float:
    return (parse(end) - parse(start)).total_seconds() / 3600


def is_external(association: str) -> bool:
    return association not in MAINTAINER


def first_maintainer_response_hours(
    opened_at: str, author: str, events: list[dict]
) -> float | None:
    answers = [
        hours_between(opened_at, e["at"])
        for e in events
        if e["user"] != author and e["association"] in MAINTAINER and not e["bot"]
    ]
    return min(answers) if answers else None


def _median(values: list[float]) -> float | None:
    return statistics.median(values) if values else None


def summarize(records: list[dict]) -> dict:
    external = [r for r in records if r["external"]]
    n = len(external)

    def pct(state: str) -> float | None:
        return 100 * sum(r["state"] == state for r in external) / n if n else None

    answered = [
        r["first_response_hours"] for r in external if r["first_response_hours"] is not None
    ]
    merged = [r["hours_to_close"] for r in external if r["state"] == "merged"]
    return {
        "count": n,
        "merged_pct": pct("merged"),
        "closed_unmerged_pct": pct("closed"),
        "open_pct": pct("open"),
        "no_response_pct": 100 * (n - len(answered)) / n if n else None,
        "median_first_response_hours": _median(answered),
        "median_hours_to_merge": _median(merged),
    }


def gh_pages(path: str, *args: str) -> list:
    out = subprocess.run(
        ["gh", "api", "-X", "GET", "--paginate", "--slurp", path, *args],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    return [
        item
        for page in json.loads(out)
        for item in (page.get("items", []) if isinstance(page, dict) else page)
    ]


def events_for(repo: str, number: int, is_pr: bool) -> list[dict]:
    events = [
        {
            "at": c["created_at"],
            "user": c["user"]["login"],
            "association": c["author_association"],
            "bot": c["user"]["type"] == "Bot",
        }
        for c in gh_pages(f"repos/{repo}/issues/{number}/comments", "-f", "per_page=100")
    ]
    if is_pr:
        events += [
            {
                "at": r["submitted_at"],
                "user": r["user"]["login"],
                "association": r["author_association"],
                "bot": r["user"]["type"] == "Bot",
            }
            for r in gh_pages(f"repos/{repo}/pulls/{number}/reviews", "-f", "per_page=100")
            if r.get("submitted_at")
        ]
    return events


def to_record(repo: str, item: dict) -> dict:
    is_pr = "pull_request" in item
    merged_at = (item.get("pull_request") or {}).get("merged_at")
    if merged_at:
        state, closed_at = "merged", merged_at
    elif item["state"] == "closed":
        state, closed_at = "closed", item["closed_at"]
    else:
        state, closed_at = "open", None
    events = events_for(repo, item["number"], is_pr)
    return {
        "kind": "pr" if is_pr else "issue",
        "external": is_external(item["author_association"]),
        "state": state,
        "first_response_hours": first_maintainer_response_hours(
            item["created_at"], item["user"]["login"], events
        ),
        "hours_to_close": hours_between(item["created_at"], closed_at) if closed_at else None,
    }


def collect(repo: str, days: int) -> list[dict]:
    since = (datetime.now(UTC) - timedelta(days=days)).strftime("%Y-%m-%d")
    items = gh_pages(
        "search/issues", "-f", f"q=repo:{repo} created:>={since}", "-f", "per_page=100"
    )
    with ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(lambda item: to_record(repo, item), items))


def fmt(value: float | None, unit: str = "") -> str:
    return "n/a" if value is None else f"{value:.1f}{unit}"


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("repos", nargs="+")
    parser.add_argument("--days", type=int, default=90)
    args = parser.parse_args(argv)
    print(f"Window: last {args.days} days. External = author is not owner, member or collaborator.")
    print()
    columns = [
        ("n", "count"),
        ("merged %", "merged_pct"),
        ("closed unmerged %", "closed_unmerged_pct"),
        ("still open %", "open_pct"),
        ("no response %", "no_response_pct"),
        ("median first response (h)", "median_first_response_hours"),
        ("median to merge (h)", "median_hours_to_merge"),
    ]
    print("| repo | kind | " + " | ".join(label for label, _ in columns) + " |")
    print("|" + "---|" * (len(columns) + 2))
    for repo in args.repos:
        records = collect(repo, args.days)
        for kind in ("pr", "issue"):
            s = summarize([r for r in records if r["kind"] == kind])
            cells = [str(s["count"])] + [fmt(s[key]) for _, key in columns[1:]]
            print(f"| {repo} | {kind} | " + " | ".join(cells) + " |")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
