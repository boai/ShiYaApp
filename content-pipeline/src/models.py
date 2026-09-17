# src/models.py
from dataclasses import dataclass, field

@dataclass
class Line:
    chars: list[str]
    pinyin: list[str] = field(default_factory=list)
    punct: str = ""

@dataclass
class Keyword:
    word: str
    explain: str

@dataclass
class Poem:
    id: str
    title: str
    author: str
    dynasty: str
    category: str
    difficulty: str
    lines: list[Line]
    translation: str
    background: str
    keywords: list[Keyword] = field(default_factory=list)
    audio: str = ""
    timing: str = ""
    bibei: bool = False

DIFFICULTIES = {"qimeng", "jinjie", "bibei"}

def parse_poem_yaml(text: str) -> Poem:
    import yaml
    d = yaml.safe_load(text)
    missing = [k for k in ("id", "title", "author", "dynasty", "category",
                           "difficulty", "lines", "translation", "background")
               if k not in d]
    if missing:
        raise ValueError(f"缺少字段: {missing}")
    if d["difficulty"] not in DIFFICULTIES:
        raise ValueError(f"难度必须是 {DIFFICULTIES} 之一")
    lines = [Line(chars=list(ln["chars"]), punct=ln.get("punct", ""))
             for ln in d["lines"]]
    kws = [Keyword(**kw) for kw in d.get("keywords", [])]
    return Poem(id=d["id"], title=d["title"], author=d["author"],
                dynasty=d["dynasty"], category=d["category"],
                difficulty=d["difficulty"], lines=lines,
                translation=d["translation"], background=d["background"],
                keywords=kws,
                audio=f"audio/{d['id']}.m4a", timing=f"timing/{d['id']}.json",
                bibei=d.get("bibei", False))
