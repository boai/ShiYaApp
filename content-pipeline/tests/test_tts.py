from src.tts import align_chars

def test_align_chars_strips_punctuation():
    # edge-tts WordBoundary 只给文字字符,不含标点
    boundaries = [  # (text, offset_ms, duration_ms)
        ("床", 100, 400), ("前", 500, 400), ("明", 900, 400),
        ("月", 1300, 400), ("光", 1700, 400),
    ]
    chars = ["床", "前", "明", "月", "光"]
    result = align_chars(boundaries, chars)
    assert len(result) == 5
    assert result[0] == {"line": 0, "index": 0, "startMs": 100, "endMs": 500}

def test_align_chars_multi_line_offsets():
    boundaries = [("床", 0, 300), ("前", 300, 300), ("明", 600, 300),
                  ("月", 900, 300), ("光", 1200, 300), ("疑", 1600, 300)]
    lines = [["床", "前", "明", "月", "光"], ["疑"]]
    result = align_chars(boundaries, lines)
    assert result[5] == {"line": 1, "index": 0, "startMs": 1600, "endMs": 1900}

def test_align_chars_mismatch_raises():
    import pytest
    with pytest.raises(ValueError):
        align_chars([("床", 0, 300)], ["床", "前"])
