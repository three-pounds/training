from typing import Annotated, Literal

from pydantic import BaseModel, Field

OFFICIAL_FORM_URL = "https://www.eparmedx.com"
STOP_QUESTIONS = {2, 7}

Question = Annotated[int, Field(ge=1, le=7)]
DelayReason = Literal["temporary_illness", "pregnancy", "health_change"]


class Readiness(BaseModel):
    leaf: Literal[
        "stop_see_a_doctor",
        "seek_professional_first",
        "delay",
        "complete_followup",
        "cleared",
    ]
    may_design: bool
    next_step: str


def _result(leaf, may_design, next_step):
    return Readiness(leaf=leaf, may_design=may_design, next_step=next_step)


def screen(
    yes_to_general: list[Question],
    yes_to_followup: bool | None = None,
    delay_reasons: list[DelayReason] | None = None,
) -> Readiness:
    if STOP_QUESTIONS & set(yes_to_general):
        return _result(
            "stop_see_a_doctor",
            False,
            "Do not design a program. Recommend seeing a physician before any training.",
        )
    if yes_to_followup:
        return _result(
            "seek_professional_first",
            False,
            f"Do not design yet. The person should see a qualified exercise professional "
            f"or complete the follow-up tools at {OFFICIAL_FORM_URL} first.",
        )
    if delay_reasons:
        return _result(
            "delay",
            False,
            "Do not design now. Wait until the temporary illness passes, or talk to a health "
            "professional first if pregnant or if health has changed.",
        )
    if yes_to_general and yes_to_followup is None:
        return _result(
            "complete_followup",
            False,
            f"Ask the person to complete the follow-up pages of the official form at "
            f"{OFFICIAL_FORM_URL} and report whether any follow-up answer was yes.",
        )
    return _result(
        "cleared",
        True,
        "The person is cleared by the official form. A qualified exercise professional "
        "is still advised.",
    )
