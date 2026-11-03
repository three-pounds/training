from typing import Literal

from mcp.server.mcpserver import MCPServer

from threepounds_training.basis import Assessment, BasisEntry, Value, assess
from threepounds_training.reevaluation import Scan, Verdict, reevaluate
from threepounds_training.registry import REGISTRY, Check, Registry, check_citations
from threepounds_training.screening import DelayReason, Question, Readiness, screen

MEDICAL_NOTICE = (
    "This is not medical advice. It is a training method, not a substitute for a physician. "
    "If you have a medical condition or symptoms, see a doctor before training."
)


def build_server(registry: Registry | None = None) -> MCPServer:
    registry = REGISTRY if registry is None else registry
    server = MCPServer("threepounds-training", instructions=MEDICAL_NOTICE)

    @server.tool()
    def assess_decision_basis(basis: list[BasisEntry], current: dict[str, Value]) -> Assessment:
        """Check whether the variables that justified a program's methodology still hold.

        If any variable moved beyond its tolerance (or is missing), the methodology is
        invalidated: only a full redesign is allowed, never a patch of the previous program.
        """
        return assess(basis, current)

    @server.tool()
    def reevaluate_body_composition(
        scans: list[Scan],
        lean_tolerance_kg: float | None = None,
        protein_g_per_kg_ffm: float | None = None,
        strength_trend: Literal["up", "flat", "down"] | None = None,
    ) -> Verdict:
        """Decide the next step after body-composition scans, in a fixed professional order.

        Verify scan conditions, then the loss rate, then protein, then strength; the training
        methodology is reviewed last. Nutrition findings are handed off, never prescribed.
        """
        return reevaluate(scans, lean_tolerance_kg, protein_g_per_kg_ffm, strength_trend)

    @server.tool()
    def check_decision_citations(citations: list[str], person_tags: list[str]) -> Check:
        """Validate the evidence a decision cites against the evidence registry.

        Rejects a decision with no citation or with a citation that is not in the registry,
        and flags citations that conflict with each other or do not apply to the person.
        """
        return check_citations(citations, person_tags, registry)

    @server.tool()
    def screen_readiness(
        yes_to_general: list[Question],
        yes_to_followup: bool | None = None,
        delay_reasons: list[DelayReason] | None = None,
    ) -> Readiness:
        """Apply the official PAR-Q+ outcome to the answers the person reports.

        Takes only the question numbers answered yes on the official form, which the person
        completes at the official site; the question text is never reproduced here. A yes to
        question 2 or 7 stops the design and recommends a physician.
        """
        return screen(yes_to_general, yes_to_followup, delay_reasons)

    return server
