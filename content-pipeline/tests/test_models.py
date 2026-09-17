# tests/test_models.py
import yaml
from src.models import Poem, Line, Keyword, parse_poem_yaml, parse_poems_yaml

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

def test_parse_poem_yaml_bibei_true():
    p = parse_poem_yaml(SAMPLE + "bibei: true\n")
    assert p.bibei is True

def test_parse_poem_yaml_bibei_defaults_false():
    p = parse_poem_yaml(SAMPLE)
    assert p.bibei is False

def test_parse_poem_yaml_audio_path_uses_m4a():
    p = parse_poem_yaml(SAMPLE)
    assert p.audio == "audio/tang-libai-jingyesi.m4a"

# 批次源数据是多文档 YAML(data/source/batch*.yaml,`---` 分隔)
DOC2 = (SAMPLE.replace("id: tang-libai-jingyesi", "id: tang-luobinwang-yonge")
              .replace("title: 静夜思", "title: 咏鹅")
              .replace("author: 李白", "author: 骆宾王")
              .replace("chars: [床, 前, 明, 月, 光]", "chars: [鹅, 鹅, 鹅]"))
MULTI_SAMPLE = SAMPLE + "---\n" + DOC2

def test_parse_poems_yaml_multi_document():
    poems = parse_poems_yaml(MULTI_SAMPLE)
    assert len(poems) == 2
    assert poems[0].id == "tang-libai-jingyesi"
    assert poems[0].title == "静夜思"
    assert poems[0].author == "李白"
    assert poems[0].lines[0].chars == ["床", "前", "明", "月", "光"]
    assert poems[1].id == "tang-luobinwang-yonge"
    assert poems[1].title == "咏鹅"
    assert poems[1].author == "骆宾王"
    assert poems[1].lines[0].chars == ["鹅", "鹅", "鹅"]
    assert poems[1].lines[0].punct == ","
    assert poems[1].audio == "audio/tang-luobinwang-yonge.m4a"

def test_parse_poems_yaml_single_document():
    poems = parse_poems_yaml(SAMPLE)
    assert len(poems) == 1
    assert poems[0].id == "tang-libai-jingyesi"
