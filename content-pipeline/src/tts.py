# edge-tts 后端(网络恢复后可切换启用;当前主后端为 tts_macos)
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
