import pytest
from mcp.client.client import Client

from threepounds_training.server import build_server

FLOWS = ["nuevo-programa", "revisar-semana"]


@pytest.mark.anyio
@pytest.mark.parametrize("flow", FLOWS)
async def test_every_flow_opens_with_the_medical_notice(flow):
    async with Client(build_server()) as client:
        result = await client.get_prompt(flow)
    first = result.messages[0].content.text
    assert first.lower().startswith("this is not medical advice")
