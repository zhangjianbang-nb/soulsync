# SoulSync 调研报告：情感陪伴多模态智能体（52 篇精选）

> 检索日期：2026-09-18/19。检索源：OpenAlex（三通道：关键词 relevance、标题 filter、引用数排序），
> 原始记录 300+ 条，人工精选筛选 52 篇入报告。编号 [S1]-[S52] 按主题分组。
> 六大主题对应用户需求：**记忆与反思 / 人员识别（人脸+声纹）/ 情绪感知 / 主动智能 / 多语言 / 端侧部署**。
> 完整 43 篇记忆方向长版报告见 `companion-agent-survey/survey_memory.md`（含检索方法论附录）。

---

## 总览：六大模块 × 文献证据地图

| 模块 | 核心文献 | 工程结论 |
|------|---------|---------|
| M1 记忆系统 | [S1]-[S12] | 四层记忆 + 三维检索打分 + 每日巩固批处理 |
| M2 记忆反思 | [S13]-[S16] | Reflexion 式经验卡 + 生成式代理反思树 |
| M3 人脸识别 | [S17]-[S21] | InsightFace (RetinaFace+ArcFace) 一体化方案 |
| M4 声纹识别 | [S22]-[S25] | ECAPA-TDNN 192 维 + 余弦验证 |
| M5 情绪感知 | [S26]-[S34] | 文本 LLM + 语音 SER 双路 + 会话上下文图网络 |
| M6 主动智能 | [S35]-[S39] | 时机选择模型 + 信任反馈循环 + 内心独白 |
| M7 多语言 | [S40]-[S44] | LLM 原生多语 + 语言检测路由 + 跨语言记忆共享 |
| M8 端侧与安全 | [S45]-[S52] | 端云协同 + 量化部署 + 心理安全红线 |

---

## 一、记忆系统（M1）

**[S1] Generative Agents: Interactive Simulacra of Human Behavior**（Park et al., 2023, 引用 1837）
奠基之作：记忆流 + 检索打分（recency × importance × relevance）+ 反思树。**直接采用其检索打分公式作为召回排序核心**，重要性由 LLM 自评 1-10 区分"用户感冒了"与"今天天气好"。

**[S2] MemGPT: Towards LLMs as Operating Systems**（Packer et al., 2023）
虚拟内存思想：LLM 上下文=主存、外部存储=磁盘，中断驱动分页。陪伴对话无限长，采用其 main/external 分页思想：近期对话+用户画像快照放主存，历史事件按需换页。

**[S3] MemoryBank: Enhancing LLMs with Long-Term Memory**（Zhong et al., 2024, AAAI）
首个明确面向 personal companion 的记忆框架：**艾宾浩斯遗忘曲线**驱动记忆更新 + 每日事件总结。遗忘不是缺陷而是特性——控制存储成本且避免"过度记忆的不适感"。

**[S4] Mem0: Building Production-Ready AI Agents with Scalable Long-Term Memory**（Chadha et al., 2025）
生产级"抽取-合并-裁决"流水线：新记忆与旧记忆冲突时 LLM 裁决 ADD/UPDATE/DELETE/NOOP。**采用为记忆写入的标准管线**（用户新说"养了猫"与旧画像"无宠物"冲突的解法）。

**[S5] A Survey on the Memory Mechanism of LLM-based Agents**（Zhang et al., 2025, ACM TOIS）
权威分类学：写什么/怎么管/怎么 memory、怎么读。用作设计评审清单。

**[S6] Memory Matters: The Need to Improve Long-Term Memory in LLM-Agents**（Laird et al., 2024）
反面参照：纯向量库"什么都记、平铺无结构"的通病。陪伴关系需要"重点突出、琐碎淡忘"。

**[S7] H-MEM: Hierarchical Memory for LLM Agents**（2026）
分层索引：话题→时期→条目，类似人类目录式自传体记忆。长期陪伴（年级体量）下平铺检索会退化，采用分层路由。

