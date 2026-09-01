# 更新记录（Changelog）

格式参考 Keep a Changelog；版本号遵循语义化版本。

## [0.4.0] - 2026-09-01

### Fixed — P0 质量快修（三轮真实数据迭代验证）

- **聚类防漂移（T1.2）**：`OnlineClusterer` 新增 SEED+累积双表征匹配与三规则评分——强词法（token Jaccard ≥0.35）、强实体（≥0.67 且共享实体 ≥2，防两个仅共享单一国家的不同故事链式合并，保留跨语言同事件合并）、组合信号（ent≥0.5 且 tok≥0.15）。效果：梅西退役事件不再吸入白宫/石油等无关报道，漂移簇拆分（事件数 157→193）。
- **关键词规则加固（T1.1）**：英文关键词改为词边界+复数/动词后缀正则（消灭 "war"⊂"ward" 类子串误命中）；主题/严重度判定要求标题命中或正文 ≥2 关键词共现；筛选卡片改为 top-2 高权重文章导语+其余标题列表（≤1600 字符）。效果：屠宰场新闻不再误标"军事 1.8"。
- **降级透明化（T1.3）**：`BriefItem.mode` 字段记录生成后端；简报头部显示"LLM 分析 x/y，规则降级 z"；逐条 ⚠️ 标注；summarizer 降级在 `steps.error_card` 记录真实异常（此前只记 "fallback:rule"）。
- **LLM JSON 三层防御（T1.4，实测新增）**：根因 = minimax-m3 偶发输出未转义引号的非法 JSON。修复 = ①严格解析 ②未转义引号状态机修复（`_fix_unescaped_quotes`）③附严格性提示的单次重试；prompts 升级 v0.2.0（screener 严重度校准表 + summarizer JSON 严格性铁律）。效果：LLM 成功率 1/6 → **5/6**。

### Added

- `scripts/diag_llm.py`：summarizer 失败诊断脚本（完整异常回溯）。
- `tests/test_extract_json.py`：引号修复状态机单测（4 例）。

### Verified

- 三轮真实数据对比（同日）：
  - 头条质量：屠宰场新闻 → 基辅连续六日空袭（12死，9源）/美伊交火/以色列将领警告，全中文深度摘要；
  - LLM 成功率：5/6 → 1/6（暴露 JSON 缺陷）→ **5/6**（修复后）；
  - 测试：37 个全绿（24→33→37）。

## [0.3.0] - 2026-09-01

### Added — M0.5 LLM 接入（MiniMax 实测通过）

- **密钥安全管理**：`.env`（已 gitignore，永不入库）+ `.env.example` 模板；`config.load_env_file()` 自动加载且不覆盖已有环境变量；`get_backend()` 二次保障加载。
- **MiniMax 兼容适配**（`api.minimax.cn/v1` / `minimax-m3`）：`<think>` 推理段剥离；markdown 围栏剥离；`response_format` 被拒自动降级重试；`reasoning_content` 兜底。
- **连通性测试脚本** `scripts/llm_check.py`：key 掩码显示、`--pipeline` 一键联动全流程。
- **Live 测试** `tests/test_llm_live.py`（默认跳过，`TELESCOPE_LLM_LIVE=1` 启用）。
- **离线测试密封性**：端到端单测强制规则后端。

### Verified — 真实数据端到端

- 20 源 → 805 篇文章 → 157 事件 → Top 6 LLM 分析 → `briefs/2026-09-01.md`（跨语言摘要、推测性标注、引用锚点）。
- 回归：26 测试全绿。

## [0.2.0] - 2026-09-01

### Added — M0 骨架（端到端可运行）

- 项目脚手架（Python ≥3.10 零第三方依赖）、20 源多极视角配置、RSS/Atom/RDF 三协议采集、URL/语言/实体规范化、双层去重、在线事件聚类、热点评分、SQLite 全套表（含 runs/steps 审计）、规则+OpenAI 兼容双后端、简报渲染（引用锚点）、确定性 DAG 编排、CLI 四命令、24 个离线单测。

## [0.1.0] - 2026-09-01

### Added — 设计基线

- `docs/DESIGN.md` 设计报告 v0.1（需求/功能/模块/架构/12-Factor 映射/数据管理/60+ 新闻源初选清单）。
- F2 事件溯源核心设计细化：单事件 → 历史事件联系（四阶段流水线 + `event_relations` 模型）。
- `AGENTS.md` 项目记忆文件。
