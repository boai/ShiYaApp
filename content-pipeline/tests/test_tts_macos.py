from src.tts_macos import estimate_timing


def test_estimate_timing_counts_and_monotonic():
    chars = estimate_timing(10000, [list("床前明月光"), list("疑是地上霜")])
    assert len(chars) == 10
    assert chars[0]["startMs"] == 0
    assert chars[-1]["endMs"] == 10000
    starts = [c["startMs"] for c in chars]
    assert all(starts[i] < starts[i + 1] for i in range(len(starts) - 1))


def test_estimate_timing_line_end_pause_absorbed():
    chars = estimate_timing(1000, [["床", "前"]], line_pause_units=1.0)
    # 单位 = 1000/3 ≈ 333;末字 end 吸收行尾停顿,必然到 1000 且长于前字
    assert chars[-1]["endMs"] == 1000
    assert (chars[-1]["endMs"] - chars[-1]["startMs"]) > \
           (chars[0]["endMs"] - chars[0]["startMs"])


def test_estimate_timing_coordinates():
    chars = estimate_timing(6000, [["床"], ["前", "明"]])
    assert (chars[-1]["line"], chars[-1]["index"]) == (1, 1)
