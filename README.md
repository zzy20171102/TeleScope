# TeleScope

> 基于大模型的多语言国际新闻监控与国际形势分析简报系统。

TeleScope 从国内外公开新闻渠道持续采集内容，经多语言处理、去重聚类、热点筛选后，由 LLM 多智能体流水线生成可溯源的分析简报：

- **每日**：新闻简报 + 重要新闻事件溯源（单事件 → 历史事件联系）
- **每周**：热点地区 / 政治热点国家 / 经济领域 / 国家产业 / 军事战略能力 / 国际关系规律研判
- **每月**：产业发展总结 + 国际热点形势总结

设计遵循 [12-Factor Agents](https://github.com/humanlayer/12-factor-agents) 原则：确定性编排、小而专注的无状态智能体、结构化输入输出、提示词版本化、执行态与业务态统一存储。

## 快速开始

```bash
# 无任何第三方依赖（Python >= 3.10）
python -m telescope run              # 采集→去重→聚类→评分→筛选→摘要→引用校验→事件溯源→简报，输出 briefs/YYYY-MM-DD.md
python -m telescope fetch            # 仅采集入库
python -m telescope sources          # 源列表 ｜ add / enable / disable 管理源（写回 sources.yaml）
python -m telescope sources check    # 逐源健康探测（结果入库 sources.health_json）
python -m telescope stats            # 查看库内统计
python -m telescope feedback add --kind event_relation --target 5 --rating reject --note "误关联"
                                     # 人机反馈：confirm/reject 直接回写谱系复核状态
python -m telescope schedule install # 注册 Windows 每日 07:00 计划任务（remove/show 同入口）
python -m unittest discover -s tests # 运行离线测试（68 个，2 个 live 默认跳过）
```

### 启用 LLM（可选，已实测 MiniMax）

默认使用内置**规则后端**（离线、确定性）。两种配置方式：

```bash
# 方式一：项目根目录 .env（已 gitignore，推荐；从 .env.example 复制）
TELESCOPE_LLM_API_KEY=sk-...
TELESCOPE_LLM_BASE_URL=https://api.minimax.cn/v1
TELESCOPE_LLM_MODEL=minimax-m3

# 方式二：系统环境变量（优先级高于 .env）
```

已验证：MiniMax `minimax-m3`（含 `<think>` 推理段容错解析）；任意 OpenAI 兼容端点均可。

```bash
# LLM 连通性检查（key 掩码显示）
python -X utf8 scripts/llm_check.py
# 检查 + 联动全流程
python -X utf8 scripts/llm_check.py --pipeline
# live 测试（显式启用）
TELESCOPE_LLM_LIVE=1 python -X utf8 -m unittest tests.test_llm_live
```

LLM 调用失败自动降级规则模式，并在 `steps` 表记录 error_card（Factor 9）。

简报渲染前经 **Reviewer 确定性引用校验**：关键引文必须在文章原文快照中逐字命中
（容忍大小写/空白/中英引号差异），未命中即剔除并将该条目降级为低置信（⚠️ 引用待核）；
通过校验的 citation（article_id + span + URL）写入 `citations` 表。

简报头部条目还附带 **事件溯源（F2）**：对头条事件从历史事件库混合召回候选
（实体/词法/主题/时间窗），由 EventTracer 判定七类联系（前因/升级/缓和/回应/
背景/同一行为体/同题平行）；每条联系必须有逐字命中原文的证据 span，否则丢弃；
结果渲染为时间线 + Mermaid 谱系并沉淀 `event_relations` 表（置信度 <0.7 标注待复核，
无关联时明确输出"孤立/新发事件"，禁止强行关联）。

## 目录结构

```
config/sources.yaml   # 新闻源配置（单一事实来源）
prompts/              # 版本化提示词模板
telescope/
  collectors/         # RSS/Atom/RDF 采集
  pipeline/           # 规范化/去重/聚类/评分/引用校验/溯源召回
  agents/             # LLM 后端 + Screener/Summarizer/Reviewer/EventTracer
  render/             # 简报渲染
  storage.py          # SQLite 存储与审计
  orchestrator.py     # 确定性 DAG 编排
  cli.py              # 命令行入口
tests/                # 离线单元测试 + live 测试
scripts/llm_check.py  # LLM 连通性检查
briefs/               # 简报输出
docs/DESIGN.md        # 设计报告
PLAN.md               # 实施计划与执行记录
```

## 文档

- [设计报告](docs/DESIGN.md)：需求 / 功能 / 架构（12-Factor 映射）/ 数据管理 / 新闻源清单
- [实施计划](PLAN.md)：里程碑看板、执行记录与 M1 已知问题
- [AGENTS.md](AGENTS.md)：项目记忆（架构与业务铁律）
