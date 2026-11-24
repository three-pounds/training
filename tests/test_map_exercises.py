import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "map_exercises", Path(__file__).parents[1] / "scripts" / "map_exercises.py"
)
me = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(me)


def candidate(id, en, es="", equipment=(), muscles=(), description_en="", variation=None):
    return {
        "id": id,
        "en_name": en,
        "es_name": es,
        "equipment": list(equipment),
        "muscles": list(muscles),
        "muscles_secondary": [],
        "descriptions": {"en": description_en, "es": ""},
        "variation_group": variation,
    }


def test_tokens_ignore_accents_punctuation_and_plurals_and_expand_abbreviations():
    assert me.tokens("Elevación Lateral en Polea") == {"elevacion", "lateral", "en", "polea"}
    assert me.tokens("Seated DB Shoulder-Press") == {"seated", "dumbbell", "shoulder", "press"}
    assert me.tokens("Cable Lateral Raises") == {"cable", "lateral", "raise"}


def test_name_score_is_the_overlap_of_the_two_names():
    assert me.dice({"a", "b"}, {"a", "b"}) == 1
    assert me.dice({"a", "b"}, {"c"}) == 0
    assert me.dice({"a", "b", "c"}, {"a", "b", "c", "d"}) == 6 / 7


def test_expected_equipment_comes_from_the_strong_words_of_the_key_and_name():
    assert me.expected_equipment({"seated", "dumbbell", "press"}) == {"dumbbell"}
    assert me.expected_equipment({"leg", "extension"}) == set()


def test_an_equipment_conflict_is_a_different_strong_equipment_not_a_missing_one():
    barbell = candidate(1, "Press", equipment=["Barbell"])
    cable = candidate(2, "Press", equipment=["Cable machine"])
    nothing = candidate(3, "Press", equipment=[])
    assert me.equipment_conflict({"dumbbell"}, barbell)
    assert not me.equipment_conflict({"cable"}, cable)
    assert me.equipment_conflict({"dumbbell"}, nothing)
    assert not me.equipment_conflict(set(), barbell)


def test_ranking_scores_the_key_and_the_names_and_orders_best_first():
    cands = [
        candidate(1, "Bench Press", equipment=["Barbell"]),
        candidate(2, "Barbell Bench Press", equipment=["Barbell"]),
    ]
    ranked = me.rank("barbell_bench_press", "Press de Banca con Barra", cands)
    assert [c["id"] for _, c in ranked] == [2, 1]
    assert ranked[0][0] == 1


def good(score=0.95, margin_to=0.5):
    return [(score, candidate(1, "x")), (margin_to, candidate(2, "y"))]


def test_a_clear_winner_above_the_threshold_without_conflict_is_approved_automatically():
    verdict = me.decide(good(), expected=set(), threshold=0.9, margin=0.1)
    assert verdict["auto"] is True
    assert verdict["reason"].startswith("score 0.95")


def test_below_the_threshold_it_goes_to_manual_review():
    assert me.decide(good(score=0.8), set(), 0.9, 0.1)["auto"] is False


def test_a_close_second_candidate_goes_to_manual_review():
    assert me.decide(good(score=0.95, margin_to=0.9), set(), 0.9, 0.1)["auto"] is False


def test_an_equipment_conflict_goes_to_manual_even_with_a_perfect_score():
    ranked = [(1.0, candidate(1, "x", equipment=["Barbell"]))]
    assert me.decide(ranked, {"dumbbell"}, 0.9, 0.1)["auto"] is False


def test_the_lateral_raise_that_looked_alike_is_not_decided_by_the_machine():
    cands = [
        candidate(1882, "High-Cable Lateral Raise", equipment=["Cable machine"]),
        candidate(1378, "Cable Lateral Raises (Single Arm)", equipment=["Cable machine"]),
        candidate(1730, "Side Lateral Raise (Cable)", equipment=["Cable machine"]),
    ]
    ranked = me.rank("cable_lateral_raise", "Elevación Lateral en Polea", cands)
    verdict = me.decide(ranked, me.expected_equipment(me.tokens("cable_lateral_raise")), 0.9, 0.1)
    assert verdict["auto"] is False


def test_the_review_card_shows_every_field_in_full_without_truncating():
    long = "Step one. " * 80
    cand = candidate(
        7,
        "Seated Leg Curl",
        es="Curl de pierna sentado",
        equipment=["Machine"],
        muscles=["Hamstrings"],
        description_en=long,
        variation="group-1",
    )
    siblings = {"group-1": ["Lying Leg Curl"]}
    card = me.render_card("seated_leg_curl", "Seated Leg Curl (heavy)", [(0.8, cand)], siblings)
    assert long.strip() in card
    assert "Curl de pierna sentado" in card
    assert "Machine" in card and "Hamstrings" in card
    assert "Lying Leg Curl" in card
    assert "seated_leg_curl" in card