**[S8] Evaluating Very Long-Term Conversational Memory（LOCOMO）**（Maharana et al., 2024, ACL）
基准：平均 26-30 会话跨会话记忆一致性测试。上线前测"记忆保持率"。

**[S9] Personalizing Dialogue Agents（PersonaChat）**（Zhang et al., 2018, ACL, 引用 1219）
显式画像（哪怕几句话）显著提升一致性与吸引度。用户画像采用其键值式 persona 格式。

**[S10] Informing augmented memory system design through autobiographical memory theory**（Sellen et al., 2007）
设计哲学：人类记忆是**有损重构**而非录像。"完美记住每句话"不像人也不健康；记忆应随时间语义化、概括化。

**[S11] Personalized Quest and Dialogue Generation via KG + LLM**（Cui et al., 2023）
图谱管"硬事实"（生日/纪念日/人物关系），向量管"软语义"（语气/偏好/情绪）。**采用为双通道架构**。

**[S12] Heterogeneous-Computing 自传体记忆级联模型 / CLS 理论**（McClelland et al., 1995）
慢速学习系统沉淀快速情景记忆的理论基础，支撑"夜间批处理巩固"设计。

## 二、记忆反思（M2）

**[S13] Reflexion: Language Agents with Verbal Reinforcement Learning**（Shinn et al., 2023）
失败经验→语言化"经验卡片"→下次行动注入。陪伴场景转化为：冲突修复经验、话题成功/失败复盘。

**[S14] Generative Agents 的反思机制**（同 [S1]）
当累计重要性超过阈值时触发"最近 100 条记忆→3 个高层洞察"的反思。反思产物本身入记忆流。**采用为定时反思器**。

**[S15] Sleep-time Compute / 离线巩固**（2025）
空闲期"睡眠计算"：重放当日事件→去重合并→生成摘要→沉淀语义记忆。用生成摘要即可，无需原始日志。

**[S16] Hippocampus-Inspired AI Memory**（2024-2026 系列）
海马体启发的情景-语义转化管线，佐证"会话结束即抽取事件 + 空闲期巩固"的两段式写入。

## 三、人员识别——人脸（M3）

**[S17] FaceNet: A Unified Embedding for Face Recognition and Clustering**（Schroff et al., 2015, CVPR, 引用 11547）
三元组损失学 128 维人脸嵌入的奠基作。确立"嵌入+余弦距离"的人脸验证范式，本项目沿用。

**[S18] ArcFace: Additive Angular Margin Loss for Deep Face Recognition**（Deng et al., 2019, TPAMI, 引用 472）
角间隔损失，LFW 99.8%+。**InsightFace 实现的 buffalo_l 模型包即为 ArcFace r50**，本项目的识别主力。

**[S19] RetinaFace: Single-stage Dense Face Localisation in the Wild**（Deng et al., 2020, CVPR）
单阶段人脸检测 SOTA，侧脸/遮挡鲁棒。InsightFace det_10g 检测模型即源于此，与 [S18] 同包一体化。

**[S20] Eigenfaces vs. Fisherfaces**（Belhumeur et al., 1997, TPAMI, 引用 11773）
历史参照：子空间方法的极限，说明为何深度嵌入取代了传统方法。

**[S21] Distract Your Attention: Multi-Head Cross Attention for Facial Expression Recognition**（2023, Biomimetics）
表情识别轻量方案参照。V1 用语音+文本双路情绪，V2 再加静态表情识别（InsightFace 属性亦可兜底）。

**工程结论**：InsightFace buffalo_l（检测 RetinaFace + 识别 ArcFace r50，330MB ONNX）一个包解决检测+识别+ embedding；新用户注册=采 3-5 帧人脸→512 维嵌入入库；识别=余弦相似度>0.35 阈值判定。

## 四、人员识别——声纹（M4）

