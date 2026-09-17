# 诗芽(ShiYa)

面向 4-5 岁及以上儿童的诗词学习 Android TV 应用。孩子跟着电视学诗、背诗,家长用遥控器操作。

## 特性

- **精选诗词库:** 约 400 首儿童适读经典(唐诗、宋词、近现代名篇、诗经/汉乐府),按难度分三级:启蒙篇、进阶篇、小学必背(覆盖课标 75 + 80 篇)
- **逐字拼音:** 每字上方标注拼音,多音字人工校验
- **有声朗读:** 内置高品质神经网络语音朗读音频,支持 0.6x / 0.8x / 1.0x 三档语速
- **KTV 式进度:** 朗读逐字高亮——已读字朱砂染红、当前字月光光环、当前行光雾带,配描金进度条
- **儿童化讲解:** 译文、背景故事、重点字词,以线装书翻页形式呈现
- **跟读模式:** 每句读完自动暂停,孩子跟读后按 OK 继续
- **画卷雅韵视觉:** 月夜山水古画长卷 + 锦缎包首 + 镶玉轴头 + 洒金宣纸,适配 TV 遥控器焦点交互
- **完全离线:** 数据、音频全部内置,无网络依赖

## 技术栈

- Kotlin + Jetpack Compose for TV(androidx.tv:tv-material)
- Media3 ExoPlayer(音频播放与变速)
- kotlinx-serialization(JSON 数据解析)
- DataStore(收藏与学习记录)

## 项目结构

```
tv/shiya/
├── app/                     # Android 应用模块(包名 com.shiya.poems)
├── content-pipeline/        # 内容生成脚本(Python:诗词数据/拼音/音频/时间轴)
├── prototypes/              # 视觉设计样板(HTML,定稿后可删)
└── docs/                    # 设计文档与实现计划
```

## 构建

```bash
# 环境要求:JDK 17、Android SDK(API 34)
./gradlew assembleDebug
```

输出 APK 位于 `app/build/outputs/apk/debug/`。

## 设计文档

- [设计规格](docs/superpowers/specs/2026-09-17-shiya-design.md)

## 许可证

[MIT](./LICENSE)
