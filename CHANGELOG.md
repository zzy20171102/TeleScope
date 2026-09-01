# 更新记录（Changelog）

格式参考 Keep a Changelog；版本号遵循语义化版本。

## [0.3.0] - 2026-09-01

### Added — M0.5 LLM 接入（MiniMax 实测通过）

- **密钥安全管理**：`.env`（已 gitignore，永不入库）+ `.env.example` 模板；`config.load_env_file()` 自动加载且不覆盖已有环境变量；`get_backend()` 二次保障加载。
- **MiniMax 兼容适配**（`api.minimax.cn/v1` / `minimax-m3`）：
  - `<think>...</think>` 推理段宽容剥离（m3 特性）；
  - markdown 代码围栏剥离 + 首尾大括号定位的 `extract_json()`；
  - `response_format` 被拒时自动降级重试；
  - `reasoning_content` 字段兜底。
- **连通性测试脚本** `scripts/llm_check.py`：key 掩码显示（`sk-cp-9L...K0xI`）、`--pipeline` 一键联动全流程。
- **Live 测试** `tests/test_llm_live.py`（默认跳过，`TELESCOPE_LLM_LIVE=1` 启用）。
- **离线测试密封性**：端到端单测强制规则后端（空 key 环境变量覆盖 .env），避免单测触网。

### Verified — 真实数据端到端

- 20 源全部抓取成功 → 805 篇文章入库 → 157 事件聚类 → Top 6 LLM 分析
- 产出 `briefs/2026-09-01.md`：中文标题、跨语言摘要（英文源→中文简报）、推测性影响标注（"可能/或"）、引用锚点 `[n]` 与来源列表
- 回归：26 测试全绿（24 离线 + 2 live 跳过）

### Known Issues → M1

- 严重度规则误触发（低重要性事件获高分混入头条）；聚类纯度不足（无关文章混入）；个别 LLM 调用超时静默降级规则模式。详见 `PLAN.md` M1 清单。

## [0.2.0] - 2026-09-01

### Added — M0 骨架（端到端可运行）

- **项目脚手架**：`pyproject.toml`（Python ≥3.10，核心零第三方依赖）、`.gitignore`、`README.md`。
- **新闻源配置**：`config/sources.yaml` 首批 20 源（BBC/卫报/NYT/半岛/DW/法国24/NPR/SCMP/日经/外交官/Global Voices/中新网×2 + Google News 桥接路透/AP/新华/环球/财新），含语言/地区/视角/权重字段，多极视角标注。
- **采集层**：RSS 2.0 / Atom / RDF 三协议统一解析器；`urllib` 抓取（UA/超时/重试）；URL 规范化（剔除 utm 等追踪参数）；语言启发式检测（中/日/韩/俄/阿/英）；内置 35+ 国家与组织中英实体词典。
- **处理层**：URL SHA-256 哈希去重 + 批内标题模糊去重（difflib）；在线贪心事件聚类（实体 Jaccard / 标题 token Jaccard，72h 窗口）；热点评分（来源权重 × 扩散度 × 体量 × 严重度 × 时效衰减）。
- **存储层**：SQLite（sources/articles/events/event_articles/entities/briefs/runs/steps 全套表）；文章按 url_hash 幂等入库；运行审计。
- **智能体层（12-Factor 落地）**：LLM 后端抽象——`RuleBackend`（离线确定性规则，默认）与 `OpenAICompatBackend`（环境变量配置，JSON 结构化输出）；Screener / Summarizer 两个小而专注的智能体，提示词版本化于 `prompts/*.md.j2`，异常自动降级规则模式并记录 error_card。
- **输出层**：每日简报 Markdown 渲染（头条要闻 + 分类速览 + 引用锚点 `[n]` 与来源列表）；`briefs/YYYY-MM-DD.md` 落盘。
- **编排与 CLI**：确定性 DAG 编排器 `run_daily`（采集→去重→落库→聚类→评分→筛选→摘要→渲染，全程 runs/steps 审计）；CLI：`run / fetch / sources / stats`。
- **测试**：24 个离线单测（yaml 解析/规范化/去重/聚类/评分/存储/RSS 三协议/渲染/端到端注入），`python -m unittest` 全绿。

## [0.1.0] - 2026-09-01

### Added — 设计基线

- `docs/DESIGN.md`：项目设计报告 v0.1（需求/功能/模块/架构/12-Factor 映射/数据管理/60+ 新闻源初选清单）。
- F2 事件溯源核心设计细化：单事件 → 历史事件联系（四阶段流水线 + `event_relations` 模型）。
- `AGENTS.md`：项目记忆文件（架构铁律/业务铁律/术语表/开发约定）。