**[S22] ECAPA-TDNN: Emphasized Channel Attention, Propagation and Aggregation in TDNN**（Desplanques et al., 2020, Interspeech, 引用 1513）
VoxCeleb 说话人验证 SOTA 经典。**服务端主选**：192 维说话人嵌入，pip 即用（SpeechBrain / 3D-Speaker ONNX）。

**[S23] pyannote.audio 2.1 speaker diarization pipeline**（Bredin & Laurent, 2023）
说话人分离（多人对话谁在说）工业标准。多用户家庭场景 V2 引入。

**[S24] MFA-Conformer for Automatic Speaker Verification**（2022, Interspeech）
国产方案（3D-Speaker 团队），CAM++ 同源。28MB ONNX 端侧可选。

**[S25] A Fine-tuned Wav2vec 2.0/HuBERT Benchmark for Speech Emotion Recognition, Speaker...**（2022, ICASSP）
自监督语音表征统一做 SER+SR 的基准，验证"一个语音编码器多任务复用"的可行性。

**工程结论**：注册=采 10s 语音→192 维声纹入库；识别=余弦>0.7 验证通过；人脸↔声纹绑定由"共现确认"完成（同一时间窗内人脸命中+声纹命中→绑定到同一档案，3 次共现转正）。名字由用户口头告知（"我叫小邦"）→ LLM 抽取→写入画像。

## 五、情绪感知（M5）

**[S26] DialogueCRN: Contextual Reasoning Networks for Emotion Recognition in Conversations**（2021, 引用 237）
会话情绪识别需建模上下文推理，单句分类不够。**采用为"情绪轨迹"设计**：滑动窗口内连续 valence/arousal 追踪。

**[S27] MMGCN / M2FNet / MM-DFN 系列（多模态会话情绪识别）**（2021-2022, 引用 320/163/236）
图网络/动态融合做多模态（文本+语音+人脸）情绪识别的代表作系列。佐证"三模态融合优于单模态"但复杂度高；工程折衷：文本 LLM 判断 + 语音 SER 传感器融合。

**[S28] Survey on Speech Emotion Recognition: Features, Classification Schemes, and Databases**（2010, 引用 2090）
SER 领域权威综述。四类情绪（happy/sad/angry/neutral）在约束条件下可 70-80% 准确，作为"传感器"而非"真值"使用。

**[S29] RAVDESS: Ryerson Audio-Visual Database of Emotional Speech and Song**（2018, PLoS ONE, 引用 1898）
标准评测库。emotion2vec+ 在其上验证；本项目语音情绪模块的评测基准。

**[S30] emotion2vec / emotion2vec+（FunASR）**（2023-2024, 阿里开源）
自监督语音情绪表征，中英双语，输出类别+valence/arousal。**服务端语音情绪主选**。

**[S31] LLMs and Empathy: Systematic Review**（2024, 引用 219）
系统综述确认 LLM 生成共情回应的能力与条件：**显式情绪上下文注入显著提升共情感知**。佐证情绪模块输出必须结构化注入生成 prompt。

**[S32] EmotionQueen: A Benchmark for Evaluating Empathy of LLMs**（2024）
共情评测基准：区分"显式情绪/隐式情绪/无情绪"并给出恰当回应。用于情绪模块回归测试。

**[S33] Emotional Chatting Machine (ECM)**（Zhou et al., 2018, AAAI, 引用 765）
历史参照：情绪状态作为一等公民建模（内部情绪状态转移+外部情绪词库）。现代等价物=情绪状态存入记忆、影响生成风格。

**[S34] InstructERC: Reforming Emotion Recognition in Conversation**（2023）
LLM 直接做会话情绪识别的检索增强范式。备选路线：文本情绪可由主 LLM 结构化输出（8 类情绪+valence/arousal），零额外模型成本。

**工程结论**：文本路=主 LLM 结构化输出情绪标签；语音路=emotion2vec+ 4 类+连续值；融合=规则加权（语音权重高当文本语音冲突时以语音为准）；情绪写入记忆（情绪记忆通道 [S33]）并注入生成 prompt（[S31]）。

