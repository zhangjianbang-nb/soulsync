# SoulSync — 多模态情感陪伴智能体

> 大型项目：安卓 App + 多模态感知 + 长期记忆 + 主动智能 + 多语言
> 定位：一个"认识你、记得你、主动关心你"的 AI 陪伴者

## 一、需求拆解（用户指定 8 大模块）

| # | 模块 | 关键能力 | 对应论文方向 |
|---|------|---------|------------|
| 1 | 记忆系统 | 分层记忆（工作/情景/语义/画像）、反思生成、遗忘曲线、检索 | Memory/Reflection |
| 2 | 人员识别-人脸 | 人脸检测+识别、新用户注册、情绪读取 | Face Recognition |
| 3 | 人员识别-声纹 | 说话人验证/识别、声纹注册、VAD | Speaker Verification |
| 4 | 身份融合与名字 | 人脸↔声纹绑定、称呼管理、多用户档案 | Identity Fusion |
| 5 | 情绪感知 | 文本情绪+语音情绪+面部表情三模态融合 | Emotion Recognition |
| 6 | 主动智能 | 主动性判断、关怀推送、冷启动破冰、话题延续 | Proactive Agent |
| 7 | 多语言 | 中/英/日/韩等对话、情感表达本地化 | Multilingual LLM |
| 8 | 记忆反思 | 定期反思生成洞察、关系进展追踪、矛盾检测 | Reflection |

## 二、系统架构

```
┌─────────────────────────────────────────────────────┐
│                  Android App (Kotlin)                │
│  ┌──────────┐ ┌──────────┐ ┌────────────────────┐   │
│  │ CameraX  │ │ AudioRec │ │  Chat UI (Compose) │   │
│  │ 人脸/表情 │ │ VAD/声纹  │ │  多语言/情绪卡片    │   │
│  └────┬─────┘ └────┬─────┘ └─────────┬──────────┘   │
│       │            │                 │              │
│  ┌────▼────────────▼─────────────────▼──────────┐   │
│  │        Agent Core (Kotlin 协程编排)           │   │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ │   │
│  │  │Percept │ │Memory  │ │Emotion │ │Proactive│ │   │
│  │  │ 人脸声纹│ │4层记忆 │ │三模态  │ │主动关怀 │ │   │
│  │  └────────┘ └────────┘ └────────┘ └────────┘ │   │
│  └────────────────────┬────────────────────────┘   │
└───────────────────────┼─────────────────────────────┘
                        │ HTTP/SSE (局域网/远程)
┌───────────────────────▼─────────────────────────────┐
│              SoulSync Server (Python/FastAPI)         │
│  ┌─────────┐ ┌──────────┐ ┌─────────────────────┐   │
│  │InsightFace│ │ 3D-Speaker│ │ Qwen2.5-Omni/GLM  │   │
│  │ 人脸识别  │ │ 声纹识别  │ │ 对话+情绪+多语言    │   │
│  └─────────┘ └──────────┘ └─────────────────────┘   │
│  ┌─────────────────────────────────────────────┐    │
│  │     Memory Engine (SQLite + 向量检索)         │    │
│  │  工作记忆/情景记忆/语义记忆/用户画像 + 反思器    │    │
│  └─────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────┘
```

**关键决策**（依据 GB10 设备 + 本机已有模型）：
- 本机已有 vLLM 服务 GLM-5.3-Flash（gateway :10450）→ 对话主模型
- 人脸/表情：InsightFace（buffalo_l，~330MB ONNX，CPU/GPU 均可）
- 声纹：3D-Speaker（CAM++，~28MB ONNX）+ silero-vad
- 语音情绪：emotion2vec/wav2vec2（可选，V1 用声纹模型特征兜底）
- 安卓端尽量薄：只做采集+UI，重活在服务端

## 三、仓库结构（大型项目标准）

```
soulsync/
├── README.md                    # 项目门面（英文，GitHub 风格）
├── LICENSE                      # Apache-2.0
├── docs/
│   ├── ARCHITECTURE.md          # 架构详解
│   ├── SURVEY.md                # 50篇论文调研精华(链接报告)
│   ├── MEMORY_DESIGN.md         # 记忆系统设计
│   └── ROADMAP.md               # 路线图
├── server/                      # Python 服务端
│   ├── pyproject.toml
│   ├── soulsync/
│   │   ├── main.py              # FastAPI 入口
│   │   ├── config.py
│   │   ├── agent/               # Agent 核心
│   │   │   ├── core.py          # 编排器
│   │   │   ├── llm.py           # LLM 客户端（OpenAI 兼容）
│   │   │   ├── persona.py       # 人格与多语言
│   │   │   └── proactive.py     # 主动智能引擎
│   │   ├── perception/          # 感知模块
│   │   │   ├── face.py          # 人脸+表情
│   │   │   ├── voice.py         # 声纹+VAD
│   │   │   └── fuse.py          # 身份融合
│   │   ├── memory/
│   │   │   ├── store.py         # SQLite + 向量
│   │   │   ├── layers.py        # 4层记忆
│   │   │   ├── reflector.py     # 反思引擎
│   │   │   └── prompts.py
│   │   ├── emotion/
│   │   │   └── fusion.py        # 三模态情绪融合
│   │   └── api/
│   │       └── routes.py        # REST+SSE
│   └── tests/
├── app/                         # Android (Kotlin+Compose)
│   ├── build.gradle.kts
│   └── app/src/main/
│       ├── java/com/soulsync/app/
│       │   ├── MainActivity.kt
│       │   ├── ui/              # Compose 界面
│       │   ├── net/             # API 客户端
│       │   └── capture/         # CameraX/AudioRecord
│       └── ...
├── scripts/                     # 部署/测试脚本
└── .github/workflows/ci.yml     # CI
```

## 四、模型选型（全部本地可用/开源）

| 用途 | 模型 | 大小 | 依据 |
|-----|------|-----|-----|
| 对话主模型 | GLM-5.3-Flash（本机 gateway :10450） | - | 已部署、中文强 |
| 备选云模型 | Qwen2.5-Omni-7B / MiniCPM-o | 7B | 端到端语音 |
| 人脸检测+识别 | InsightFace buffalo_l | 330MB | 精度/速度平衡，开源协议注意 |
| 表情识别 | InsightFace emotion 属性 + 文本情绪 | 0 | 复用人脸模型 |
| 声纹 | 3D-Speaker CAM++ ONNX | 28MB | 中文社区活跃 |
| VAD | silero-vad | 2MB | 事实标准 |
| Embedding | bge-small-zh-v1.5 | 95MB | 中文向量好 |
| TTS（可选 V2） | CosyVoice | - | 情感 TTS |

## 五、里程碑

- [x] M0: 论文调研 50 篇 + 报告
- [ ] M1: 服务端骨架（LLM+记忆+API）
- [ ] M2: 感知模块（人脸+声纹+情绪融合）
- [ ] M3: 主动智能 + 反思
- [ ] M4: 安卓 App
- [ ] M5: GitHub 发布（README/CI/文档）
