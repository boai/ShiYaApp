# src/validate.py
import re

TONE_RE = re.compile(r"[āáǎàēéěèīíǐìōóǒòūúǔùǖǘǚǜ]")

def validate_poem(p: "Poem") -> list[str]:
    errs = []
    if not p.audio:
        errs.append(f"{p.id}: audio 路径为空")
    if not p.timing:
        errs.append(f"{p.id}: timing 路径为空")
    if not p.translation.strip():
        errs.append(f"{p.id}: 译文为空")
    if not p.background.strip():
        errs.append(f"{p.id}: 背景故事为空")
    for i, line in enumerate(p.lines):
        if len(line.pinyin) != len(line.chars):
            errs.append(f"{p.id}: 第 {i+1} 行拼音数 {len(line.pinyin)} != 字数 {len(line.chars)}")
            continue
        for j, py in enumerate(line.pinyin):
            if not TONE_RE.search(py):
                errs.append(f"{p.id}: 第 {i+1} 行第 {j+1} 字拼音 {py!r} 缺少声调")
    return errs
