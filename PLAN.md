# TeleScope 实施计划

> 本文件是项目的**执行计划与滚动看板**。每完成一项：勾选任务、在「执行记录」追加条目；
> 里程碑完成（项目大更新）时执行 `git commit` 并 `git push` 到远端。
> 设计依据：`docs/DESIGN.md`（v0.1）

## 里程碑总览

| 里程碑 | 目标 | 状态 |
|---|---|---|
| **M0 骨架** | 20 源 RSS → 去重 → 落库 → 事件聚类 → 热点评分 → 日简报端到端 | ✅ 完成 |
| **M0.5 LLM 接入** | MiniMax 后端实测、`.env` 密钥管理、容错解析、真实简报生成 | ✅ 完成 |
| **M1 核心闭环** | 筛选质量调优、引用校验、事件溯源（F2）、源管理、人机反馈 | ⬜ 进行中 |
| **M2 周/月报** | 六类周报 Analyzer、GDELT/ACLED 接入、月度总结、Web UI | ⬜ 未开始 |
| **M3 增强** | 事件图谱可视化、多渠道推送、OPML、历史回填 | ⬜ 未开始 |

## Git 规范

- 远端：`https://github.com/zzy20171102/TeleScope.git`（分支 `main`）
- Commit 格式：`<type>(<scope>): <subject>`，type ∈ feat/fix/docs/chore/test/refactor
- 推送时机：**里程碑完成或项目大更新**时 push；小步可多 commit 后一并 push
- 敏感信息（API key）不入库，一律走 `.env`（已 gitignore）+ 环境变量

---

## M0 任务清单（已完成）

| # | 任务 | 产出 | 状态 |
|---|---|---|---|
| T0.1 | 计划文件与更新记录机制 | `PLAN.md` `CHANGELOG.md` | ✅ |
| T0.2 | 项目脚手架与依赖声明 | `pyproject.toml` `.gitignore` `README.md` | ✅ |
| T0.3 | 新闻源配置（20 源，多极视角） | `config/sources.yaml` | ✅ |
| T0.4 | 数据模型（Article/Event/Brief 等） | `telescope/models.py` | ✅ |
| T0.5 | 配置加载（内置 YAML 子集解析器 + .env 加载） | `telescope/config.py` `telescope/yamlmini.py` | ✅ |
| T0.6 | RSS/Atom/RDF 采集器 + URL 规范化/语言检测/实体识别 | `telescope/collectors/rss.py` `telescope/pipeline/normalize.py` | ✅ |
| T0.7 | 去重（URL 哈希 + 标题模糊） | `telescope/pipeline/dedup.py` | ✅ |
| T0.8 | 事件在线聚类 + 热点评分 | `telescope/pipeline/cluster.py` `telescope/pipeline/scoring.py` | ✅ |
| T0.9 | SQLite 存储层（含 runs/steps 审计表） | `telescope/storage.py` | ✅ |
| T0.10 | LLM 抽象层（规则后端 + OpenAI 兼容后端）与 Screener/Summarizer 智能体 | `telescope/agents/` `prompts/` | ✅ |
| T0.11 | 简报渲染（引用锚点）+ 编排器 + CLI | `telescope/render/brief.py` `telescope/orchestrator.py` `telescope/cli.py` | ✅ |
| T0.12 | 单元测试（离线 24 个 + live 2 个） | `tests/` | ✅ |
| T0.13 | 端到端验证 + 文档更新 + git 提交推送 | 24 离线测试全绿 | ✅ |

## M0.5 任务清单（LLM 接入，已完成）

| # | 任务 | 产出 | 状态 |
|---|---|---|---|
| T0.5.1 | 密钥安全管理：`.env`（gitignore）+ `.env.example` 模板 + 自动加载 | `.env*` `config.load_env_file()` | ✅ |
| T0.5.2 | 连通性测试脚本（掩码显示 key、response_format 容错降级） | `scripts/llm_check.py` | ✅ |
| T0.5.3 | MiniMax 适配：`<think>` 推理段剥离、markdown 围栏剥离、宽容 JSON 提取 | `agents/llm.py extract_json()` | ✅ |
| T0.5.4 | 离线测试密封性：单测强制规则后端（env 覆盖 .env） | `tests/test_orchestrator.py` | ✅ |
| T0.5.5 | 真实全流程实测：20 源采集 + LLM 分析 + 简报落盘 | `briefs/2026-09-01.md` | ✅ |
| T0.5.6 | Live 测试用例（TELESCOPE_LLM_LIVE=1 启用） | `tests/test_llm_live.py` | ✅ |

## 执行记录

| 日期 | 记录 |
|---|---|
| 2026-09-01 | **M0 完成**：零第三方依赖骨架、20 源配置、采集→去重→聚类→评分→筛选→摘要→渲染端到端；24 个离线单测全绿；CLI `sources/stats` 验证通过。 |
| 2026-09-01 | **M0.5 完成**：接入 MiniMax（`api.minimax.cn/v1`，模型 `minimax-m3`）。连通性测试 PASS（HTTP 200，`response_format=json_object` 支持）；发现 m3 输出 `<think>` 推理段 → `extract_json()` 容错剥离；`.env` 密钥管理（不入库）；真实全流程：20 源 805 文章 → 157 事件 → Top6 LLM 中文简报（含翻译摘要/影响初判/引用锚点），落盘 `briefs/2026-09-01.md`；回归 26 测试全绿（2 live 跳过）。git 首次提交并推送远端。 |

## M1 已知问题（真实数据实测发现，下一步优先）

- [ ] **筛选质量**：低重要性事件混入头条（如屠宰场新闻被标"军事 1.8"）→ 严重度规则误触发 + LLM 筛选阈值需调高；标题/摘要关键词上下文窗口需收紧
- [ ] **聚类纯度**：无关文章混入同一事件（梅西退役混入拉丁美洲无关报道）→ 阈值上调 + 实体数下限
- [ ] **摘要降级**：个别事件 LLM 调用超时/失败静默回退规则模式（英文标题未翻译）→ 步骤级 error_card 已记录，需在简报头部明示降级比例
- [ ] 引用校验器（quote_span 快照校验）+ Reviewer 质检
- [ ] F2 事件溯源引擎：混合召回 + EventTracer + `event_relations` 表
- [ ] 源管理 CLI（增删改查/启停）与健康监控
- [ ] 人机反馈标注回流