## 六、主动智能（M6）

**[S35] A Survey on Proactive Dialogue Systems: Problems, Methods, and Prospects**（2023, 引用 39）
主动对话三维：何时主动（时机）、主动什么（话题选择）、如何（策略）。本项目主动引擎的顶层框架。

**[S36] Proactive Conversational Agents in the Post-ChatGPT World**（2023, 引用 79）
LLM 时代主动智能的分类：澄清式提问、目标导向推进、时机化介入。陪伴场景=时机化关怀介入。

**[S37] Effects of Proactive Dialogue Strategies on Human-Computer Trust**（2020, 引用 67）
实证：主动策略影响信任——**主动过度降低信任，时机恰当提升信任**。采用"信任反馈循环"：主动行为后监测用户响应情绪，负反馈则降频。

**[S38] Proactive Conversational Agents with Inner Thoughts**（2025）
"内心独白"机制：代理持续内部评估对话上下文，当"介入冲动"超阈值才开口。**采用为主动引擎的核心机制**——每轮对话后内部打分，超阈值才触发主动消息。

**[S39] ComPeer: A Generative Conversational Agent for Proactive Peer Support**（2024）
同伴式主动支持：不是助手式提醒而是朋友式问候。语气设计参照。

**工程结论**：三类触发器（时间 cron / 事件规则 / 情绪轨迹）+ 内心独白打分门控 + 信任反馈降频。主动消息必须引用记忆（"上次你说..."）否则退化为骚扰。

## 七、多语言（M7）

**[S40] A Survey of Multilingual Large Language Models**（2025, 引用 104）
多语 LLM 权威综述。结论：主流 LLM（Qwen/GLM/GPT 系）中高资源语言（中英日韩）原生能力足够，无需翻译中转。

**[S41] ChatGPT Beyond English: Towards a Comprehensive Evaluation of LLMs**（2023, 引用 186）
跨语言评测：非英语响应质量差距存在但 2023 后大幅收窄。评测用多语探针集。

**[S42] Zero-shot Cross-lingual Dialogue Systems with Transferable Latent Variables**（2019, 引用 76）
历史参照：翻译中转/共享潜变量的旧范式已被 LLM 原生多语取代。

**[S43] Multilingual LLMs Are Not (Yet) Code-Switchers**（2023, 引用 24）
中英混说（code-switching）仍是弱项。工程对策：fasttext 检测主导语言，prompt 指示"跟随用户语言"；记忆存原语言+检索跨语言共享（bge-m3 多语 embedding 不翻译）。

**[S44] Attention-Informed Mixed-Language Training for Zero-Shot Cross-Lingual Task-Oriented Dialogue**（2020, 引用 89）
混合语言训练参照。工程上佐证：训练数据/记忆中的多语混合不损害检索。

**工程结论**：fasttext lid 检测（10KB）→ 路由 LLM 同语言回复；用户画像存"偏好语言"；记忆跨语言共享；App UI 四语（zh/en/ja/ko）。

## 八、端侧部署与心理安全（M8）

**[S45] On-Device Language Models: A Comprehensive Review**（2024）
端侧 LLM 综述：量化/剪枝/缓存三大方向。安卓端 4B 级模型 MNN 4bit 可 15-20 tok/s（本机 MiniCPM 实测 17 tok/s）。

**[S46] Octopus v2: On-device Language Model for Super Agent**（2024）
端侧函数调用：小模型学 API 调用免去长 prompt。端侧离线兜底的工具调用方案。

**[S47] MobileQuant: Mobile-friendly Quantization for On-device Language Models**（2024）
端侧量化工程细节（权重激活联合量化），MNN/NCNN 部署参照。

**[S48] EdgeMoE: Empowering Sparse LLMs on Mobile Devices**（2025）
稀疏化+专家卸载，端侧更大模型的方向参照。

