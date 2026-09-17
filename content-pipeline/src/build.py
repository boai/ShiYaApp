# src/build.py
from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from pypinyin import pinyin as _py, Style
from src.models import Poem, parse_poem_yaml
from src.pinyin import fill_pinyin, load_overrides
from src.validate import validate_poem
from src.tts_macos import synthesize_sync

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "data" / "source"
OUT_DIR = ROOT / "output"

def build_index(poems: list[Poem]) -> dict:
    by_diff: dict[str, list[str]] = {"qimeng": [], "jinjie": [], "bibei": []}
    by_poet: dict[str, list[str]] = {}
    by_initial: dict[str, list[dict]] = {}
    meta = {}
    for p in poems:
        by_diff[p.difficulty].append(p.id)
        if p.bibei and p.difficulty != "bibei":
            by_diff["bibei"].append(p.id)
        by_poet.setdefault(p.author, []).append(p.id)
        ini = _py(p.title[0], style=Style.NORMAL)[0][0][0] if p.title else "?"
        by_initial.setdefault(ini, []).append(
            {"id": p.id, "title": p.title, "author": p.author, "difficulty": p.difficulty})
        meta[p.id] = {"title": p.title, "author": p.author, "dynasty": p.dynasty,
                      "category": p.category, "difficulty": p.difficulty}
    return {"byDifficulty": by_diff, "byPoet": by_poet, "byInitial": by_initial, "poems": meta}

def run_pipeline(source: str | None = None) -> tuple[list[Poem], list[str]]:
    """执行完整管线:解析 → 拼音 → 校验。音频生成单独跑 generate_audio(耗时)。"""
    overrides = load_overrides(str(ROOT / "data" / "overrides.csv"))
    poems, errs = [], []
    files = sorted(Path(source or SOURCE_DIR).glob("*.yaml"))
    for f in files:
        p = parse_poem_yaml(f.read_text(encoding="utf-8"))
        fill_pinyin(p.lines, title=p.title, overrides=overrides)
        poems.append(p)
        errs += validate_poem(p)
    return poems, errs

def generate_audio(poems: list[Poem], max_n: int | None = None) -> None:
    (OUT_DIR / "audio").mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "timing").mkdir(parents=True, exist_ok=True)
    for p in poems[:max_n]:
        text = "".join("".join(l.chars) + (l.punct or "") for l in p.lines)
        synthesize_sync(text, str(OUT_DIR / p.audio), str(OUT_DIR / p.timing),
                        [l.chars for l in p.lines])

def write_outputs(poems: list[Poem]) -> None:
    (OUT_DIR / "poems").mkdir(parents=True, exist_ok=True)
    for p in poems:
        (OUT_DIR / "poems" / f"{p.id}.json").write_text(
            json.dumps(asdict(p), ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "index.json").write_text(
        json.dumps(build_index(poems), ensure_ascii=False, indent=2), encoding="utf-8")
