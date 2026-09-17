# 「诗芽」内容管线实现计划

> **面向 AI 代理的工作者:** 必需子技能:使用 superpowers:subagent-driven-development(推荐)或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框(`- [ ]`)语法来跟踪进度。

**目标:** 构建 content-pipeline:把人工整理的诗词源数据加工成应用内置资产(poems JSON、逐字拼音、朗读 mp3、逐字时间轴),全部通过校验。

**架构:** Python 脚本管线:源数据(YAML)→ 拼音生成(pypinyin + 多音字覆盖)→ 音频与时间轴生成(edge-tts WordBoundary)→ 校验器 → 输出目录。产物由 Android 应用打包进 assets。

**技术栈:** Python 3 + pypinyin + edge-tts + PyYAML + pytest

---

## 风险门(执行任务 1 前必须确认)

1. `python3` 版本 ≥ 3.9 可用,`pip` 可用(必要时用清华镜像 `https://pypi.tuna.tsinghua.edu.cn/simple`)
2. **edge-tts 网络可达性:** 运行 `curl -sS -o /dev/null -w "%{http_code}" --connect-timeout 8 https://speech.platform.bing.com` 确认可访问(该域名在国内通常可达)。若不可达:暂停任务 3,向用户报告,改用系统 TTS 兜底方案(仅拼音+讲解,无逐字时间轴,KTV 按句高亮降级)
3. 输出产物写入 `content-pipeline/output/`(已在 .gitignore 中,不入库;应用构建时复制到 assets)

## 文件结构

- `content-pipeline/src/models.py` — Poem/Line/Keyword 数据类与解析
- `content-pipeline/src/pinyin.py` — 逐字拼音生成与多音字覆盖
- `content-pipeline/src/tts.py` — edge-tts 音频生成 + 逐字时间轴提取
- `content-pipeline/src/validate.py` — 数据完整性校验器
- `content-pipeline/src/build.py` — 编排管线:源 → 输出
- `content-pipeline/data/source/*.yaml` — 诗词源数据(人工整理,入库)
- `content-pipeline/data/overrides.csv` — 多音字读音覆盖表(入库)
- `content-pipeline/tests/*.py` — pytest 测试
- `content-pipeline/output/` — 产物(不入库)

---

### 任务 1:工程脚手架与依赖

**文件:**
- 创建:`content-pipeline/requirements.txt`
- 创建:`content-pipeline/README.md`

- [ ] **步骤 1:确认 Python 与 pip**

运行:`python3 --version && python3 -m pip --version`
预期:Python ≥ 3.9。若 pip 缺失:运行 `python3 -m ensurepip`

- [ ] **步骤 2:创建虚拟环境并安装依赖**

```bash
cd content-pipeline
python3 -m venv .venv
.venv/bin/pip install -i https://pypi.tuna.tsinghua.edu.cn/simple pypinyin edge-tts pyyaml pytest
```

`requirements.txt` 内容:

```
pypinyin>=0.51
edge-tts>=6.1
pyyaml>=6.0
pytest>=8.0
```

- [ ] **步骤 3:edge-tts 可达性检查(风险门)**

运行:

```bash
curl -sS -o /dev/null -w "%{http_code}\n" --connect-timeout 8 https://speech.platform.bing.com
```

预期:返回 200/403 均可(表示可达);连接超时则按风险门第 2 条处理,停止本计划并向用户报告。

- [ ] **步骤 4:冒烟验证 pypinyin 与 edge-tts 可用**

```bash
.venv/bin/python -c "from pypinyin import pinyin, Style; print(pinyin('床前明月光', style=Style.TONE))"
.venv/bin/python -c "import edge_tts; print(edge_tts.__version__)"
```

预期:第一行输出 `[['chuáng'], ['qián'], ['míng'], ['yuè'], ['guāng']]`(含声调);第二行输出版本号。

- [ ] **步骤 5:Commit**

```bash
git add content-pipeline/requirements.txt content-pipeline/README.md
git commit -m "chore(内容管线): 搭建 Python 工程骨架与依赖清单"
```

`README.md` 简述:管线用途、四个模块职责、运行方式(`.venv/bin/python -m src.build`)、产物目录约定。

---

### 任务 2:数据模型与解析器

**文件:**
- 创建:`content-pipeline/src/__init__.py`
- 创建:`content-pipeline/src/models.py`
- 测试:`content-pipeline/tests/test_models.py`

- [ ] **步骤 1:编写失败的测试**

```python
# tests/test_models.py
import yaml
from src.models import Poem, Line, Keyword, parse_poem_yaml

SAMPLE = """
id: tang-libai-jingyesi
title: 静夜思
author: 李白
dynasty: 唐
category: 唐诗
difficulty: qimeng
lines:
  - chars: [床, 前, 明, 月, 光]
    punct: ","
translation: 明亮的月光洒在床前。
background: 李白离开家乡后写下的思乡诗。
keywords:
  - word: 疑
    explain: 好像
"""

def test_parse_poem_yaml_basic():
    p = parse_poem_yaml(SAMPLE)
    assert p.id == "tang-libai-jingyesi"
    assert p.title == "静夜思"
    assert p.lines[0].chars == ["床", "前", "明", "月", "光"]
    assert p.lines[0].punct == ","
    assert p.keywords[0].word == "疑"

def test_parse_poem_yaml_pinyin_filled_later():
    p = parse_poem_yaml(SAMPLE)
    assert p.lines[0].pinyin == []  # 拼音由 pinyin 模块填充

def test_parse_missing_difficulty_raises():
    bad = SAMPLE.replace("difficulty: qimeng", "")
    import pytest
    with pytest.raises(ValueError):
        parse_poem_yaml(bad)
```

- [ ] **步骤 2:运行测试验证失败**

运行:`content-pipeline/.venv/bin/pytest tests/test_models.py -q`
预期:FAIL,报错 `ModuleNotFoundError: No module named 'src.models'`

- [ ] **步骤 3:编写实现**

```python
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
                audio=f"audio/{d['id']}.mp3", timing=f"timing/{d['id']}.json")
```

- [ ] **步骤 4:运行测试验证通过**

运行:`content-pipeline/.venv/bin/pytest tests/test_models.py -q`
预期:PASS(3 个测试全过)

- [ ] **步骤 5:Commit**

```bash
git add content-pipeline/src/ content-pipeline/tests/
git commit -m "feat(内容管线): 添加诗词数据模型与 YAML 解析器"
```

---

### 任务 3:拼音生成与多音字覆盖

**文件:**
- 创建:`content-pipeline/src/pinyin.py`
- 创建:`content-pipeline/data/overrides.csv`(首批覆盖见步骤 3)
- 测试:`content-pipeline/tests/test_pinyin.py`

- [ ] **步骤 1:编写失败的测试**

