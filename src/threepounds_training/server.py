from mcp.server.mcpserver import MCPServer

from threepounds_training.basis import Assessment, BasisEntry, Value, assess

MEDICAL_NOTICE = (
    "This is not medical advice. It is a training method, not a substitute for a physician. "
    "If you have a medical condition or symptoms, see a doctor before training."
)


def build_server() -> MCPServer:
    server = MCPServer("threepounds-training", instructions=MEDICAL_NOTICE)

    @server.tool()
    def assess_decision_basis(basis: list[BasisEntry], current: dict[str, Value]) -> Assessment:
        """Check whether the variables that justified a program's methodology still hold.

        If any variable moved beyond its tolerance (or is missing), the methodology is
        invalidated: only a full redesign is allowed, never a patch of the previous program.
        """
        return assess(basis, current)

    return server
