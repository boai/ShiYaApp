# content-pipeline:「诗芽」内容管线

把人工整理的诗词源数据(YAML)加工成应用内置资产:poems JSON、逐字拼音、朗读 mp3、逐字时间轴,全部通过校验。产物由 Android 应用打包进 assets。

## 四个模块

- `src/pinyin.py` — 逐字拼音生成与多音字覆盖(读取 `data/overrides.csv`)
- `src/tts.py` — edge-tts 音频生成与逐字时间轴提取
- `src/validate.py` — 数据完整性校验器
- `src/build.py` — 编排管线:解析源数据(`src/models.py` 提供数据模型)→ 拼音 → 校验 → 输出

## 运行方式

```bash
.venv/bin/python -m src.build
```

## 产物目录约定

- `data/source/*.yaml` — 诗词源数据(人工整理,入库)
- `data/overrides.csv` — 多音字读音覆盖表(入库)
- `output/` — 构建产物(poems/、index.json、audio/、timing/),不入库,由脚本重新生成;应用构建时复制到 assets

环境要求:Python ≥ 3.9,依赖清单见 `requirements.txt`。
