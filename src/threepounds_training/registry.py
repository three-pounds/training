from typing import Literal

from pydantic import BaseModel

Firmness = Literal["position_stand", "single_study", "inference"]


class Entry(BaseModel):
    id: str
    claim: str
    firmness: Firmness
    requires_tags: list[str] = []
    conflicts_with: list[str] = []


class Problem(BaseModel):
    kind: Literal["no_citation", "unknown_citation", "incompatible", "not_applicable"]
    citation: str | None = None
    other: str | None = None


class Check(BaseModel):
    ok: bool
    problems: list[Problem]


Registry = dict[str, Entry]

REGISTRY: Registry = {
    e.id: e
    for e in [
        Entry(
            id="issn-2017-diets-and-body-composition",
            claim=(
                "Weekly loss of 0.5-1.0% of body weight (contest prep); 2.3-3.1 g/kg of "
                "fat-free mass of protein for lean, resistance-trained people in a deficit."
            ),
            firmness="position_stand",
            requires_tags=["resistance_trained"],
        ),
        Entry(
            id="inbody-770-reliability-2024",
            claim=(
                "Very repeatable between scans, but about 2-3 kg off versus DXA for fat and "
                "fat-free mass; no minimal detectable change reported."
            ),
            firmness="single_study",
        ),
        Entry(
            id="professional-decision-order",
            claim=(
                "Reevaluation order: verify the scan, loss rate, protein, strength, then "
                "methodology. A synthesis, not a published guideline."
            ),
            firmness="inference",
        ),
    ]
}


def check_citations(citations: list[str], person_tags: list[str], registry: Registry) -> Check:
    if not citations:
        return Check(ok=False, problems=[Problem(kind="no_citation")])
    problems = [
        Problem(kind="unknown_citation", citation=c) for c in citations if c not in registry
    ]
    known = [registry[c] for c in citations if c in registry]
    seen_pairs = set()
    for entry in known:
        for other in entry.conflicts_with:
            pair = frozenset((entry.id, other))
            both_cited = other in citations and entry.id in citations
            if both_cited and pair not in seen_pairs:
                seen_pairs.add(pair)
                problems.append(Problem(kind="incompatible", citation=entry.id, other=other))
        if not set(entry.requires_tags) <= set(person_tags):
            problems.append(Problem(kind="not_applicable", citation=entry.id))
    return Check(ok=not problems, problems=problems)