```python
# tests/test_pinyin.py
from src.models import Line
from src.pinyin import fill_pinyin, load_overrides

def test_fill_pinyin_basic():
    line = Line(chars=list("床前明月光"))
    fill_pinyin([line])
    assert line.pinyin == ["chuáng", "qián", "míng", "yuè", "guāng"]

def test_override_wins_for_polyphone():
    line = Line(chars=list("一行白鹭上青天"))
    fill_pinyin([line], overrides={("一行白鹭上青天", "行"): "háng"})
    assert line.pinyin[1] == "háng"

def test_load_overrides_from_csv(tmp_path):
    p = tmp_path / "o.csv"
    p.write_text("静夜思,疑,yí\n", encoding="utf-8")
    o = load_overrides(str(p))
    assert o[("静夜思", "疑")] == "yí"
```

- [ ] **步骤 2:运行测试验证失败**

运行:`content-pipeline/.venv/bin/pytest tests/test_pinyin.py -q`
预期:FAIL,报错 `ModuleNotFoundError: No module named 'src.pinyin'`

- [ ] **步骤 3:编写实现**

```python
# src/pinyin.py
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
```

`data/overrides.csv` 首批内容(后续每批内容任务增补):

```csv
# title,char,reading(按篇目逐字覆盖多音字)
静夜思,疑,yí
古朗月行,行,xíng
```

- [ ] **步骤 4:运行测试验证通过**

运行:`content-pipeline/.venv/bin/pytest tests/test_pinyin.py -q`
预期:PASS(3 个测试全过)

- [ ] **步骤 5:Commit**

```bash
git add content-pipeline/src/pinyin.py content-pipeline/data/overrides.csv content-pipeline/tests/test_pinyin.py
git commit -m "feat(内容管线): 添加逐字拼音生成与多音字覆盖机制"
```

---

### 任务 4:edge-tts 音频与逐字时间轴

**文件:**
- 创建:`content-pipeline/src/tts.py`
- 测试:`content-pipeline/tests/test_tts.py`(时间轴映射逻辑,不依赖网络)

- [ ] **步骤 1:编写失败的测试(离线可测的映射逻辑)**

```python
# tests/test_tts.py
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
```

- [ ] **步骤 2:运行测试验证失败**

运行:`content-pipeline/.venv/bin/pytest tests/test_tts.py -q`
预期:FAIL,报错 `ModuleNotFoundError: No module named 'src.tts'`

- [ ] **步骤 3:编写实现**

```python
# src/tts.py
import asyncio
import json
import edge_tts

VOICE = "zh-CN-XiaoxiaoNeural"   # 晓晓(女声,温柔清晰,适合儿童)
RATE = "-20%"                     # 慢速朗读

def align_chars(boundaries, lines):
    """把 edge-tts 逐字边界映射到 (line, index) 坐标。

    boundaries: [(text, offset_ms, duration_ms), ...](仅文字,无标点)
    lines: [[char, ...], ...]
    """
    flat = [ch for line in lines for ch in line]
    if len(boundaries) != len(flat):
        raise ValueError(f"边界数 {len(boundaries)} 与字数 {len(flat)} 不一致")
    out, pos = [], 0
    for li, line in enumerate(lines):
        for ci in range(len(line)):
            text, off, dur = boundaries[pos]
            if text != flat[pos]:
                raise ValueError(f"第 {pos} 字不匹配: TTS={text!r} 数据={flat[pos]!r}")
            out.append({"line": li, "index": ci, "startMs": off, "endMs": off + dur})
            pos += 1
    return out

async def synthesize(text: str, out_mp3: str, out_timing: str,
                     lines: list[list[str]]) -> dict:
    """生成 mp3 与逐字时间轴,返回 {durationMs, chars}。"""
    comm = edge_tts.Communicate(text, voice=VOICE, rate=RATE)
    boundaries = []
    with open(out_mp3, "wb") as f:
        async for chunk in comm.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "WordBoundary":
                boundaries.append((chunk["text"], chunk["offset"], chunk["duration"]))
    chars = align_chars(boundaries, lines)
    duration_ms = chars[-1]["endMs"] + 800  # 末尾留白
    payload = {"audioDurationMs": duration_ms, "chars": chars}
    with open(out_timing, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return payload

def synthesize_sync(text, out_mp3, out_timing, lines) -> dict:
    return asyncio.run(synthesize(text, out_mp3, out_timing, lines))
```

- [ ] **步骤 4:运行测试验证通过**

运行:`content-pipeline/.venv/bin/pytest tests/test_tts.py -q`
预期:PASS(3 个测试全过)

- [ ] **步骤 5:联网冒烟:为一首真实诗词生成音频**

运行:

```bash
cd content-pipeline
.venv/bin/python -c "
from src.tts import synthesize_sync
payload = synthesize_sync('床前明月光,疑是地上霜。举头望明月,低头思故乡。',
  'output/audio/tang-libai-jingyesi.mp3',
  'output/timing/tang-libai-jingyesi.json',
  [list('床前明月光'), list('疑是地上霜'), list('举头望明月'), list('低头思故乡')])
print('durationMs =', payload['audioDurationMs'], 'chars =', len(payload['chars']))
"
```

预期:生成 mp3 文件(非空,约 100-300 KB)与 timing JSON;chars 共 20 条,startMs 严格递增。若网络失败 → 按风险门第 2 条处理。

- [ ] **步骤 6:Commit(不含 output/,已忽略)**

```bash
git add content-pipeline/src/tts.py content-pipeline/tests/test_tts.py
git commit -m "feat(内容管线): 添加 edge-tts 音频生成与逐字时间轴提取"
```

---

### 任务 5:校验器

**文件:**
- 创建:`content-pipeline/src/validate.py`
- 测试:`content-pipeline/tests/test_validate.py`

- [ ] **步骤 1:编写失败的测试**

```python
# tests/test_validate.py
from src.models import Poem, Line
from src.validate import validate_poem

def make_poem(**kw):
    base = dict(id="x", title="测", author="测", dynasty="唐", category="唐诗",
                difficulty="qimeng",
                lines=[Line(chars=list("床前明月光"), pinyin=["chuáng","qián","míng","yuè","guāng"], punct=",")],
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
```

- [ ] **步骤 2:运行测试验证失败**

运行:`content-pipeline/.venv/bin/pytest tests/test_validate.py -q`
预期:FAIL,报错 `ModuleNotFoundError: No module named 'src.validate'`

- [ ] **步骤 3:编写实现**

```python
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
```

- [ ] **步骤 4:运行测试验证通过**

运行:`content-pipeline/.venv/bin/pytest tests/test_validate.py -q`
预期:PASS(4 个测试全过)

- [ ] **步骤 5:Commit**

```bash
git add content-pipeline/src/validate.py content-pipeline/tests/test_validate.py
git commit -m "feat(内容管线): 添加数据完整性校验器"
```

