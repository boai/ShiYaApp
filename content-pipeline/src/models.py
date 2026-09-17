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

def parse_poem_dict(d: dict) -> Poem:
    """把单个源文档(dict)构造为 Poem。"""
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

def parse_poem_yaml(text: str) -> Poem:
    """解析单文档 YAML 为一首诗。"""
    import yaml
    return parse_poem_dict(yaml.safe_load(text))

def parse_poems_yaml(text: str) -> list[Poem]:
    """解析多文档 YAML(`---` 分隔,批次源数据格式)为多首诗。"""
    import yaml
    return [parse_poem_dict(d) for d in yaml.safe_load_all(text)]
