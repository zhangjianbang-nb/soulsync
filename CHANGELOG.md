# Changelog

## [0.2.0] — 2026-09-19

### Added
- **多轮对话上下文**：工作记忆成对进 messages（`_build_history`），LLM 看得到前文
- **SSE 流式对话** `POST /v1/chat/stream`：meta → delta*… → done 事件序列
- **反思定时器**：服务端后台任务周期性对活跃用户执行巩固+反思（夜间批处理 [S15]），
  每日自动执行遗忘曲线衰减 [S3]
- **语音情绪 emotion2vec 集成**（`perception/voice_emotion.py`）：funasr 可用时真 SER，
  缺失时自动降级能量特征兜底
- 安卓：`chatStream` SSE 客户端、聊天气泡流式渲染、语音按钮（运行时权限申请，
  4 秒 PCM 随消息上传做声纹+语音情绪）

### Changed
- `LLMClient.complete` 支持 `history` 参数；新增 `LLMClient.stream` 异步生成器
- main.py 改 lifespan 管理（startup/shutdown 启停后台任务）
- 测试 20 → 24（SSE 事件序列/多轮 history/后台任务循环/health）

## [0.1.0] — 2026-09-19

首个公开版本。

### Added
- 52 篇论文调研报告 docs/SURVEY.md（记忆/反思/人脸/声纹/情绪/主动/多语言/端侧八组）
- 服务端 soulsync：四层记忆引擎（三维检索打分+遗忘曲线）、反思器（抽取/巩固/洞察）、
  人脸+声纹识别与身份融合（共现绑定）、情绪传感器融合、主动智能（内心独白门控+
  信任反馈降频）、多语言路由、危机旁路、被遗忘权；13 个 REST 端点
- 安卓 App：Compose 聊天界面（zh/en/ja/ko）、CameraX/Mic 采集、主动关怀通知
- CI：pytest（20 测试）

### Notes
- 感知模型（insightface/speechbrain/emotion2vec）为可选依赖，缺省降级运行
