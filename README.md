# SoulSync 💙

**A multimodal emotional companion agent — it that knows you, remembers you, and reaches out first.**
**认识你、记得你、主动关心你的多模态情感陪伴智能体。**

[![CI](https://github.com/zhangjianbang-nb/soulsync/actions/workflows/ci.yml/badge.svg)](../../actions)
[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-green)](server/)
[![Android](https://img.shields.io/badge/android-minSdk%2026-green)](app/)

---

## What is SoulSync?

SoulSync is not a chatbot that answers questions — it's a companion that **builds a relationship**:

| Capability | How it works |
|---|---|
| 🧠 **Layered Memory** | 4-layer memory (working / episodic / semantic / profile) with importance-gated writes, 3-factor retrieval scoring (recency × importance × relevance), and Ebbinghaus-style forgetting |
| 🪞 **Memory Reflection** | End-of-session extraction, nightly consolidation (Mem0-style merge arbitration), and Generative-Agent-style insight reflection |
| 👤 **Person Recognition** | Face (InsightFace ArcFace 512-d) + voiceprint (ECAPA-TDNN 192-d) with co-occurrence identity binding and name learning |
| 💗 **Emotion Awareness** | Text (LLM structured) + voice (SER) sensor fusion — when they disagree, voice wins |
| 🚀 **Proactive Intelligence** | "Inner thought" scoring gate, time/event/emotion triggers, trust feedback loop (negative reactions → cooldown), daily cap |
| 🌍 **Multilingual** | zh/en/ja/ko + more — language detection routing, cross-lingual shared memory, 4-language Android UI |
| 🛡️ **Safety Bypass** | Crisis language routes around ALL personalization straight to professional-help guidance; full "right to be forgotten" API |
| 📱 **Android App** | Kotlin + Compose, camera/mic capture, proactive-care notifications |

**50+ research papers** back every design decision — see [docs/SURVEY.md](docs/SURVEY.md) (English tables) with per-decision citations like `[S38]`.

## Architecture

```
┌─────────────────────────────────────────────────┐
│           Android App (Kotlin + Compose)         │
│   Chat UI · CameraX face frames · Mic PCM16k     │
│   Proactive-care JobScheduler notifications      │
└───────────────────┬─────────────────────────────┘
                    │ HTTP JSON (LAN / remote)
┌───────────────────▼─────────────────────────────┐
│          SoulSync Server (Python / FastAPI)      │
│                                                  │
│  Perception   InsightFace buffalo_l (face 512d)  │
│               ECAPA-TDNN (voice 192d)            │
│               IdentityResolver (co-occurrence)   │
│                                                  │
│  Emotion      text-LLM ‖ voice-SER → fusion      │
│               (voice wins on conflict)           │
│                                                  │
│  Memory       SQLite + vectors, 4 layers         │
│               Reflector: extract/consolidate/    │
│               reflect (+ forgetting curve)       │
│                                                  │
│  Agent        ProactiveEngine (inner-thought     │
│               gate + trust loop) · Persona       │
│               · LLM (any OpenAI-compatible)      │
└──────────────────────────────────────────────────┘
```

## Quick Start

### 1. Server

```bash
cd server
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[llm-local]"
# 感知模块（人脸/声纹，可选但推荐）：
pip install -e ".[perception]"

# 指向任意 OpenAI 兼容 LLM（示例：本地 vLLM / GLM gateway / OpenAI）
export SOULSYNC_LLM_BASE_URL="http://127.0.0.1:10450/v1"
export SOULSYNC_LLM_MODEL="glm-5.3-flash"
# 可选：多语 embedding（不设则用内置哈希向量降级，语义检索质量下降）
export SOULSYNC_EMBED_BASE_URL="http://127.0.0.1:10450/v1"
export SOULSYNC_EMBED_MODEL="bge-m3"

uvicorn soulsync.main:app --host 0.0.0.0 --port 8800
```

### 2. Android App

用 Android Studio 打开 `app/`，改 `AppSession.serverUrl` 默认值为你的服务器地址，构建安装。

### 3. Talk to it

```bash
curl -X POST http://localhost:8800/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{"user_id": "me", "text": "我今天感冒了，头好疼"}'

# 下一轮它会记得：
# → "上次你说感冒了，现在好些了吗？"
```

## Model Selection (why these)

| Role | Model | Why |
|---|---|---|
| Conversation LLM | Any OpenAI-compatible (GLM-4.5/Qwen/GPT) | 中文共情 + 原生多语 [S40] |
| Face | InsightFace buffalo_l (RetinaFace + ArcFace-r50) | 检测+识别一体，330MB ONNX [S18][S19] |
| Voiceprint | ECAPA-TDNN 192-d | VoxCeleb SOTA 经典 [S22] |
| Voice emotion | emotion2vec+ (FunASR) | 中英 SER + valence/arousal [S30] |
| Embedding | bge-m3 | 多语 1024d，跨语言记忆共享 [S43] |
| On-device (roadmap) | MiniCPM-V4 MNN 4-bit | 实测 17 tok/s，离线兜底 [S45] |

## Project Layout

```
soulsync/
├── docs/                 SURVEY.md (52 篇文献) · ARCHITECTURE.md · ROADMAP.md
├── server/               Python 服务端
│   ├── soulsync/
│   │   ├── agent/        core(编排) · llm · persona(多语言) · proactive(主动)
│   │   ├── perception/   face · voice · fuse(身份融合)
│   │   ├── memory/       store(4层+遗忘) · reflector(反思) · embeddings
│   │   ├── emotion/      fusion(传感器融合)
│   │   ├── api/          routes(13 REST 端点)
│   │   └── main.py       FastAPI 入口
│   └── tests/            20 个测试（单测 + e2e mock-LLM）
├── app/                  Android (Kotlin/Compose, minSdk 26)
│   └── app/src/main/     UI(四语) · net · capture · proactive · manifest
└── .github/workflows/    CI（pytest）
```

## API Overview

| Endpoint | Purpose |
|---|---|
| `POST /v1/chat` | 一轮对话（可带 face_b64 / voice_wav_b64） |
| `POST /v1/session/end` | 会话结束 → 触发反思 |
| `POST /v1/proactive` | 询问是否该主动问候（返回 null=否） |
| `POST /v1/proactive/reaction` | 反馈用户对主动消息的反应 |
| `POST /v1/register/face` · `/voice` | 注册人脸/声纹 |
| `POST /v1/identity/name` | 教它你的名字 |
| `GET /v1/memories/{user}` · `DELETE ...` | 记忆查看/删除（被遗忘权） |
| `DELETE /v1/user/{user}` | 完全遗忘（GDPR 级） |
| `GET /v1/health` | 状态 + 感知模块可用性 |

## Roadmap

- [x] M0 — 50+ paper survey ([docs/SURVEY.md](docs/SURVEY.md))
- [x] M1 — Server: memory engine + reflection + API (20 tests green)
- [x] M2 — Perception: face + voiceprint + identity fusion
- [x] M3 — Emotion fusion + proactive engine + multilingual
- [x] M4 — Android app (chat UI, 4 languages, capture, notifications)
- [ ] M5 — On-device fallback (MiniCPM-MNN), voice emotion2vec integration, SSE streaming
- [ ] M6 — Multi-user family mode (pyannote diarization [S23]), memory album UI

## License

Apache-2.0. 注意 InsightFace 模型权重仅供研究用途（见其官方协议），商用部署请替换为可商用模型。
