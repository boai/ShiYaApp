# src/pinyin.py
from __future__ import annotations

import csv
from pypinyin import pinyin as _py, Style
from src.models import Line

def load_overrides(path: str) -> dict[tuple[str, str], str]:
    out = {}
    with open(path, encoding="utf-8") as f:
        for row in csv.reader(f):
            if not row or row[0].startswith("#"):
                continue
            title, char, reading = row[0].strip(), row[1].strip(), row[2].strip()
            out[(title, char)] = reading
    return out

def fill_pinyin(lines: list[Line], title: str = "",
                overrides: dict[tuple[str, str], str] | None = None) -> None:
    overrides = overrides or {}
    for line in lines:
        text = "".join(line.chars)
        py = [_py(ch, style=Style.TONE)[0][0] for ch in text]
        for i, ch in enumerate(line.chars):
            if (title, ch) in overrides:
                py[i] = overrides[(title, ch)]
        line.pinyin = py