---

### 任务 6:构建编排 build.py

**文件:**
- 创建:`content-pipeline/src/build.py`
- 创建:`content-pipeline/src/__main__.py`
- 测试:`content-pipeline/tests/test_build_index.py`

- [ ] **步骤 1:编写失败的测试(索引生成)**

```python
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
```

- [ ] **步骤 2:运行测试验证失败**

运行:`content-pipeline/.venv/bin/pytest tests/test_build_index.py -q`
预期:FAIL,报错 `ModuleNotFoundError: No module named 'src.build'`

- [ ] **步骤 3:编写实现**

```python
# src/build.py
import json
from pathlib import Path
from pypinyin import pinyin as _py, Style
from src.models import Poem, parse_poem_yaml
from src.pinyin import fill_pinyin, load_overrides
from src.validate import validate_poem
from src.tts import synthesize_sync

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
            json.dumps(p.__dict__, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "index.json").write_text(
        json.dumps(build_index(poems), ensure_ascii=False, indent=2), encoding="utf-8")
```

`src/__main__.py`:

```python
from src.build import run_pipeline, generate_audio, write_outputs
import sys

def main() -> int:
    poems, errs = run_pipeline()
    if errs:
        print("\n".join(errs))
        return 1
    if "--audio" in sys.argv:
        n = None
        if "--limit" in sys.argv:
            n = int(sys.argv[sys.argv.index("--limit") + 1])
        generate_audio(poems, max_n=n)
    write_outputs(poems)
    print(f"OK: {len(poems)} 首已构建")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **步骤 4:运行测试验证通过**

运行:`content-pipeline/.venv/bin/pytest tests/test_build_index.py -q`
预期:PASS(2 个测试全过)

- [ ] **步骤 5:Commit**

```bash
git add content-pipeline/src/build.py content-pipeline/src/__main__.py content-pipeline/tests/test_build_index.py
git commit -m "feat(内容管线): 添加构建编排与索引生成"
```

---

### 任务 7:内容批次 1 — 启蒙篇(一)40 首

**文件:**
- 创建:`content-pipeline/data/source/batch1-qimeng-a.yaml`(40 首,见篇目清单)
- 修改:`content-pipeline/data/overrides.csv`(本批次多音字)

- [ ] **步骤 1:编写 40 首源数据**

篇目清单(每首含:诗句原文、逐字拼音由管线生成、译文、背景故事、重点字词 1-4 条):

| # | 篇目 | 作者 |
|---|---|---|
| 1 | 咏鹅 | 骆宾王 |
| 2 | 静夜思 | 李白 |
| 3 | 悯农(锄禾日当午) | 李绅 |
| 4 | 春晓 | 孟浩然 |
| 5 | 登鹳雀楼 | 王之涣 |
| 6 | 画 | 王维 |
| 7 | 古朗月行(节选:小时不识月) | 李白 |
| 8 | 风(解落三秋叶) | 李峤 |
| 9 | 山村咏怀(一去二三里) | 邵雍 |
| 10 | 相思 | 王维 |
| 11 | 游子吟 | 孟郊 |
| 12 | 江雪 | 柳宗元 |
| 13 | 鹿柴 | 王维 |
| 14 | 池上(小娃撑小艇) | 白居易 |
| 15 | 小池 | 杨万里 |
| 16 | 所见 | 袁枚 |
| 17 | 村居 | 高鼎 |
| 18 | 绝句(两个黄鹂鸣翠柳) | 杜甫 |
| 19 | 绝句(迟日江山丽) | 杜甫 |
| 20 | 早发白帝城 | 李白 |
| 21 | 望庐山瀑布 | 李白 |
| 22 | 咏柳 | 贺知章 |
| 23 | 回乡偶书 | 贺知章 |
| 24 | 赠汪伦 | 李白 |
| 25 | 黄鹤楼送孟浩然之广陵 | 李白 |
| 26 | 望天门山 | 李白 |
| 27 | 夜宿山寺 | 李白 |
| 28 | 小儿垂钓 | 胡令能 |
| 29 | 清明 | 杜牧 |
| 30 | 山行 | 杜牧 |
| 31 | 寻隐者不遇 | 贾岛 |
| 32 | 枫桥夜泊 | 张继 |
| 33 | 出塞(秦时明月汉时关) | 王昌龄 |
| 34 | 凉州词(葡萄美酒夜光杯) | 王翰 |
| 35 | 九月九日忆山东兄弟 | 王维 |
| 36 | 送元二使安西 | 王维 |
| 37 | 芙蓉楼送辛渐 | 王昌龄 |
| 38 | 别董大 | 高适 |
| 39 | 江南(江南可采莲) | 汉乐府 |
| 40 | 长歌行(青青园中葵) | 汉乐府 |

YAML 格式示例(`batch1-qimeng-a.yaml` 为多文档 YAML,`---` 分隔):

```yaml
---
id: tang-luobinwang-yonge
title: 咏鹅
author: 骆宾王
dynasty: 唐
category: 唐诗
difficulty: qimeng
lines:
  - chars: [鹅, 鹅, 鹅]
    punct: ","
  - chars: [曲, 项, 向, 天, 歌]
    punct: "。"
  - chars: [白, 毛, 浮, 绿, 水]
    punct: ","
  - chars: [红, 掌, 拨, 清, 波]
    punct: "。"
translation: 大白鹅呀大白鹅,弯着脖子朝着天空唱歌。洁白的羽毛浮在碧绿的水面上,红红的脚掌拨动着清清的水波。
background: 传说骆宾王七岁那年,家里来了一位客人。客人指着池塘里的白鹅,想考考这个小神童。骆宾王望着水中游来游去的白鹅,张嘴就吟出了这首诗,客人们都惊呆了。
keywords:
  - word: 曲项
    explain: 弯着脖子
  - word: 拨
    explain: 划动
