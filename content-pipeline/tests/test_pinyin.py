from src.models import Line
from src.pinyin import fill_pinyin, load_overrides

def test_fill_pinyin_basic():
    line = Line(chars=list("床前明月光"))
    fill_pinyin([line])
    assert line.pinyin == ["chuáng", "qián", "míng", "yuè", "guāng"]

def test_override_wins_for_polyphone():
    line = Line(chars=list("大山"))
    fill_pinyin([line], title="大山", overrides={("大山", "大"): "dài"})
    assert line.pinyin[0] == "dài"

def test_load_overrides_from_csv(tmp_path):
    p = tmp_path / "o.csv"
    p.write_text("静夜思,疑,yí\n", encoding="utf-8")
    o = load_overrides(str(p))
    assert o[("静夜思", "疑")] == "yí"
