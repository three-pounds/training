"""Map one person's exercise names to wger catalog ids, automatically when it is clear.

Each source exercise is scored against the wger catalog with a plain, explicit rule. A candidate
is approved without a person only if its score reaches the threshold, it wins by a margin over
the runner-up, and its equipment does not contradict the equipment named in the source. Anything
else is shown one exercise at a time, in full, and a person decides. Progress is saved after every
decision, so the work can be stopped and resumed.

    uv run python scripts/map_exercises.py --keys KEYS --out MAP.json --catalog CATALOG.json
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import unicodedata
import urllib.request
from pathlib import Path

CATALOG_URL = "https://wger.de/api/v2/exerciseinfo/?language=2&limit=100"
ENGLISH, SPANISH = 2, 4
STRONG_EQUIPMENT = {"dumbbell", "barbell", "cable"}
SPANISH_EQUIPMENT = {"mancuerna": "dumbbell", "polea": "cable", "barra": "barbell"}
ABBREVIATIONS = {"db": "dumbbell", "dbs": "dumbbell", "bb": "barbell"}


def tokens(text: str) -> set[str]:
    plain = unicodedata.normalize("NFKD", text.lower())
    plain = "".join(c for c in plain if not unicodedata.combining(c))
    out = set()
    for word in re.findall(r"[a-z0-9]+", plain):
        word = ABBREVIATIONS.get(word, word)
        if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
            word = word[:-1]
        out.add(word)
    return out


def dice(a: set[str], b: set[str]) -> float:
    return 2 * len(a & b) / (len(a) + len(b)) if a or b else 0.0


def expected_equipment(words: set[str]) -> set[str]:
    return (words & STRONG_EQUIPMENT) | {
        SPANISH_EQUIPMENT[w] for w in words if w in SPANISH_EQUIPMENT
    }


def equipment_conflict(expected: set[str], candidate: dict) -> bool:
    if not expected:
        return False
    names = " ".join(candidate["equipment"]).lower()
    return not any(word in names for word in expected)


def rank(key: str, name: str, candidates: list[dict]) -> list[tuple[float, dict]]:
    key_words, name_words = tokens(key.replace("_", " ")), tokens(name)
    scored = []
    for cand in candidates:
        english, spanish = tokens(cand["en_name"]), tokens(cand["es_name"])
        score = max(
            dice(key_words, english),
            dice(name_words, english),
            dice(name_words, spanish),
            dice(key_words, spanish),
        )
        scored.append((score, cand))
    return sorted(scored, key=lambda pair: pair[0], reverse=True)


def decide(ranked: list[tuple[float, dict]], expected: set[str], threshold: float, margin: float):
    if not ranked:
        return {"auto": False, "reason": "no candidates"}
    best_score, best = ranked[0]
    gap = best_score - ranked[1][0] if len(ranked) > 1 else best_score
    reason = f"score {best_score:.2f}, margin {gap:.2f}"
    if equipment_conflict(expected, best):
        return {"auto": False, "reason": f"{reason}, equipment does not match"}
    if best_score < threshold:
        return {"auto": False, "reason": f"{reason}, below threshold {threshold:.2f}"}
    if gap < margin - 1e-9:
        return {"auto": False, "reason": f"{reason}, runner-up too close"}
    return {"auto": True, "reason": f"{reason}, no equipment conflict"}


def strip_html(text: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", text))).strip()


def to_candidate(raw: dict) -> dict | None:
    by_language = {t["language"]: t for t in raw.get("translations", [])}
    if ENGLISH not in by_language:
        return None
    english, spanish = by_language[ENGLISH], by_language.get(SPANISH, {})
    return {
        "id": raw["id"],
        "en_name": english["name"],
        "es_name": spanish.get("name", ""),
        "equipment": [e["name"] for e in raw.get("equipment", [])],
        "muscles": [m["name"] for m in raw.get("muscles", [])],
        "muscles_secondary": [m["name"] for m in raw.get("muscles_secondary", [])],
        "descriptions": {
            "en": strip_html(english.get("description", "")),
            "es": strip_html(spanish.get("description", "")),
        },
        "variation_group": raw.get("variation_group"),
    }


def read_regular_keys(text: str) -> list[tuple[str, str]]:
    section, out = None, []
    for line in text.splitlines():
        header = re.match(r"#\s*\[([^\]]+)\]", line)
        if header:
            section = header.group(1)
        elif section == "regular" and "|" in line and not line.startswith("#"):
            key, name = (part.strip() for part in line.split("|", 1))
            out.append((key, name))
    return out


def auto_entry(cand: dict, reason: str) -> dict:
    return {
        "wger_id": cand["id"],
        "name": cand["en_name"],
        "status": "auto",
        "confirmed_by": "auto-rule",
        "sources": [f"wger:{cand['id']}"],
        "note": reason,
    }


def manual_entry(cand: dict, note: str) -> dict:
    if not note.strip():
        raise ValueError("a manual decision needs a note saying why")
    return {
        "wger_id": cand["id"],
        "name": cand["en_name"],
        "status": "approved",
        "confirmed_by": "human",
        "sources": [f"wger:{cand['id']}"],
        "note": note.strip(),
    }


def pending_entry(note: str) -> dict:
    return {
        "wger_id": None,
        "name": None,
        "status": "pending",
        "confirmed_by": "human",
        "sources": [],
        "note": note.strip() or "no candidate fits",
    }


def render_card(key: str, name: str, ranked: list[tuple[float, dict]], siblings: dict) -> str:
    lines = [f"=== {key}  |  source name: {name}", ""]
    for number, (score, cand) in enumerate(ranked, start=1):
        group = [n for n in siblings.get(cand["variation_group"], []) if n != cand["en_name"]]
        lines += [
            f"[{number}] id {cand['id']}  score {score:.2f}",
            f"    English: {cand['en_name']}",
            f"    Spanish: {cand['es_name'] or '-'}",
            f"    Equipment: {', '.join(cand['equipment']) or '-'}",
            f"    Primary muscles: {', '.join(cand['muscles']) or '-'}",
            f"    Secondary muscles: {', '.join(cand['muscles_secondary']) or '-'}",
            f"    Same variation group: {', '.join(group) or '-'}",
            f"    Description (English): {cand['descriptions']['en'].strip() or '-'}",
            f"    Description (Spanish): {cand['descriptions']['es'].strip() or '-'}",
            "",
        ]
    return "\n".join(lines)


def fetch_catalog(path: Path) -> list[dict]:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    raw, url = [], CATALOG_URL
    while url:
        with urllib.request.urlopen(url, timeout=30) as response:
            page = json.load(response)
        raw += page["results"]
        url = page["next"]
    catalog = [c for c in map(to_candidate, raw) if c]
    path.write_text(json.dumps(catalog, ensure_ascii=False), encoding="utf-8")
    return catalog


def save(path: Path, entries: dict) -> None:
    path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")


def plan(keys, saved, catalog, threshold, margin, shown):
    """Approve the clear ones, queue the rest. Entries already decided are never touched."""
    entries, queue = dict(saved), []
    for key, name in keys:
        if key in entries:
            continue
        ranked = rank(key, name, catalog)[:shown]
        expected = expected_equipment(tokens(key.replace("_", " ")) | tokens(name))
        verdict = decide(ranked, expected, threshold, margin)
        if verdict["auto"]:
            entries[key] = auto_entry(ranked[0][1], verdict["reason"])
        else:
            queue.append((key, name, ranked))
    return entries, queue


def apply_decision(
    entries: dict, key: str, ranked: list, pick: str, note: str, catalog: list | None = None
) -> dict:
    pick = pick.strip().lower()
    if pick.startswith("id:"):
        found = [c for c in catalog or [] if str(c["id"]) == pick[3:]]
        if not found:
            raise ValueError(f"{pick[3:]!r} is not an id in the catalog")
        entry = manual_entry(found[0], note)
    elif pick == "n":
        entry = pending_entry(note)
    elif pick.isdigit() and 1 <= int(pick) <= len(ranked):
        entry = manual_entry(ranked[int(pick) - 1][1], note)
    else:
        raise ValueError(f"pick must be a number from 1 to {len(ranked)} or n, got {pick!r}")
    return {**entries, key: entry}


def review(key: str, name: str, ranked: list[tuple[float, dict]], siblings: dict) -> dict | None:
    print(render_card(key, name, ranked, siblings))
    while True:
        answer = input("Pick a number, n = none fits, s = skip for later, q = save and quit: ")
        answer = answer.strip().lower()
        if answer == "q":
            raise SystemExit(0)
        if answer == "s":
            return None
        if answer == "n":
            return pending_entry(input("Why does none fit? "))
        if answer.isdigit() and 1 <= int(answer) <= len(ranked):
            cand = ranked[int(answer) - 1][1]
            while True:
                try:
                    return manual_entry(cand, input("Note (why this one): "))
                except ValueError as error:
                    print(error)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--keys", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--catalog", type=Path, required=True)
    parser.add_argument("--threshold", type=float, default=0.9)
    parser.add_argument("--margin", type=float, default=0.1)
    parser.add_argument("--shown", type=int, default=5, help="candidates shown per exercise")
    parser.add_argument("--next", action="store_true", help="print the next card and exit")
    parser.add_argument("--decide", metavar="KEY", help="record a decision for KEY and exit")
    parser.add_argument("--pick", help="with --decide: a candidate number, or n if none fits")
    parser.add_argument("--note", default="", help="with --decide: why")
    args = parser.parse_args(argv)

    catalog = fetch_catalog(args.catalog)
    siblings: dict = {}
    for cand in catalog:
        siblings.setdefault(cand["variation_group"], []).append(cand["en_name"])
    saved = json.loads(args.out.read_text()) if args.out.exists() else {}
    keys = read_regular_keys(args.keys.read_text(encoding="utf-8"))
    entries, queue = plan(keys, saved, catalog, args.threshold, args.margin, args.shown)
    for key in entries.keys() - saved.keys():
        print(f"auto  {key} -> {entries[key]['name']} (id {entries[key]['wger_id']})")
    save(args.out, entries)

    if args.decide:
        waiting = {key: ranked for key, _, ranked in queue}
        if args.decide not in waiting:
            print(f"{args.decide} is not waiting for a decision", file=sys.stderr)
            return 1
        try:
            entries = apply_decision(
                entries, args.decide, waiting[args.decide], args.pick or "", args.note, catalog
            )
        except ValueError as error:
            print(error, file=sys.stderr)
            return 1
        save(args.out, entries)
        print(f"saved {args.decide}: {entries[args.decide]['status']}, {len(queue) - 1} left")
        return 0
    if args.next:
        if not queue:
            print("Every exercise has a decision.")
            return 0
        key, name, ranked = queue[0]
        print(f"{len(queue)} waiting. Next:\n")
        print(render_card(key, name, ranked, siblings))
        return 0

    print(f"\n{len(queue)} exercises need a person. Progress is saved after each one.\n")
    for key, name, ranked in queue:
        entry = review(key, name, ranked, siblings)
        if entry:
            entries[key] = entry
            save(args.out, entries)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
