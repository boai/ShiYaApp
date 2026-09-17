# tests/test_build_index.py
from src.build import build_index
from src.models import Poem, Line

def test_build_index_groups():
    p1 = Poem(id="a", title="静夜思", author="李白", dynasty="唐", category="唐诗",
              difficulty="qimeng", lines=[Line(chars=list("床"), pinyin=["chuáng"])],
              translation="t", background="b", audio="audio/a.mp3", timing="timing/a.json")
    p2 = Poem(id="b", title="咏鹅", author="骆宾王", dynasty="唐", category="唐诗",
              difficulty="qimeng", lines=[Line(chars=list("鹅"), pinyin=["é"])],
              translation="t", background="b", audio="audio/b.mp3", timing="timing/b.json")
    idx = build_index([p1, p2])
    assert idx["byDifficulty"]["qimeng"] == ["a", "b"]
    assert idx["byPoet"]["李白"] == ["a"]
    assert idx["byInitial"]["j"][0]["id"] == "a"   # 静夜思 jìng → j
    assert idx["byInitial"]["y"][0]["id"] == "b"   # 咏鹅 yǒng → y

def test_build_index_deterministic_order():
    from src.models import Line
    ps = [Poem(id=str(i), title=f"诗{i}", author="李", dynasty="唐", category="唐诗",
               difficulty="qimeng", lines=[Line(chars=["一"], pinyin=["yī"])],
               translation="t", background="b", audio="a", timing="t")
          for i in range(5)]
    idx = build_index(ps)
    assert idx["byPoet"]["李"] == ["0", "1", "2", "3", "4"]

def test_build_index_bibei_dual_group():
    p = Poem(id="c", title="测", author="李", dynasty="唐", category="唐诗",
             difficulty="qimeng", bibei=True, lines=[Line(chars=["一"], pinyin=["yī"])],
             translation="t", background="b", audio="audio/c.m4a", timing="timing/c.json")
    idx = build_index([p])
    assert "c" in idx["byDifficulty"]["qimeng"]
    assert idx["byDifficulty"]["bibei"] == ["c"]


def test_build_index_bibei_no_duplicate():
    p = Poem(id="d", title="测", author="李", dynasty="唐", category="唐诗",
             difficulty="bibei", bibei=True, lines=[Line(chars=["一"], pinyin=["yī"])],
             translation="t", background="b", audio="audio/d.m4a", timing="timing/d.json")
    idx = build_index([p])
    assert idx["byDifficulty"]["bibei"] == ["d"]
