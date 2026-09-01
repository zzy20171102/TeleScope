# AGENTS.md — TeleScope 项目记忆

## 项目是什么
TeleScope：基于大模型的多语言国际新闻监控与国际形势分析简报系统。
覆盖领域：国际政治、经济、外交、军事、科技与社会变化。
核心产出：每日新闻简报+事件溯源；每周六类专题研判（热点地区/政治热点国家/经济领域/国家产业/军事战略能力/国际关系规律）；每月产业与国际形势总结。

## 关键文件索引
- `docs/DESIGN.md` — 项目设计报告（需求/功能/模块/架构/数据/源清单）
- `config/sources.yaml` — 新闻源配置（单一事实来源，勿在代码中硬编码源）
- `prompts/` — 全部 LLM 提示词（版本化模板，见 Factor 2）
- `briefs/` — 生成简报输出目录
- `PLAN.md` — 里程碑看板与执行记录（含 M1 已知问题清单）
- `.env` — LLM 密钥（gitignore，永不入库；模板见 `.env.example`）

## 架构铁律（12-Factor Agents）
1. 编排是确定性代码，LLM 只在节点内工作，不做路径决策（Factor 8）。
2. 每个智能体小而专注：Screener / Summarizer / EventTracer / 各专题 Analyst / Reviewer，禁止万能 Agent（Factor 10）。
3. 智能体是无状态纯函数，状态一律入库（SQLite runs/steps），可暂停/恢复/重放（Factor 5/6/12）。
4. 所有 LLM 输入输出结构化（dataclass/JSON 校验）（Factor 1/4）。
5. 提示词是代码：位于 `prompts/`，改提示词必须走 git 并记录版本（Factor 2）。
6. 上下文显式构造：任务卡+精选素材+规则，不用聊天历史（Factor 3）。
7. 人工介入通过 `request_review()` 工具调用实现，反馈写回 feedback 表（Factor 7）。
8. 错误压缩为 error_card 注入上下文/记录，不传原始 traceback（Factor 9）。
9. 触发器抽象统一为 run_request（cron/CLI/Webhook）（Factor 11）。

## LLM 接入约定（M0.5 实测经验）
- 后端：OpenAI 兼容协议；当前实测 MiniMax `minimax-m3`（`api.minimax.cn/v1`）。
- `minimax-m3` 会在 JSON 前输出 `<think>` 推理段 → 必须经 `agents/llm.py extract_json()` 容错解析，禁止直接 `json.loads(content)`。
- 密钥只放 `.env`（自动加载、不覆盖系统环境变量）；日志/输出中 key 一律掩码显示。
- LLM 失败自动降级 `RuleBackend`（确定性规则），降级事件记录在 `steps.error_card`。
- 离线单测必须强制规则后端：`os.environ["TELESCOPE_LLM_API_KEY"]=""`（空值优先于 .env）。

## 业务铁律
- 一切分析结论必须有 citation（article_id + 原文 span + URL），渲染期自动校验 span 存在性，失败即剔除或降级置信度。
- 数字与统计由代码计算，LLM 只负责解读；推测性结论显式标注（"可能/或"开头）。
- 新闻源须带 perspective/ideology 标签，多极视角配额，防单一叙事。
- 尊重 robots.txt 与站点条款；付费墙内容仅存标题级线索；快照内部留存限期 90 天。

## 数据模型速查
sources → articles(url_hash 唯一, entities) → events(聚类) ↔ entities；
analyses / briefs / citations；runs + steps = 执行审计。
主库：SQLite（data/telescope.db，M2 拟迁 Postgres+pgvector）。

## 术语表
- Article：单篇原文；Event：跨语言跨源聚类后的"新闻事件"；Brief：简报；
- Event Lineage（事件谱系）：单个事件与历史事件的联系图，F2 的核心产物；
- event_relations：事件-事件联系边表（type: causal/escalation/response/background/…，必附 evidence）；
- Hot Score：来源权重×扩散度×体量×严重度×时效衰减；error_card：压缩错误对象；
- extract_json：宽容 JSON 提取（剥 `<think>`/围栏）。

## 开发约定
- Python ≥3.10 核心零第三方依赖；新增依赖须说明理由并加入 pyproject extras。
- 新增新闻源 = 改 `config/sources.yaml`，不改代码。
- 新增分析主题 = 新增一个 Analyzer 插件 + 对应 prompt 模板 + 单测。
- 测试：离线单测必须可在无网环境 <1s 完成；联网测试放 `tests/test_llm_live.py` 或 `scripts/`。

## 当前状态（滚动更新）
- [x] 调研完成（商业平台/开放数据/源生态）— 2026-09-01
- [x] 设计报告 v0.1 — docs/DESIGN.md
- [x] F2 溯源核心设计细化：单事件 → 历史事件联系（四阶段流水线 + event_relations 模型）
- [x] M0 骨架：20 源 RSS → 去重 → 日简报端到端（24 离线单测全绿）
- [x] M0.5 LLM 接入：MiniMax 实测通过，真实简报落盘（805 文章/157 事件/Top6）
- [ ] M1：筛选质量调优（严重度误触发/聚类纯度）→ 引用校验 → F2 溯源 → 源管理 → 人机反馈
