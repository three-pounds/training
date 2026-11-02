"""Fail if tracked files contain private terms (names, conditions, personal figures).

The term list never lives in the repo: CI reads it from the PRIVATE_DENYLIST secret,
a local run reads the git-ignored .private-denylist file. One term per line; '#' comments.
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

DEFAULT_FILE = Path(".private-denylist")


def load_patterns(path: Path = DEFAULT_FILE) -> list[str]:
    raw = os.environ.get("PRIVATE_DENYLIST")
    if raw is None and path.exists():
        raw = path.read_text(encoding="utf-8")
    if not raw:
        return []
    terms = (line.strip().lower() for line in raw.splitlines())
    return [t for t in terms if t and not t.startswith("#")]


def find_hits(texts: dict[str, str], patterns: list[str]) -> list[tuple[str, int, str]]:
    compiled = [(p, re.compile(rf"(?<!\w){re.escape(p)}(?!\w)", re.IGNORECASE)) for p in patterns]
    hits = []
    for name, text in texts.items():
        for lineno, line in enumerate(text.splitlines(), start=1):
            for term, rx in compiled:
                if rx.search(line):
                    hits.append((name, lineno, term))
    return hits


def tracked_texts() -> dict[str, str]:
    files = subprocess.run(
        ["git", "ls-files", "-z"], check=True, capture_output=True, text=True
    ).stdout.split("\0")
    out = {}
    for f in filter(None, files):
        try:
            out[f] = Path(f).read_text(encoding="utf-8")
        except UnicodeDecodeError, FileNotFoundError:
            continue
    return out


def main() -> int:
    patterns = load_patterns()
    if not patterns:
        if os.environ.get("CI") and os.environ.get("REQUIRE_DENYLIST") == "1":
            print("PRIVATE_DENYLIST is required on this branch but is empty", file=sys.stderr)
            return 1
        print("no private denylist configured; skipping", file=sys.stderr)
        return 0
    hits = find_hits(tracked_texts(), patterns)
    for name, lineno, _term in hits:
        # never print the term itself: CI logs are public
        print(f"{name}:{lineno}: private term found", file=sys.stderr)
    return 1 if hits else 0


if __name__ == "__main__":
    sys.exit(main())
