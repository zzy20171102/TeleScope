# TeleScope 实施计划

> 本文件是项目的**执行计划与滚动看板**。每完成一项：勾选任务、在「执行记录」追加条目；
> 里程碑完成（项目大更新）时执行 `git commit` 并 `git push` 到远端。
> 设计依据：`docs/DESIGN.md`（v0.1）

## 里程碑总览

| 里程碑 | 目标 | 状态 |
|---|---|---|
| **M0 骨架** | 20 源 RSS → 去重 → 落库 → 事件聚类 → 热点评分 → 日简报端到端 | ✅ 完成 |
| **M0.5 LLM 接入** | MiniMax 后端实测、`.env` 密钥管理、容错解析、真实简报生成 | ✅ 完成 |
| **P0 质量快修** | 聚类防漂移、关键词边界、降级透明化、JSON 三层防御 | ✅ 完成 |
| **M1 核心闭环** | 引用校验、事件溯源（F2）、源管理、人机反馈 | 🔄 进行中 |
| **M2 周/月报** | 六类周报 Analyzer、GDELT/ACLED 接入、月度总结、Web UI | ⬜ 未开始 |
| **M3 增强** | 事件图谱可视化、多渠道推送、OPML、历史回填 | ⬜ 未开始 |

## Git 规范

- 远端：`https://github.com/zzy20171102/TeleScope.git`（分支 `main`）
- Commit 格式：`<type>(<scope>): <subject>`，type ∈ feat/fix/docs/chore/test/refactor
- 推送时机：**里程碑完成或项目大更新**时 push；小步可多 commit 后一并 push
- 敏感信息（API key）不入库，一律走 `.env`（已 gitignore）+ 环境变量

---

## P0 质量快修任务清单（已完成）

| # | 任务 | 方案 | 状态 |
|---|---|---|---|
| T1.1 | 严重度/主题规则误触发 | 英文关键词词边界+后缀正则；标题命中或正文≥2关键词共现才算强信号；topic 与 severity 独立评估；筛选卡片改为 top-2 高权重文章导语（不再喂全量聚合文本） | ✅ |
| T1.2 | 聚类漂移（无关文章混入） | 反漂移三规则：强词法（tok≥0.35）/强实体（ent≥0.67 且共享实体≥2，防单实体链式合并）/组合信号（ent≥0.5 且 tok≥0.15）；SEED+累积双表征匹配 | ✅ |
| T1.3 | LLM 降级不可见 | BriefItem.mode 字段；简报头部显示"LLM 分析 x/y，规则降级 z"；逐条 ⚠️ 标注；error_card 记录真实异常 | ✅ |
| T1.4 | （实测新增）LLM 输出非法 JSON | 三层防御：严格解析 → 未转义引号状态机修复 → 严格性提示重试；screener/summarizer prompt 升级 v0.2.0 | ✅ |

## M0 任务清单（已完成）

| # | 任务 | 产出 | 状态 |
|---|---|---|---|
| T0.1 | 计划文件与更新记录机制 | `PLAN.md` `CHANGELOG.md` | ✅ |
| T0.2 | 项目脚手架与依赖声明 | `pyproject.toml` `.gitignore` `README.md` | ✅ |
| T0.3 | 新闻源配置（20 源，多极视角） | `config/sources.yaml` | ✅ |
| T0.4 | 数据模型 | `telescope/models.py` | ✅ |
| T0.5 | 配置加载（YAML 子集解析 + .env） | `telescope/config.py` `telescope/yamlmini.py` | ✅ |
| T0.6 | RSS/Atom/RDF 采集 + 规范化 | `telescope/collectors/rss.py` `telescope/pipeline/normalize.py` | ✅ |
| T0.7 | 去重 | `telescope/pipeline/dedup.py` | ✅ |
| T0.8 | 事件聚类 + 热点评分 | `telescope/pipeline/cluster.py` `telescope/pipeline/scoring.py` | ✅ |
| T0.9 | SQLite 存储层（含审计表） | `telescope/storage.py` | ✅ |
| T0.10 | LLM 抽象层 + Screener/Summarizer | `telescope/agents/` `prompts/` | ✅ |
| T0.11 | 简报渲染 + 编排器 + CLI | `telescope/render/` `orchestrator.py` `cli.py` | ✅ |
| T0.12 | 单元测试 | `tests/` | ✅ |
| T0.13 | 端到端验证 + git 提交推送 | 全绿 | ✅ |

## M0.5 任务清单（LLM 接入，已完成）

| # | 任务 | 产出 | 状态 |
|---|---|---|---|
| T0.5.1 | 密钥安全管理 | `.env`（gitignore）+ `.env.example` + 自动加载 | ✅ |
| T0.5.2 | 连通性测试脚本 | `scripts/llm_check.py` | ✅ |
| T0.5.3 | MiniMax 适配（`<think>` 剥离等） | `agents/llm.py` | ✅ |
| T0.5.4 | 离线测试密封性 | `tests/test_orchestrator.py` | ✅ |
| T0.5.5 | 真实全流程实测 | `briefs/2026-09-01.md` | ✅ |
| T0.5.6 | Live 测试用例 | `tests/test_llm_live.py` | ✅ |

## 执行记录

| 日期 | 记录 |
|---|---|
| 2026-09-01 | **M0 完成**：零依赖骨架、20 源、端到端、24 离线单测全绿。 |
| 2026-09-01 | **M0.5 完成**：MiniMax 接入实测通过；真实简报 805 文章/157 事件。 |
| 2026-09-01 | **P0 完成**：三轮真实数据迭代验证——(1) 聚类防漂移+关键词边界修复：头条从"屠宰场新闻"变为真实国际要闻（基辅连续空袭/美伊交火/以色列将领警告），聚类事件数 157→193（漂移簇被拆分）；(2) 降级透明化：头部"LLM 分析 x/y"+逐条⚠️；(3) JSON 三层防御：LLM 成功率 1/6→5/6（根因：模型偶发未转义引号）。测试 37 个全绿（新增 4 个 extract_json 修复测试）。commit + push。 |

## M1 待办（下一步）

- [ ] 引用校验器（quote_span 快照校验）+ Reviewer 质检智能体
- [ ] **F2 事件溯源引擎**（M1 主菜）：`event_relations` 表 + 混合召回 + EventTracer Agent + 时间线渲染
- [ ] 源管理 CLI（增删改查/启停/健康监控）
- [ ] 人机反馈标注回流（feedback 表 + CLI 标注命令）
- [ ] Windows 任务计划定时运行（每日 07:00）

## M1 观察项（低优先）

- severity 词表补充 "kill/kills"（"strikes kill five" 当前=1.0，应为 1.4+）
- SCO 事件英文标题（规则降级时未翻译）→ 可接受，LLM 模式正常