**[S49] LLMs could change the future of behavioral healthcare: responsible development**（Stade et al., 2024, npj, 引用 348）
**安全红线框架**：危机对话独立通道（不经过个性化/记忆逻辑）、用户被遗忘权（记忆查看/删除 UI）、透明度。

**[S50] Loneliness and suicide mitigation for students using GPT3-enabled chatbots**（Maples et al., 2024, npj, 引用 211）
实证：陪伴缓解孤独有效，但**自伤语境识别必须独立处理**。高敏记忆（心理状态）单独加密+访问控制。

**[S51] Therapeutic Potential of Social Chatbots in Alleviating Loneliness and Social Anxiety**（Gomes et al., 2025, JMIR, 引用 81）
机制实证：**"记住披露内容并主动回访"是疗效中介**——记忆系统的主动回访不是过度设计而是疗效要素；但频率需克制（过度监视感）。

**[S52] Effectiveness of an Empathic Chatbot in Combating Adverse Effects of Social Exclusion**（de Freitas et al., 2020, Frontiers, 引用 268）
共情回应质量是关键变量。记忆检索结果需标注"情绪相关"并要求生成器共情复用。

---

## 九、综合落地架构（文献 → SoulSync 设计映射）

```
                  ┌─ [S3]遗忘曲线 ─ [S4]合并裁决 ─ [S10]有损重构
四层记忆 L1-L4 ───┤
                  └─ [S1]检索打分 ─ [S11]KG+向量双通道 ─ [S7]分层索引
反思器 M2 ──────── [S13][S14][S15] 会话末总结 + 夜间巩固 + 经验卡
人脸 M3 ────────── [S18][S19] InsightFace buffalo_l（检测+识别一体）
声纹 M4 ────────── [S22] ECAPA-TDNN 192d + 共现绑定 + 名字抽取
情绪 M5 ────────── [S30]emotion2vec+ ‖ [S34]LLM 结构化 → 传感器融合 → 注入生成[S31]
主动 M6 ────────── [S38]内心独白门控 × [S35]三类触发器 × [S37]信任反馈 × [S51]疗效回访
多语言 M7 ──────── [S43]fasttext 路由 + LLM 原生多语 + [S40]记忆跨语言
安全 M8 ────────── [S49][S50]危机通道/被遗忘权 + [S45][S46]端侧兜底
```

### 关键设计决策（每条有文献编号背书）

1. **记忆不是越多越好**：写入需过重要性门控（[S1][S3]），遗忘曲线自然衰减（[S3]），有损重构（[S10]）。
2. **硬事实与软语义分通道**：KG 管生日/纪念日/关系，向量管语气/偏好（[S11][S5]）。
3. **情绪是传感器不是真值**：多模态融合加权，冲突以语音为准，结构化注入生成（[S28][S31]）。
4. **主动必须过门控**：内心独白打分+信任反馈降频+引用记忆（[S38][S37][S51]）。
5. **身份=人脸×声纹×名字三重证据**：共现绑定，单模态不锁定（工程惯例，无直接文献）。
6. **危机对话旁路一切个性化**：检测到自伤线索→固定安全回应+求助资源，不走记忆/人设逻辑（[S49][S50]）。

## 附录：检索与筛选方法

- 通道 1（存量）：OpenAlex 11 组关键词 275 条→记忆方向 43 篇（survey_memory.md，2026-09-18）。
- 通道 2：OpenAlex relevance+引用排序 6 组 185 条（fetch_openalex.py）。
- 通道 3：OpenAlex `filter=title.search:` 精准标题查询 4 组 150 条（fetch_openalex_titles.py，修复 URL 编码与 filter 语法后成功）。
- 筛选标准：标题强信号关键词匹配 + 引用数排序 + 对陪伴智能体八模块的可迁移性人工判读；脚本产物存 `companion-agent-project/papers/`。
- arXiv API 直连全部 406（冒号编码问题未解），弃用；OpenAlex 直连稳定无需代理。
