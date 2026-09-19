# Changelog

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
