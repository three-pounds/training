import pytest
from mcp.client.client import Client

from threepounds_training.server import build_server


async def screen(yes_to_general=(), yes_to_followup=None, delay_reasons=()):
    async with Client(build_server()) as client:
        result = await client.call_tool(
            "screen_readiness",
            {
                "yes_to_general": list(yes_to_general),
                "yes_to_followup": yes_to_followup,
                "delay_reasons": list(delay_reasons),
            },
        )
    return result.structured_content


@pytest.mark.anyio
@pytest.mark.parametrize("question", [2, 7])
async def test_a_yes_to_chest_pain_or_supervised_only_stops_the_design(question):
    out = await screen(yes_to_general=[1, question])
    assert out["leaf"] == "stop_see_a_doctor"
    assert out["may_design"] is False


@pytest.mark.anyio
async def test_a_yes_elsewhere_needs_the_followup_before_anything():
    out = await screen(yes_to_general=[1])
    assert out["leaf"] == "complete_followup"
    assert out["may_design"] is False


@pytest.mark.anyio
async def test_a_yes_in_the_followup_means_a_professional_first():
    out = await screen(yes_to_general=[5], yes_to_followup=True)
    assert out["leaf"] == "seek_professional_first"
    assert out["may_design"] is False


@pytest.mark.anyio
async def test_all_no_in_the_followup_clears_the_person():
    out = await screen(yes_to_general=[5], yes_to_followup=False)
    assert out["leaf"] == "cleared"
    assert out["may_design"] is True


@pytest.mark.anyio
async def test_all_general_answers_no_clears_the_person():
    out = await screen()
    assert out["leaf"] == "cleared"
    assert out["may_design"] is True


@pytest.mark.anyio
@pytest.mark.parametrize("reason", ["temporary_illness", "pregnancy", "health_change"])
async def test_a_reason_to_delay_postpones_even_when_everything_else_is_no(reason):
    out = await screen(delay_reasons=[reason])
    assert out["leaf"] == "delay"
    assert out["may_design"] is False


@pytest.mark.anyio
async def test_question_numbers_outside_the_seven_are_rejected():
    async with Client(build_server()) as client:
        result = await client.call_tool(
            "screen_readiness",
            {"yes_to_general": [8], "yes_to_followup": None, "delay_reasons": []},
        )
    assert result.is_error
