from mcp.server.mcpserver import MCPServer

MEDICAL_NOTICE = (
    "This is not medical advice. It is a training method, not a substitute for a physician. "
    "If you have a medical condition or symptoms, see a doctor before training."
)


def build_server() -> MCPServer:
    return MCPServer("threepounds-training", instructions=MEDICAL_NOTICE)
