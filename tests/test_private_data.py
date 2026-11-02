import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "check_private_data", Path(__file__).parents[1] / "scripts" / "check_private_data.py"
)
cpd = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cpd)


def test_finds_case_insensitive_whole_word_hits():
    texts = {"a.md": "line one\nHello Alicia here\n", "b.md": "nothing"}
    hits = cpd.find_hits(texts, ["alicia"])
    assert hits == [("a.md", 2, "alicia")]


def test_does_not_match_inside_other_words():
    assert cpd.find_hits({"a.md": "malicia"}, ["alicia"]) == []


def test_load_patterns_reads_env_then_file(tmp_path, monkeypatch):
    monkeypatch.setenv("PRIVATE_DENYLIST", "Foo\n\n bar \n# comment\n")
    assert cpd.load_patterns(tmp_path / "missing") == ["foo", "bar"]
    monkeypatch.delenv("PRIVATE_DENYLIST")
    f = tmp_path / "list"
    f.write_text("baz\n")
    assert cpd.load_patterns(f) == ["baz"]


def test_load_patterns_empty_when_nothing_configured(tmp_path, monkeypatch):
    monkeypatch.delenv("PRIVATE_DENYLIST", raising=False)
    assert cpd.load_patterns(tmp_path / "missing") == []
