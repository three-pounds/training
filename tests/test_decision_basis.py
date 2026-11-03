import pytest
from mcp.client.client import Client

from threepounds_training.server import build_server

BASIS = [
    {"name": "goal", "value": "fat_loss"},
    {"name": "lean_mass_kg", "value": 60.0, "tolerance": 1.0},
]


async def assess(basis, current):
    async with Client(build_server()) as client:
        result = await client.call_tool(
            "assess_decision_basis", {"basis": basis, "current": current}
        )
    return result.structured_content


@pytest.mark.anyio
async def test_a_variable_beyond_its_tolerance_invalidates_the_basis():
    out = await assess(BASIS, {"goal": "fat_loss", "lean_mass_kg": 57.5})
    assert out["valid"] is False
    assert [c["name"] for c in out["changed"]] == ["lean_mass_kg"]
    assert out["changed"][0]["was"] == 60.0
    assert out["changed"][0]["now"] == 57.5


@pytest.mark.anyio
async def test_unchanged_variables_keep_the_basis_valid():
    out = await assess(BASIS, {"goal": "fat_loss", "lean_mass_kg": 60.8})
    assert out["valid"] is True
    assert out["changed"] == []
    assert out["allowed_updates"] == ["patch", "redesign"]


@pytest.mark.anyio
async def test_an_invalidated_basis_refuses_patches_and_demands_a_redesign():
    out = await assess(BASIS, {"goal": "hypertrophy", "lean_mass_kg": 60.0})
    assert out["valid"] is False
    assert out["allowed_updates"] == ["redesign"]


@pytest.mark.anyio
async def test_a_variable_missing_from_the_current_data_invalidates_the_basis():
    out = await assess(BASIS, {"goal": "fat_loss"})
    assert out["valid"] is False
    assert out["changed"][0]["name"] == "lean_mass_kg"
    assert out["changed"][0]["now"] is None