def test_a_catalog_entry_is_flattened_and_its_html_removed():
    raw = {
        "id": 5,
        "equipment": [{"id": 1, "name": "Dumbbell"}],
        "muscles": [{"name": "Biceps brachii"}],
        "muscles_secondary": [{"name": "Brachialis"}],
        "variation_group": "g",
        "translations": [
            {"language": 2, "name": "Curl", "description": "<p>Lift <b>up</b>.</p>"},
            {"language": 4, "name": "Curl de bíceps", "description": "<p>Sube.</p>"},
        ],
    }
    out = me.to_candidate(raw)
    assert out["id"] == 5
    assert out["en_name"] == "Curl" and out["es_name"] == "Curl de bíceps"
    assert out["equipment"] == ["Dumbbell"]
    assert out["descriptions"]["en"] == "Lift up."
    assert out["variation_group"] == "g"


def test_a_catalog_entry_without_an_english_name_is_dropped():
    raw = {"id": 6, "equipment": [], "muscles": [], "translations": [{"language": 4, "name": "x"}]}
    assert me.to_candidate(raw) is None


def test_keys_are_read_only_from_the_regular_section():
    text = (
        "# header\n# [regular] map normally\nlat_pulldown | Lat Pulldown (wide neutral)\n"
        "rope_pushdown | Rope Pushdown\n# [quarantine] hold\nweighted_dips | Weighted Dips\n"
        "# [not weights] skip\nswim | Natación\n"
    )
    assert me.read_regular_keys(text) == [
        ("lat_pulldown", "Lat Pulldown (wide neutral)"),
        ("rope_pushdown", "Rope Pushdown"),
    ]


def test_an_automatic_entry_records_where_it_came_from_and_why():
    entry = me.auto_entry(candidate(9, "Rope Pushdown"), "score 1.00, margin 0.50, no conflict")
    assert entry == {
        "wger_id": 9,
        "name": "Rope Pushdown",
        "status": "auto",
        "confirmed_by": "auto-rule",
        "sources": ["wger:9"],
        "note": "score 1.00, margin 0.50, no conflict",
    }


def test_a_manual_entry_requires_a_note():
    entry = me.manual_entry(candidate(9, "Rope Pushdown"), "same movement, rope attachment")
    assert entry["status"] == "approved" and entry["confirmed_by"] == "human"
    assert entry["note"] == "same movement, rope attachment"
    try:
        me.manual_entry(candidate(9, "Rope Pushdown"), "  ")
    except ValueError:
        return
    raise AssertionError("a blank note must be refused")


def small_catalog():
    return [
        candidate(1, "Rope Pushdown", equipment=["Cable machine"]),
        candidate(2, "Cable Lateral Raise", equipment=["Cable machine"]),
        candidate(3, "Lateral Raise (Cable)", equipment=["Cable machine"]),
    ]


def test_a_plan_approves_the_clear_ones_and_queues_the_rest_without_touching_saved_entries():
    keys = [("rope_pushdown", "Rope Pushdown"), ("cable_lateral_raise", "Elevación Lateral")]
    saved = {"already": {"status": "approved"}}
    entries, queue = me.plan(keys + [("already", "x")], saved, small_catalog(), 0.9, 0.1, 5)
    assert entries["rope_pushdown"]["status"] == "auto"
    assert entries["already"] == {"status": "approved"}
    assert [key for key, _, _ in queue] == ["cable_lateral_raise"]
    assert saved == {"already": {"status": "approved"}}


def test_a_decision_by_number_records_the_note_and_leaves_other_entries_alone():
    ranked = [(0.8, candidate(5, "First")), (0.7, candidate(6, "Second"))]
    out = me.apply_decision({"keep": 1}, "k", ranked, "2", "same movement")
    assert out["k"]["wger_id"] == 6 and out["k"]["note"] == "same movement"
    assert out["keep"] == 1


def test_a_decision_of_none_leaves_the_exercise_pending_with_its_reason():
    out = me.apply_decision({}, "k", [(0.8, candidate(5, "First"))], "n", "nothing fits")
    assert out["k"]["status"] == "pending" and out["k"]["note"] == "nothing fits"


def test_a_decision_outside_the_options_is_refused_and_saves_nothing():
    ranked = [(0.8, candidate(5, "First"))]
    for pick in ("0", "2", "x"):
        try:
            me.apply_decision({}, "k", ranked, pick, "note")
        except ValueError:
            continue
        raise AssertionError(f"pick {pick!r} must be refused")


def test_a_decision_can_name_any_catalog_exercise_by_id():
    catalog = [candidate(380, "Leverage Machine Iso Row"), candidate(5, "First")]
    ranked = [(0.8, candidate(5, "First"))]
    out = me.apply_decision({}, "k", ranked, "id:380", "plate-loaded iso row", catalog)
    assert out["k"]["wger_id"] == 380 and out["k"]["name"] == "Leverage Machine Iso Row"
    assert out["k"]["sources"] == ["wger:380"]


def test_an_id_that_is_not_in_the_catalog_is_refused():
    for pick in ("id:999", "id:abc"):
        try:
            me.apply_decision({}, "k", [], pick, "note", [candidate(5, "First")])
        except ValueError:
            continue
        raise AssertionError(f"{pick!r} must be refused")
