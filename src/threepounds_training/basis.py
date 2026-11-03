from typing import Literal

from pydantic import BaseModel

Value = float | str


class BasisEntry(BaseModel):
    name: str
    value: Value
    tolerance: float | None = None


class Change(BaseModel):
    name: str
    was: Value
    now: Value | None


class Assessment(BaseModel):
    valid: bool
    changed: list[Change]
    allowed_updates: list[Literal["patch", "redesign"]]


def _differs(entry: BasisEntry, now: Value | None) -> bool:
    if now is None:
        return True
    if isinstance(entry.value, str) or isinstance(now, str) or entry.tolerance is None:
        return now != entry.value
    return abs(now - entry.value) > entry.tolerance


def assess(basis: list[BasisEntry], current: dict[str, Value]) -> Assessment:
    changed = [
        Change(name=e.name, was=e.value, now=current.get(e.name))
        for e in basis
        if _differs(e, current.get(e.name))
    ]
    return Assessment(
        valid=not changed,
        changed=changed,
        allowed_updates=["redesign"] if changed else ["patch", "redesign"],
    )
