import pytest
from mcp.client.client import Client

from threepounds_training.server import build_server


@pytest.mark.anyio
async def test_instructions_carry_the_medical_notice():
    async with Client(build_server()) as client:
        assert "not medical advice" in client.instructions.lower()
