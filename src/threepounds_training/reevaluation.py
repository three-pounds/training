from datetime import date
from typing import Literal

from pydantic import BaseModel

Firmness = Literal["position_stand", "single_study", "inference"]
Leaf = Literal[
    "rescan_standardized",
    "insufficient_evidence",
    "reduce_deficit",
    "hold_course",
    "raise_protein",
    "review_methodology",
    "keep_method_monitor",
]

MAX_LOSS_PCT_PER_WEEK = 1.0
MIN_PROTEIN_G_PER_KG_FFM = 2.3

ISSN_2017 = {"source": "issn-2017-diets-and-body-composition", "firmness": "position_stand"}
INBODY_770 = {"source": "inbody-770-reliability-2024", "firmness": "single_study"}
PRACTICE_ORDER = {"source": "professional-decision-order", "firmness": "inference"}


class Citation(BaseModel):
    source: str
    firmness: Firmness


class Scan(BaseModel):
    on: date
    weight_kg: float
    lean_kg: float
    standardized: bool


class Verdict(BaseModel):
    leaf: Leaf
    reason: str
    handoff: Literal["none", "nutrition"]
    missing: list[str] = []
    evidence: list[Citation] = []


def _verdict(leaf, reason, handoff="none", missing=(), evidence=()):
    return Verdict(
        leaf=leaf,
        reason=reason,
        handoff=handoff,
        missing=list(missing),
        evidence=[Citation(**e) for e in evidence],
    )


def _insufficient(reason, *missing):
    return _verdict("insufficient_evidence", reason, missing=missing)


def reevaluate(
    scans: list[Scan],
    lean_tolerance_kg: float | None = None,
    protein_g_per_kg_ffm: float | None = None,
    strength_trend: Literal["up", "flat", "down"] | None = None,
) -> Verdict:
    if not all(s.standardized for s in scans):
        return _verdict(
            "rescan_standardized",
            "A scan was taken under different conditions; repeat it under the same ones first.",
            evidence=[INBODY_770],
        )
    ordered = sorted(scans, key=lambda s: s.on)
    if len(ordered) < 2 or ordered[-1].on == ordered[0].on:
        return _insufficient("At least two scans on different days are needed.", "scans")
    first, last = ordered[0], ordered[-1]
    weeks = (last.on - first.on).days / 7
    loss_pct_per_week = (first.weight_kg - last.weight_kg) / first.weight_kg * 100 / weeks
    if loss_pct_per_week > MAX_LOSS_PCT_PER_WEEK:
        return _verdict(
            "reduce_deficit",
            "Body weight is falling faster than the supported weekly rate.",
            handoff="nutrition",
            evidence=[ISSN_2017],
        )
    lean_drop = first.lean_kg - last.lean_kg
    if lean_drop <= 0:
        return _verdict("hold_course", "Lean mass did not drop.")
    if lean_tolerance_kg is None:
        return _insufficient(
            "Lean mass dropped but no verified measurement tolerance was provided.",
            "lean_tolerance_kg",
        )
    if lean_drop <= lean_tolerance_kg:
        return _verdict("hold_course", "The lean-mass change is within measurement tolerance.")
    if protein_g_per_kg_ffm is None:
        return _insufficient("Protein intake is needed to read a lean-mass drop.", "protein")
    if protein_g_per_kg_ffm < MIN_PROTEIN_G_PER_KG_FFM:
        return _verdict(
            "raise_protein",
            "Protein is below the range supported for lean lifters in a deficit.",
            handoff="nutrition",
            evidence=[ISSN_2017],
        )
    if strength_trend is None:
        return _insufficient("The strength trend is needed before judging the method.", "strength")
    if strength_trend == "down":
        return _verdict(
            "review_methodology",
            "Lean mass and strength fell with rate and protein in range: review the methodology.",
            evidence=[PRACTICE_ORDER],
        )
    return _verdict(
        "keep_method_monitor",
        "Strength holds: keep the method and rescan under the same conditions.",
        evidence=[PRACTICE_ORDER],
    )
