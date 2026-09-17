"""macOS 系统语音后端:say 生成朗读音频 + afconvert 转 m4a,逐字时间轴按比例估算。"""
import json
import re
import subprocess
from pathlib import Path

VOICE = "Tingting"
RATE = 130                     # say 语速(词/分钟),儿童跟读用慢速
LINE_PAUSE_UNITS = 1.2         # 每行行尾停顿,折算为字数单位


def estimate_timing(duration_ms: int, lines: list[list[str]],
                    line_pause_units: float = LINE_PAUSE_UNITS) -> list[dict]:
    """按比例估算逐字时间轴:每字 1 单位,每行行尾加 line_pause_units 单位停顿,
    停顿吸收进该行末字的 endMs。返回 [{line,index,startMs,endMs}, ...],
    首字 startMs=0,末字 endMs=duration_ms,严格单调。"""
    total_units = sum(len(line) + line_pause_units for line in lines)
    if total_units <= 0 or duration_ms <= 0:
        raise ValueError("lines 为空或 duration_ms 非正")
    unit = duration_ms / total_units
    out = []
    acc = 0.0
    for li, line in enumerate(lines):
        for ci in range(len(line)):
            start = acc
            acc += unit
            end = acc + (line_pause_units * unit if ci == len(line) - 1 else 0.0)
            out.append({"line": li, "index": ci,
                        "startMs": round(start), "endMs": round(end)})
            if ci == len(line) - 1:
                acc = end
    return out


def _afinfo_duration_ms(path: str) -> int:
    proc = subprocess.run(["afinfo", path], capture_output=True, text=True)
    m = re.search(r"estimated duration:\s*([\d.]+)\s*sec", proc.stdout)
    if not m:
        raise RuntimeError(f"无法解析音频时长: {proc.stdout[:200]}")
    return round(float(m.group(1)) * 1000)


def synthesize(text: str, out_m4a: str, out_timing: str,
               lines: list[list[str]]) -> dict:
    """生成 m4a 与估算逐字时间轴,返回 {audioDurationMs, chars}。"""
    Path(out_m4a).parent.mkdir(parents=True, exist_ok=True)
    Path(out_timing).parent.mkdir(parents=True, exist_ok=True)
    aiff = out_m4a + ".aiff"
    p1 = subprocess.run(["say", "-v", VOICE, "-r", str(RATE), "-o", aiff, text],
                        capture_output=True, text=True)
    if p1.returncode != 0:
        raise RuntimeError(f"say 失败: {p1.stderr.strip()}")
    try:
        p2 = subprocess.run(["afconvert", "-f", "m4af", "-d", "aac", aiff, out_m4a],
                            capture_output=True, text=True)
        if p2.returncode != 0:
            raise RuntimeError(f"afconvert 失败: {p2.stderr.strip()}")
    finally:
        Path(aiff).unlink(missing_ok=True)
    duration_ms = _afinfo_duration_ms(out_m4a)
    chars = estimate_timing(duration_ms, lines)
    payload = {"audioDurationMs": duration_ms, "chars": chars}
    with open(out_timing, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return payload


def synthesize_sync(text: str, out_m4a: str, out_timing: str,
                    lines: list[list[str]]) -> dict:
    return synthesize(text, out_m4a, out_timing, lines)
