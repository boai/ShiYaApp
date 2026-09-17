# tests/test_validate.py
from src.models import Poem, Line
from src.validate import validate_poem

def make_poem(**kw):
    base = dict(id="x", title="测", author="测", dynasty="唐", category="唐诗",
                difficulty="qimeng",
                lines=[Line(chars=list("床前明月光"), pinyin=["chuáng","qián","míng","yuè","guāng"], punct=",")],
                audio="audio/x.mp3", timing="timing/x.json",
                translation="t", background="b")
    base.update(kw)
    return Poem(**base)

def test_valid_poem_passes():
    assert validate_poem(make_poem()) == []

def test_pinyin_chars_count_mismatch():
    p = make_poem(lines=[Line(chars=list("床前"), pinyin=["chuáng"])])
    errs = validate_poem(p)
    assert any("拼音" in e for e in errs)

def test_pinyin_has_no_tone_mark():
    p = make_poem(lines=[Line(chars=list("床"), pinyin=["chuang"])])
    assert any("声调" in e for e in validate_poem(p))

def test_audio_and_timing_paths_set():
    p = make_poem(audio="", timing="")
    assert any("audio" in e for e in validate_poem(p))
