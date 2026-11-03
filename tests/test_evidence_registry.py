import pytest
from mcp.client.client import Client

from threepounds_training.registry import Entry
from threepounds_training.server import build_server

REGISTRY = {
    e.id: e
    for e in [
        Entry(id="a", claim="a", firmness="position_stand", conflicts_with=["b"]),
        Entry(id="b", claim="b", firmness="single_study"),
        Entry(id="c", claim="c", firmness="position_stand", requires_tags=["lean"]),
    ]
}


async def check(citations, person_tags=(), registry=REGISTRY):
    async with Client(build_server(registry=registry)) as client:
        result = await client.call_tool(
            "check_decision_citations",
            {"citations": list(citations), "person_tags": list(person_tags)},
        )
    return result.structured_content


def kinds(out):
    return [p["kind"] for p in out["problems"]]


@pytest.mark.anyio
async def test_a_decision_without_citations_is_rejected():
    out = await check([])
    assert out["ok"] is False
    assert kinds(out) == ["no_citation"]


@pytest.mark.anyio
async def test_a_citation_missing_from_the_registry_is_rejected():
    out = await check(["a", "made-up-2031"])
    assert out["ok"] is False
    assert out["problems"] == [
        {"kind": "unknown_citation", "citation": "made-up-2031", "other": None}
    ]


@pytest.mark.anyio
async def test_two_citations_marked_incompatible_are_flagged_together():
    out = await check(["b", "a"])
    assert out["ok"] is False
    assert kinds(out) == ["incompatible"]
    assert {out["problems"][0]["citation"], out["problems"][0]["other"]} == {"a", "b"}


@pytest.mark.anyio
async def test_a_citation_that_does_not_apply_to_the_person_is_flagged():
    out = await check(["c"], person_tags=["beginner"])
    assert out["ok"] is False
    assert kinds(out) == ["not_applicable"]


@pytest.mark.anyio
async def test_compatible_applicable_known_citations_pass():
    out = await check(["b", "c"], person_tags=["lean"])
    assert out == {"ok": True, "problems": []}


@pytest.mark.anyio
async def test_every_source_the_reevaluation_tree_cites_exists_in_the_registry():
    scans = [
        {"on": "2026-09-01", "weight_kg": 80.0, "lean_kg": 60.0, "standardized": True},
        {"on": "2026-09-15", "weight_kg": 77.5, "lean_kg": 57.0, "standardized": False},
    ]
    fast = [{**scans[1], "standardized": True}]
    async with Client(build_server()) as client:
        cited = set()
        for batch in (scans, [scans[0], *fast]):
            verdict = await client.call_tool("reevaluate_body_composition", {"scans": batch})
            cited |= {e["source"] for e in verdict.structured_content["evidence"]}
        steady = await client.call_tool(
            "reevaluate_body_composition",
            {
                "scans": [
                    scans[0],
                    {"on": "2026-09-15", "weight_kg": 79.0, "lean_kg": 57.0, "standardized": True},
                ],
                "lean_tolerance_kg": 1.0,
                "protein_g_per_kg_ffm": 2.5,
                "strength_trend": "down",
            },
        )
        cited |= {e["source"] for e in steady.structured_content["evidence"]}
        out = await client.call_tool(
            "check_decision_citations",
            {"citations": sorted(cited), "person_tags": ["resistance_trained"]},
        )
    assert len(cited) == 3
    assert out.structured_content["problems"] == []
