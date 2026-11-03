import pytest
from mcp.client.client import Client

from threepounds_training.server import build_server


def scan(on, weight, lean, standardized=True):
    return {"on": on, "weight_kg": weight, "lean_kg": lean, "standardized": standardized}


FIRST = scan("2026-09-01", 80.0, 60.0)
IN_BAND = scan("2026-09-15", 79.0, 57.0)
TOO_FAST = scan("2026-09-15", 77.5, 57.0)
LEAN_KEPT = scan("2026-09-15", 79.0, 59.8)


async def reevaluate(scans, **inputs):
    async with Client(build_server()) as client:
        result = await client.call_tool("reevaluate_body_composition", {"scans": scans, **inputs})
    return result.structured_content


@pytest.mark.anyio
async def test_a_scan_taken_under_different_conditions_must_be_repeated_first():
    out = await reevaluate([FIRST, scan("2026-09-15", 79.0, 57.0, standardized=False)])
    assert out["leaf"] == "rescan_standardized"
    assert out["handoff"] == "none"


@pytest.mark.anyio
async def test_a_single_scan_is_not_enough_evidence():
    out = await reevaluate([FIRST])
    assert out["leaf"] == "insufficient_evidence"
    assert "scans" in out["missing"]


@pytest.mark.anyio
async def test_weight_loss_faster_than_the_band_reduces_the_deficit_via_nutrition():
    out = await reevaluate([FIRST, TOO_FAST])
    assert out["leaf"] == "reduce_deficit"
    assert out["handoff"] == "nutrition"
    assert out["evidence"][0]["firmness"] == "position_stand"


@pytest.mark.anyio
async def test_lean_loss_without_a_verified_tolerance_is_not_acted_on():
    out = await reevaluate([FIRST, IN_BAND])
    assert out["leaf"] == "insufficient_evidence"
    assert "lean_tolerance_kg" in out["missing"]


@pytest.mark.anyio
async def test_a_lean_change_within_tolerance_holds_course():
    out = await reevaluate([FIRST, LEAN_KEPT], lean_tolerance_kg=1.0)
    assert out["leaf"] == "hold_course"


@pytest.mark.anyio
async def test_lean_loss_with_low_protein_flags_protein_before_anything_else():
    out = await reevaluate(
        [FIRST, IN_BAND],
        lean_tolerance_kg=1.0,
        protein_g_per_kg_ffm=1.8,
        strength_trend="down",
    )
    assert out["leaf"] == "raise_protein"
    assert out["handoff"] == "nutrition"


@pytest.mark.anyio
async def test_the_methodology_is_reviewed_last_and_only_if_strength_also_falls():
    inputs = {"lean_tolerance_kg": 1.0, "protein_g_per_kg_ffm": 2.5}
    falling = await reevaluate([FIRST, IN_BAND], strength_trend="down", **inputs)
    assert falling["leaf"] == "review_methodology"
    steady = await reevaluate([FIRST, IN_BAND], strength_trend="flat", **inputs)
    assert steady["leaf"] == "keep_method_monitor"
