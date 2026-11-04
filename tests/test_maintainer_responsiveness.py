import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "maintainer_responsiveness",
    Path(__file__).parents[1] / "scripts" / "maintainer_responsiveness.py",
)
mr = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(mr)

OPENED = "2026-10-01T00:00:00Z"


def event(at, user, association="NONE", bot=False):
    return {"at": at, "user": user, "association": association, "bot": bot}


def test_first_response_is_the_earliest_maintainer_who_is_not_the_author_or_a_bot():
    events = [
        event("2026-10-01T01:00:00Z", "author", "OWNER"),
        event("2026-10-01T02:00:00Z", "stale-bot", "OWNER", bot=True),
        event("2026-10-01T03:00:00Z", "stranger", "NONE"),
        event("2026-10-01T10:00:00Z", "maint", "MEMBER"),
        event("2026-10-01T06:00:00Z", "other", "COLLABORATOR"),
    ]
    assert mr.first_maintainer_response_hours(OPENED, "author", events) == 6


def test_first_response_is_none_when_no_maintainer_answered():
    events = [event("2026-10-01T03:00:00Z", "stranger", "NONE")]
    assert mr.first_maintainer_response_hours(OPENED, "author", events) is None


def test_external_means_the_author_is_not_a_maintainer():
    assert mr.is_external("CONTRIBUTOR")
    assert mr.is_external("FIRST_TIME_CONTRIBUTOR")
    assert mr.is_external("NONE")
    assert not mr.is_external("OWNER")
    assert not mr.is_external("MEMBER")
    assert not mr.is_external("COLLABORATOR")


def record(external, state, first_response=None, hours_to_close=None):
    return {
        "external": external,
        "state": state,
        "first_response_hours": first_response,
        "hours_to_close": hours_to_close,
    }


def test_summary_counts_only_external_items_and_reports_the_shares_and_medians():
    records = [
        record(True, "merged", first_response=2, hours_to_close=48),
        record(True, "merged", first_response=10, hours_to_close=24),
        record(True, "closed", first_response=4, hours_to_close=100),
        record(True, "open"),
        record(False, "merged", first_response=1, hours_to_close=1),
    ]
    out = mr.summarize(records)
    assert out["count"] == 4
    assert out["merged_pct"] == 50
    assert out["closed_unmerged_pct"] == 25
    assert out["open_pct"] == 25
    assert out["no_response_pct"] == 25
    assert out["median_first_response_hours"] == 4
    assert out["median_hours_to_merge"] == 36


def test_every_github_read_is_an_explicit_get(monkeypatch):
    """gh turns a request with -f fields into a POST unless the method is stated."""
    calls = []

    class Done:
        stdout = "[]"

    def fake_run(cmd, **kwargs):
        calls.append(cmd)
        return Done()

    monkeypatch.setattr(mr.subprocess, "run", fake_run)
    mr.gh_pages("repos/o/r/issues/1/comments", "-f", "per_page=100")
    cmd = calls[0]
    assert cmd[cmd.index("-X") + 1] == "GET"


def test_summary_of_nothing_does_not_divide_by_zero():
    out = mr.summarize([record(False, "merged", first_response=1, hours_to_close=1)])
    assert out["count"] == 0
    assert out["median_first_response_hours"] is None