```

其余 39 首按同一格式完成,内容要求:译文用短句儿童化语言;背景故事 1-3 句,讲"谁在什么情况下写的";重点字词 1-4 条。所有文字为简体中文,不含生僻网络用语。

- [ ] **步骤 2:运行管线校验**

运行:

```bash
cd content-pipeline
.venv/bin/python -m src
```

预期:输出 `OK: 40 首已构建`,无错误;`output/poems/` 生成 40 个 JSON;抽查 `output/poems/tang-libai-jingyesi.json` 拼音含声调且字数对齐。

- [ ] **步骤 3:为本批次生成音频**

运行:

```bash
cd content-pipeline
.venv/bin/python -m src --audio
```

预期:40 首全部成功,`output/audio/*.mp3` 非空,`output/timing/*.json` 存在且 chars 数与诗句字数一致。逐首核对:运行 `ls output/audio | wc -l` 得 40。

- [ ] **步骤 4:人工抽查音频质量**

抽查 3 首(咏鹅/静夜思/江雪)播放:发音正确、语速适合跟读、无截断。播放命令:

```bash
afplay output/audio/tang-luobinwang-yonge.mp3
```

- [ ] **步骤 5:Commit**

```bash
git add content-pipeline/data/source/batch1-qimeng-a.yaml content-pipeline/data/overrides.csv
git commit -m "feat(内容管线): 新增启蒙篇第一批 40 首诗词源数据"
```

---

### 任务 8:内容批次 2 — 启蒙篇(二)40 首

**文件:**
- 创建:`content-pipeline/data/source/batch2-qimeng-b.yaml`

篇目清单:

| # | 篇目 | 作者 |
|---|---|---|
| 41 | 敕勒歌 | 北朝民歌 |
| 42 | 忆江南 | 白居易 |
| 43 | 渔歌子 | 张志和 |
| 44 | 滁州西涧 | 韦应物 |
| 45 | 晓出净慈寺送林子方 | 杨万里 |
| 46 | 春日 | 朱熹 |
| 47 | 惠崇春江晚景 | 苏轼 |
| 48 | 题西林壁 | 苏轼 |
| 49 | 饮湖上初晴后雨 | 苏轼 |
| 50 | 赠刘景文 | 苏轼 |
| 51 | 望洞庭 | 刘禹锡 |
| 52 | 浪淘沙(九曲黄河万里沙) | 刘禹锡 |
| 53 | 竹石 | 郑燮 |
| 54 | 墨梅 | 王冕 |
| 55 | 石灰吟 | 于谦 |
| 56 | 己亥杂诗(九州生气恃风雷) | 龚自珍 |
| 57 | 示儿 | 陆游 |
| 58 | 游山西村(节选:莫笑农家腊酒浑) | 陆游 |
| 59 | 四时田园杂兴(昼出耘田夜绩麻) | 范成大 |
| 60 | 四时田园杂兴(梅子金黄杏子肥) | 范成大 |
| 61 | 宿新市徐公店 | 杨万里 |
| 62 | 舟过安仁 | 杨万里 |
| 63 | 清平乐·村居 | 辛弃疾 |
| 64 | 西江月·夜行黄沙道中 | 辛弃疾 |
| 65 | 如梦令(常记溪亭日暮) | 李清照 |
| 66 | 夏日绝句 | 李清照 |
| 67 | 泊船瓜洲 | 王安石 |
| 68 | 元日 | 王安石 |
| 69 | 梅花 | 王安石 |
| 70 | 蜂 | 罗隐 |
| 71 | 早春呈水部张十八员外 | 韩愈 |
| 72 | 春夜喜雨(节选:好雨知时节) | 杜甫 |
| 73 | 江畔独步寻花(黄四娘家花满蹊) | 杜甫 |
| 74 | 闻官军收河南河北(节选) | 杜甫 |
| 75 | 秋夜将晓出篱门迎凉有感 | 陆游 |
| 76 | 观书有感(其一) | 朱熹 |
| 77 | 乡村四月 | 翁卷 |
| 78 | 三衢道中 | 曾几 |
| 79 | 采莲曲(荷叶罗裙一色裁) | 王昌龄 |
| 80 | 鸟鸣涧 | 王维 |

步骤与任务 7 相同:编写源数据 → `.venv/bin/python -m src` 校验(预期 `OK: 80 首已构建`)→ `.venv/bin/python -m src --audio`(生成 40 首新音频,已有 40 首自动重生成亦可)→ 抽查音频 → Commit:

```bash
git add content-pipeline/data/source/batch2-qimeng-b.yaml
git commit -m "feat(内容管线): 新增启蒙篇第二批 40 首诗词源数据"
```

---

### 任务 9:内容批次 3 — 启蒙篇(三)40 首

**文件:**
- 创建:`content-pipeline/data/source/batch3-qimeng-c.yaml`

篇目清单:

| # | 篇目 | 作者 |
|---|---|---|
| 81 | 山居秋暝 | 王维 |
| 82 | 使至塞上(节选:大漠孤烟直) | 王维 |
| 83 | 天净沙·秋思 | 马致远 |
| 84 | 静夜思(近现代仿写不收录;此处为)秋浦歌(白发三千丈) | 李白 |
| 85 | 独坐敬亭山 | 李白 |
| 86 | 峨眉山月歌 | 李白 |
| 87 | 春夜洛城闻笛 | 李白 |
| 88 | 子夜吴歌(长安一片月) | 李白 |
| 89 | 闻王昌龄左迁龙标遥有此寄 | 李白 |
| 90 | 渡荆门送别(节选) | 李白 |
| 91 | 望岳(节选:岱宗夫如何) | 杜甫 |
| 92 | 前出塞(节选:挽弓当挽强) | 杜甫 |
| 93 | 月夜忆舍弟(节选:露从今夜白) | 杜甫 |
| 94 | 江南逢李龟年 | 杜甫 |
| 95 | 登高(节选:无边落木萧萧下) | 杜甫 |
| 96 | 赠花卿 | 杜甫 |
| 97 | 逢雪宿芙蓉山主人 | 刘长卿 |
| 98 | 塞下曲(月黑雁飞高) | 卢纶 |
| 99 | 春望(节选:国破山河在) | 杜甫 |
| 100 | 游子吟(重收校验:若 id 冲突则跳过) | 孟郊 |
| 101 | 赋得古原草送别(节选:离离原上草) | 白居易 |
| 102 | 钱塘湖春行(节选) | 白居易 |
| 103 | 暮江吟 | 白居易 |
| 104 | 大林寺桃花 | 白居易 |
| 105 | 遗爱寺 | 白居易 |
| 106 | 夜雨寄北 | 李商隐 |
| 107 | 登乐游原 | 李商隐 |
| 108 | 嫦娥 | 李商隐 |
| 109 | 秋夕 | 杜牧 |
| 110 | 江南春 | 杜牧 |
| 111 | 泊秦淮 | 杜牧 |
| 112 | 赤壁 | 杜牧 |
| 113 | 过华清宫(一骑红尘妃子笑) | 杜牧 |
| 114 | 乌衣巷 | 刘禹锡 |
| 115 | 竹枝词(杨柳青青江水平) | 刘禹锡 |
| 116 | 秋词(自古逢秋悲寂寥) | 刘禹锡 |
| 117 | 陋室铭(节选:山不在高) | 刘禹锡 |
| 118 | 悯农(春种一粒粟) | 李绅 |
| 119 | 江上渔者 | 范仲淹 |
| 120 | 陶者(陶尽门前土) | 梅尧臣 |

注:第 84 行括号内说明是给工作者的提示(避免收录失误),正式数据只写「秋浦歌」。第 100 行游子吟若与批次 1 重复,改为「送杜少府之任蜀州(王勃)」。

步骤与任务 7 相同 → Commit:

```bash
git add content-pipeline/data/source/batch3-qimeng-c.yaml
git commit -m "feat(内容管线): 新增启蒙篇第三批 40 首诗词源数据"
```

---

### 任务 10:内容批次 4 — 进阶篇(一)40 首

**文件:**
- 创建:`content-pipeline/data/source/batch4-jinjie-a.yaml`

篇目清单(难度 jinjie):

| # | 篇目 | 作者 |
|---|---|---|
| 121 | 关雎(节选:关关雎鸠) | 诗经 |
| 122 | 蒹葭(节选:蒹葭苍苍) | 诗经 |
| 123 | 采薇(节选:昔我往矣) | 诗经 |
| 124 | 桃夭 | 诗经 |
| 125 | 木瓜(节选:投我以木瓜) | 诗经 |
| 126 | 静女(节选) | 诗经 |
| 127 | 子衿(节选) | 诗经 |
| 128 | 无衣(节选:岂曰无衣) | 诗经 |
| 129 | 黍离(节选:彼黍离离) | 诗经 |
| 130 | 短歌行(节选:对酒当歌) | 曹操 |
| 131 | 观沧海 | 曹操 |
| 132 | 龟虽寿(节选:老骥伏枥) | 曹操 |
| 133 | 七步诗 | 曹植 |
| 134 | 归园田居(其三:种豆南山下) | 陶渊明 |
| 135 | 饮酒(其五:结庐在人境) | 陶渊明 |
| 136 | 桃花源记(节选:忽逢桃花林) | 陶渊明 |
| 137 | 敕勒歌(重复检查,若批次 2 已收则换)咏荆轲(节选) | 陶渊明 |
| 138 | 与诸子登岘山(节选) | 孟浩然 |
| 139 | 过故人庄 | 孟浩然 |
| 140 | 宿建德江 | 孟浩然 |
| 141 | 望洞庭湖赠张丞相(节选:气蒸云梦泽) | 孟浩然 |
| 142 | 从军行(青海长云暗雪山) | 王昌龄 |
| 143 | 从军行(黄沙百战穿金甲) | 王昌龄 |
| 144 | 塞上曲(蝉鸣空桑林) | 王昌龄 |
| 145 | 少年行(其一:新丰美酒斗十千) | 王维 |
| 146 | 观猎(节选:风劲角弓鸣) | 王维 |
| 147 | 终南别业(节选:行到水穷处) | 王维 |
| 148 | 辋川闲居赠裴秀才迪(节选) | 王维 |
| 149 | 汉江临眺(节选:江流天地外) | 王维 |
| 150 | 陇西行(誓扫匈奴不顾身) | 陈陶 |
| 151 | 燕歌行(节选:汉家烟尘在东北) | 高适 |
| 152 | 白雪歌送武判官归京(节选:忽如一夜春风来) | 岑参 |
| 153 | 逢入京使 | 岑参 |
| 154 | 行军九日思长安故园 | 岑参 |
| 155 | 登科后(节选:春风得意马蹄疾) | 孟郊 |
| 156 | 剑客 | 贾岛 |
| 157 | 题李凝幽居(节选:鸟宿池边树) | 贾岛 |
| 158 | 雁门太守行(节选:黑云压城城欲摧) | 李贺 |
| 159 | 马诗(其五:大漠沙如雪) | 李贺 |
| 160 | 南园(其五:男儿何不带吴钩) | 李贺 |

步骤与任务 7 相同 → Commit:

```bash
git add content-pipeline/data/source/batch4-jinjie-a.yaml
git commit -m "feat(内容管线): 新增进阶篇第一批 40 首诗词源数据"
```

---

### 任务 11:内容批次 5 — 进阶篇(二)50 首

**文件:**
- 创建:`content-pipeline/data/source/batch5-jinjie-b.yaml`

篇目清单:

| # | 篇目 | 作者 |
|---|---|---|
| 161 | 望月怀远(节选:海上生明月) | 张九龄 |
| 162 | 感遇(其一:兰叶春葳蕤) | 张九龄 |
| 163 | 回乡偶书(其二:离别家乡岁月多) | 贺知章 |
| 164 | 春江花月夜(节选:春江潮水连海平) | 张若虚 |
| 165 | 登幽州台歌 | 陈子昂 |
| 166 | 送杜少府之任蜀州 | 王勃 |
| 167 | 滕王阁序(节选:落霞与孤鹜齐飞) | 王勃 |
| 168 | 山中(长江悲已滞) | 王勃 |
| 169 | 从军行(烽火照西京) | 杨炯 |
| 170 | 题都城南庄(节选:人面桃花相映红) | 崔护 |
| 171 | 登楼(节选:锦江春色来天地) | 杜甫 |
| 172 | 蜀相(节选:出师未捷身先死) | 杜甫 |
| 173 | 旅夜书怀(节选:星垂平野阔) | 杜甫 |
| 174 | 登岳阳楼(节选:吴楚东南坼) | 杜甫 |
| 175 | 客至(节选:花径不曾缘客扫) | 杜甫 |
| 176 | 茅屋为秋风所破歌(节选:安得广厦千万间) | 杜甫 |
| 177 | 兵车行(节选:车辚辚,马萧萧) | 杜甫 |
| 178 | 蜀道难(节选:蜀道之难,难于上青天) | 李白 |
| 179 | 将进酒(节选:君不见黄河之水天上来) | 李白 |
| 180 | 行路难(其一:金樽清酒斗十千) | 李白 |
| 181 | 梦游天姥吟留别(节选:海客谈瀛洲) | 李白 |
| 182 | 庐山谣寄卢侍御虚舟(节选) | 李白 |
| 183 | 把酒问月(节选:青天有月来几时) | 李白 |
| 184 | 宣州谢朓楼饯别校书叔云(节选) | 李白 |
| 185 | 长干行(节选:郎骑竹马来) | 李白 |
| 186 | 长恨歌(节选:在天愿作比翼鸟) | 白居易 |
| 187 | 琵琶行(节选:千呼万唤始出来/大珠小珠落玉盘) | 白居易 |
| 188 | 卖炭翁(节选) | 白居易 |
| 189 | 观刈麦(节选:足蒸暑土气) | 白居易 |
| 190 | 问刘十九 | 白居易 |
| 191 | 离思(其四:曾经沧海难为水) | 元稹 |
| 192 | 菊花(秋丛绕舍似陶家) | 元稹 |
| 193 | 酬乐天扬州初逢席上见赠(节选) | 刘禹锡 |
| 194 | 石头城(山围故国周遭在) | 刘禹锡 |
| 195 | 戏赠看花诸君子(紫陌红尘拂面来) | 刘禹锡 |
| 196 | 金铜仙人辞汉歌(节选:衰兰送客咸阳道) | 李贺 |
| 197 | 李凭箜篌引(节选:昆山玉碎凤凰叫) | 李贺 |
| 198 | 梦天(节选:遥望齐州九点烟) | 李贺 |
| 199 | 无题(相见时难别亦难) | 李商隐 |
| 200 | 无题(昨夜星辰昨夜风) | 李商隐 |
| 201 | 锦瑟(节选:庄生晓梦迷蝴蝶) | 李商隐 |
| 202 | 贾生(宣室求贤访逐臣) | 李商隐 |
| 203 | 常娥(云母屏风烛影深) | 李商隐 |
| 204 | 晚晴(节选:天意怜幽草) | 李商隐 |
| 205 | 安定城楼(节选:永忆江湖归白发) | 李商隐 |
| 206 | 蝉(本以高难饱) | 李商隐 |
| 207 | 清明(近现代不收录;此处为)长安秋望(节选:楼倚霜树外) | 杜牧 |
| 208 | 过零丁洋(节选:人生自古谁无死) | 文天祥 |
| 209 | 正气歌(节选:天地有正气) | 文天祥 |
| 210 | 题临安邸 | 林升 |

步骤与任务 7 相同 → Commit:

```bash
git add content-pipeline/data/source/batch5-jinjie-b.yaml
git commit -m "feat(内容管线): 新增进阶篇第二批 50 首诗词源数据"
```

---

### 任务 12:内容批次 6 — 进阶篇(三)与宋词 60 首

**文件:**
- 创建:`content-pipeline/data/source/batch6-jinjie-ci.yaml`

篇目清单(难度 jinjie,宋词为主):

| # | 篇目 | 作者 |
|---|---|---|
| 211 | 水调歌头(明月几时有) | 苏轼 |
| 212 | 念奴娇·赤壁怀古(节选:大江东去) | 苏轼 |
| 213 | 江城子·密州出猎(节选:老夫聊发少年狂) | 苏轼 |
| 214 | 江城子·乙卯正月二十日夜记梦(节选) | 苏轼 |
| 215 | 定风波(莫听穿林打叶声) | 苏轼 |
| 216 | 浣溪沙(山下兰芽短浸溪) | 苏轼 |
| 217 | 蝶恋花(花褪残红青杏小) | 苏轼 |
| 218 | 卜算子·黄州定慧院寓居作(缺月挂疏桐) | 苏轼 |
| 219 | 水龙吟·次韵章质夫杨花词(节选) | 苏轼 |
| 220 | 望海潮(东南形胜,节选) | 柳永 |
| 221 | 雨霖铃(寒蝉凄切,节选:多情自古伤离别) | 柳永 |
| 222 | 蝶恋花(伫倚危楼风细细) | 柳永 |
| 223 | 八声甘州(节选:对潇潇暮雨洒江天) | 柳永 |
| 224 | 苏幕遮(碧云天,黄叶地) | 范仲淹 |
| 225 | 渔家傲·秋思(塞下秋来风景异) | 范仲淹 |
| 226 | 岳阳楼记(节选:先天下之忧而忧) | 范仲淹 |
| 227 | 醉翁亭记(节选:醉翁之意不在酒) | 欧阳修 |
| 228 | 生查子·元夕(去年元夜时) | 欧阳修 |
| 229 | 蝶恋花(庭院深深深几许) | 欧阳修 |
| 230 | 玉楼春(节选:人生自是有情痴) | 欧阳修 |
| 231 | 浣溪沙(一曲新词酒一杯) | 晏殊 |
| 232 | 蝶恋花(槛菊愁烟兰泣露) | 晏殊 |
| 233 | 破阵子(燕子来时新社) | 晏殊 |
| 234 | 木兰花(绿杨芳草长亭路) | 晏殊 |
| 235 | 鹧鸪天(彩袖殷勤捧玉钟) | 晏几道 |
| 236 | 临江仙(梦后楼台高锁) | 晏几道 |
| 237 | 卜算子(我住长江头) | 李之仪 |
| 238 | 鹊桥仙(纤云弄巧) | 秦观 |
| 239 | 踏莎行(雾失楼台) | 秦观 |
| 240 | 浣溪沙(漠漠轻寒上小楼) | 秦观 |
| 241 | 青玉案(凌波不过横塘路,节选:一川烟草) | 贺铸 |
| 242 | 六州歌头(节选:少年侠气) | 贺铸 |
| 243 | 满江红(怒发冲冠) | 岳飞 |
| 244 | 小重山(昨夜寒蛩不住鸣) | 岳飞 |
| 245 | 钗头凤(红酥手) | 陆游 |
| 246 | 卜算子·咏梅(驿外断桥边) | 陆游 |
| 247 | 诉衷情(当年万里觅封侯) | 陆游 |
| 248 | 十一月四日风雨大作 | 陆游 |
| 249 | 冬夜读书示子聿 | 陆游 |
| 250 | 病起书怀(节选:位卑未敢忘忧国) | 陆游 |
| 251 | 书愤(节选:楼船夜雪瓜洲渡) | 陆游 |
| 252 | 临安春雨初霁(节选:小楼一夜听春雨) | 陆游 |
| 253 | 永遇乐·京口北固亭怀古(节选:千古江山) | 辛弃疾 |
| 254 | 菩萨蛮·书江西造口壁(郁孤台下清江水) | 辛弃疾 |
| 255 | 青玉案·元夕(东风夜放花千树) | 辛弃疾 |
| 256 | 丑奴儿·书博山道中壁(少年不识愁滋味) | 辛弃疾 |
| 257 | 南乡子·登京口北固亭有怀(何处望神州) | 辛弃疾 |
| 258 | 破阵子·为陈同甫赋壮词以寄之(醉里挑灯看剑) | 辛弃疾 |
| 259 | 鹧鸪天(陌上柔桑破嫩芽) | 辛弃疾 |
| 260 | 声声慢(寻寻觅觅,节选) | 李清照 |
| 261 | 一剪梅(红藕香残玉簟秋) | 李清照 |
| 262 | 武陵春(风住尘香花已尽) | 李清照 |
| 263 | 醉花阴(薄雾浓云愁永昼) | 李清照 |
| 264 | 永遇乐(落日熔金,节选) | 李清照 |
| 265 | 渔家傲(天接云涛连晓雾) | 李清照 |
| 266 | 点绛唇(蹴罢秋千) | 李清照 |
| 267 | 桂枝香·金陵怀古(登临送目,节选) | 王安石 |
| 268 | 浪淘沙令(帘外雨潺潺) | 李煜 |
| 269 | 相见欢(无言独上西楼) | 李煜 |
| 270 | 虞美人(春花秋月何时了) | 李煜 |

步骤与任务 7 相同 → Commit:

```bash
git add content-pipeline/data/source/batch6-jinjie-ci.yaml
git commit -m "feat(内容管线): 新增进阶篇第三批 60 首诗词源数据"
```

---

### 任务 13:内容批次 7 — 近现代名篇 60 首

**文件:**
- 创建:`content-pipeline/data/source/batch7-xiandai.yaml`

篇目清单(difficulty:jinjie,除特别标注外):

| # | 篇目 | 作者 |
|---|---|---|
| 271 | 沁园春·雪(节选:北国风光) | 毛泽东 |
| 272 | 沁园春·长沙(节选:独立寒秋) | 毛泽东 |
| 273 | 卜算子·咏梅(风雨送春归) | 毛泽东 |
| 274 | 七律·长征 | 毛泽东 |
| 275 | 忆秦娥·娄山关(节选) | 毛泽东 |
| 276 | 十六字令三首(其一:山) | 毛泽东 |
| 277 | 繁星(节选:繁星闪烁着/成功的花) | 冰心 |
| 278 | 春水(节选:墙角的花) | 冰心 |
| 279 | 纸船——寄母亲 | 冰心 |
| 280 | 雨后 | 冰心 |
| 281 | 小小的船 | 叶圣陶 |
| 282 | 瀑布 | 叶圣陶 |
| 283 | 萤火虫 | 叶圣陶 |
| 284 | 弯弯的月儿(重复检查,与 281 同源则换)风 | 叶圣陶 |
| 285 | 天上的街市 | 郭沫若 |
| 286 | 白鹭 | 郭沫若 |
| 287 | 静夜 | 郭沫若 |
| 288 | 再别康桥(节选:轻轻的我走了) | 徐志摩 |
| 289 | 沙扬娜拉(最是那一低头的温柔) | 徐志摩 |
| 290 | 偶然(我是天空里的一片云) | 徐志摩 |
| 291 | 雪花的快乐(节选) | 徐志摩 |
| 292 | 面朝大海,春暖花开(节选) | 海子 |
| 293 | 春暖花开(重复检查,若与 292 同则换)日记 | 海子 |
| 294 | 热爱生命(节选:我不去想是否能够成功) | 汪国真 |
| 295 | 山高路远(节选:呼喊是爆发的沉默) | 汪国真 |
| 296 | 感谢 | 汪国真 |
| 297 | 假如生活欺骗了你 | 普希金(译:戈宝权) |
| 298 | 帆(节选) | 莱蒙托夫(译) |
| 299 | 乡愁(小时候) | 余光中 |
| 300 | 乡愁四韵(节选) | 余光中 |
| 301 | 春天,遂想起(节选) | 余光中 |
| 302 | 断章(你站在桥上看风景) | 卞之琳 |
| 303 | 老马(总得叫大车装个够) | 臧克家 |
| 304 | 有的人(节选:有的人活着) | 臧克家 |
| 305 | 泥土(老是把自己当作珍珠) | 鲁藜 |
| 306 | 礁石(一个浪,一个浪) | 艾青 |
| 307 | 我爱这土地(节选:为什么我的眼里常含泪水) | 艾青 |
| 308 | 大堰河——我的保姆(节选) | 艾青 |
| 309 | 你是人间的四月天(节选:我说你是人间的四月天) | 林徽因 |
| 310 | 笑(节选) | 林徽因 |
| 311 | 花牛歌 | 徐志摩 |
| 312 | 秋晚的江上 | 刘大白 |
| 313 | 晚风 | 刘大白 |
| 314 | 夜 | 叶赛宁(译) |
| 315 | 春的消息(节选:风,摇绿了树的枝条) | 金波 |
| 316 | 雨中的树林 | 金波 |
| 317 | 我们去看海(节选) | 金波 |
| 318 | 狗尾草 | 金波 |
| 319 | 找梦 | 金波 |
| 320 | 四季的风 | 儿童诗(佚名) |
| 321 | 虫和鸟 | 张继楼 |
| 322 | 太阳的话(节选) | 艾青 |
| 323 | 摇篮曲(节选) | 顾城 |
| 324 | 弧线 | 顾城 |
| 325 | 门前(节选:我多么希望,有一个门口) | 顾城 |
| 326 | 一代人(黑夜给了我黑色的眼睛) | 顾城 |
| 327 | 远和近(你,一会看我) | 顾城 |
| 328 | 致橡树(节选:我如果爱你) | 舒婷 |
| 329 | 这也是一切(节选) | 舒婷 |
| 330 | 惠安女子(节选) | 舒婷 |

注:第 284/293 行为防重提示,正式数据不写括号内容;若检查出重复,替换为「繁星(节选)」「雨巷(戴望舒,节选:撑着油纸伞)」。

步骤与任务 7 相同 → Commit:

```bash
git add content-pipeline/data/source/batch7-xiandai.yaml
git commit -m "feat(内容管线): 新增近现代名篇 60 首源数据"
```

---

### 任务 14:内容批次 8 — 小学必背补全 70 首

**文件:**
- 创建:`content-pipeline/data/source/batch8-bibei.yaml`

篇目清单(difficulty:bibei;与已收录篇目重复的不再重复收录,改为把已收录篇目的难度升级为 bibei——本任务同时更新前几批对应篇目的 difficulty 字段,见步骤 1 说明):

| # | 篇目 | 作者 |
|---|---|---|
| 331 | 江南春(若已收则改标) | 杜牧 |
| 332 | 观刈麦(若已收则改标) | 白居易 |
| 333 | 闻王昌龄左迁龙标遥有此寄(若已收则改标) | 李白 |
| 334 | 次北固山下(节选:客路青山外) | 王湾 |
| 335 | 天净沙·秋思(若已收则改标) | 马致远 |
| 336 | 登飞来峰 | 王安石 |
| 337 | 书湖阴先生壁 | 王安石 |
| 338 | 六月二十七日望湖楼醉书 | 苏轼 |
| 339 | 浣溪沙·游蕲水清泉寺(若已收则改标) | 苏轼 |
| 340 | 游园不值 | 叶绍翁 |
| 341 | 夜书所见 | 叶绍翁 |
| 342 | 山居秋暝(若已收则改标) | 王维 |
| 343 | 十五夜望月 | 王建 |
| 344 | 寒食 | 韩翃 |
| 345 | 迢迢牵牛星 | 古诗十九首 |
| 346 | 石灰吟(若已收则改标) | 于谦 |
| 347 | 竹石(若已收则改标) | 郑燮 |
| 348 | 春夜喜雨(若已收则改标) | 杜甫 |
| 349 | 闻官军收河南河北(若已收则改标) | 杜甫 |
| 350 | 己亥杂诗(若已收则改标) | 龚自珍 |
| 351 | 观沧海(若已收则改标) | 曹操 |
| 352 | 龟虽寿(若已收则改标) | 曹操 |
| 353 | 短歌行(若已收则改标) | 曹操 |
| 354 | 观书有感(若已收则改标) | 朱熹 |
| 355 | 墨梅(若已收则改标) | 王冕 |
| 356 | 塞下曲(若已收则改标) | 卢纶 |
| 357 | 送元二使安西(若已收则改标) | 王维 |
| 358 | 别董大(若已收则改标) | 高适 |
| 359 | 春望(若已收则改标) | 杜甫 |
| 360 | 过零丁洋(若已收则改标) | 文天祥 |
| 361 | 卜算子·咏梅(陆游,若已收则改标) | 陆游 |
| 362 | 卜算子·咏梅(毛泽东,若已收则改标) | 毛泽东 |
| 363 | 沁园春·雪(若已收则改标) | 毛泽东 |
| 364 | 七律·长征(若已收则改标) | 毛泽东 |
| 365 | 面朝大海,春暖花开(若已收则改标) | 海子 |
| 366 | 乡愁(若已收则改标) | 余光中 |
| 367 | 天上的街市(若已收则改标) | 郭沫若 |
| 368 | 繁星(节选,若已收则改标) | 冰心 |
| 369 | 纸船(若已收则改标) | 冰心 |
| 370 | 假如生活欺骗了你(若已收则改标) | 普希金 |
| 371 | 未选择的路(节选) | 弗罗斯特(译) |
| 372 | 金色花(节选:假如我变成了一朵金色花) | 泰戈尔(译) |
| 373 | 荷叶·母亲(节选) | 冰心 |
| 374 | 绿(好像绿色的墨水瓶倒翻了) | 艾青 |
| 375 | 白桦(节选) | 叶赛宁(译) |
| 376 | 在天晴了的时候(节选) | 戴望舒 |
| 377 | 采莲曲(若已收则改标) | 王昌龄 |
| 378 | 晓出净慈寺送林子方(若已收则改标) | 杨万里 |
| 379 | 惠崇春江晚景(若已收则改标) | 苏轼 |
| 380 | 绝句(若已收则改标) | 杜甫 |
| 381 | 早春呈水部张十八员外(若已收则改标) | 韩愈 |
| 382 | 枫桥夜泊(若已收则改标) | 张继 |
| 383 | 咏柳(若已收则改标) | 贺知章 |
| 384 | 山行(若已收则改标) | 杜牧 |
| 385 | 清明(若已收则改标) | 杜牧 |
| 386 | 九月九日忆山东兄弟(若已收则改标) | 王维 |
| 387 | 鹿柴(若已收则改标) | 王维 |
| 388 | 池上(若已收则改标) | 白居易 |
| 389 | 小池(若已收则改标) | 杨万里 |
| 390 | 村居(若已收则改标) | 高鼎 |
| 391 | 题西林壁(若已收则改标) | 苏轼 |
| 392 | 游山西村(若已收则改标) | 陆游 |
| 393 | 四时田园杂兴(若已收则改标) | 范成大 |
| 394 | 清平乐·村居(若已收则改标) | 辛弃疾 |
| 395 | 江畔独步寻花(若已收则改标) | 杜甫 |
| 396 | 暮江吟(若已收则改标) | 白居易 |
| 397 | 赠刘景文(若已收则改标) | 苏轼 |
| 398 | 夜书所见(若已收则改标) | 叶绍翁 |
| 399 | 蜂(若已收则改标) | 罗隐 |
| 400 | 悯农(其一+其二,若已收则改标) | 李绅 |

- [ ] **步骤 1:处理难度标注与去重**

做法:先核对前 7 批已收录篇目,凡本表标注「若已收则改标」且确已收录者,不新增数据,而是在原 YAML 中把 `difficulty` 改为 `bibei`(一首诗词可同时属于启蒙/必背——数据模型按主难度存一个值,必背清单由 `index.json` 的 `bibeiIds` 数组维护)。本步骤产出:`data/source/batch8-bibei.yaml`(仅含真正新增的篇目)+ 前几批 YAML 的 difficulty 修正。

- [ ] **步骤 2:运行管线校验**

运行:`content-pipeline/.venv/bin/python -m src`
预期:`OK: 约400 首已构建`,无错误;`output/index.json` 中 `bibei` 组数量 ≥ 130。

- [ ] **步骤 3:生成全部缺失音频并全量校验**

运行:`content-pipeline/.venv/bin/python -m src --audio`
预期:全部成功。全量核对脚本:

```bash
cd content-pipeline
.venv/bin/python -c "
import json, pathlib
idx = json.loads(pathlib.Path('output/index.json').read_text(encoding='utf-8'))
n = len(idx['poems'])
audio = len(list(pathlib.Path('output/audio').glob('*.mp3')))
timing = len(list(pathlib.Path('output/timing').glob('*.json')))
print(f'poems={n} audio={audio} timing={timing}')
assert n == audio == timing, '数量不一致'
print('ALL OK')
"
```

预期:`poems=N audio=N timing=N` 且 `ALL OK`。

- [ ] **步骤 4:Commit**

```bash
git add content-pipeline/data/source/
git commit -m "feat(内容管线): 补全小学必背篇目,完成 400 首内容库"
```

---

### 任务 15:管线文档与收尾

**文件:**
- 修改:`content-pipeline/README.md`(补充运行说明、目录约定、多音字覆盖维护方法)
- 修改:`docs/superpowers/specs/2026-09-17-shiya-design.md`(如实际执行与规格有出入,记录差异)

- [ ] **步骤 1:更新 README**

README 需包含:环境搭建(venv + 清华镜像)、三种运行方式(`-m src` 校验构建 / `-m src --audio` 生成音频 / `-m src --audio --limit 5` 测试用)、overrides.csv 格式与维护说明、output 目录结构与「不入库」约定。

- [ ] **步骤 2:全量回归**

运行:

```bash
cd content-pipeline
.venv/bin/pytest tests/ -q
.venv/bin/python -m src
```

预期:pytest 全过(12+ 测试);构建 OK 无校验错误。

- [ ] **步骤 3:Commit**

```bash
git add content-pipeline/README.md
git commit -m "docs(内容管线): 完善管线使用文档与维护说明"
```

---

## 自检记录

- 规格覆盖度:规格第 7/8 节(数据模型、内容管线、400 首规模、难度分级)全部由任务 2-14 覆盖
- 类型一致性:`Poem`/`Line`/`Keyword` 字段在 models/tts/validate/build 间一致;`align_chars` 返回结构 `{line,index,startMs,endMs}` 与 timing JSON 一致
- 占位符扫描:所有批次任务含具体篇目清单;示例代码可运行;无「待定/TODO」
- 风险:edge-tts 网络不可达(风险门已定义降级路径);多音字需逐批人工增补 overrides.csv(已纳入各批次步骤)
