# TeleScope 项目设计报告

> 版本：v0.1（初稿）　日期：2026-09-01　状态：待评审
> 定位：基于大模型的国际新闻监控与国际形势分析简报系统

---

## 1. 项目概述

### 1.1 背景与定位

TeleScope 是一个面向国际政治、经济、外交关系、科技与社会变化领域的**新闻监控与情报分析工具**。系统从国内外公开可获取的新闻渠道持续采集内容，经多语言处理、去重聚类、热点筛选后，由大模型（LLM）驱动的多智能体流水线生成结构化分析简报。

核心价值主张：
- **从"信息过载"到"决策可用"**：每日数千条新闻 → 一份可溯源的热点简报；
- **多源多极视角对冲**：同时纳入西方、中国、区域第三方媒体，降低单一叙事偏差；
- **一切结论可溯源**：每条分析结论均强制挂接原文引用（citations），杜绝无据推断；
- **节奏化产出**：每日简报 / 每周深度研判 / 每月总结，符合情报周期（intelligence cycle）惯例。

### 1.2 目标用户

| 用户 | 场景 |
|---|---|
| 国际关系研究者/学生 | 快速掌握每日热点、追溯事件脉络、获取文献级引用 |
| 智库/咨询分析师 | 周报月报素材库、地区/产业/军事专题底稿 |
| 企业战略/风控人员 | 海外政治风险、供应链产业动态监测 |
| 个人重度国际新闻读者 | 定制化多源简报替代手工刷多个网站 |

### 1.3 设计总原则

1. **遵循 12-Factor Agents**（humanlayer/12-factor-agents）：智能体是"主要由确定性软件组成、在关键节点 sprinkling LLM"的微智能体（micro-agent），而非"提示词 + 工具袋 + 无限循环"。
2. **引用优先**：任何分析输出必须携带来源链路，不可溯源的结论一律拒收。
3. **源即配置**：新闻源全部数据化、可增删、可配置权重与调度，不硬编码。
4. **多语言一等公民**：中/英/日/俄/阿/法/西等语言在采集、聚类、分析全链路支持。
5. **成本可控**：LLM 调用分级（粗筛便宜模型 → 精析强模型），非 LLM 的确定性步骤（去重、实体抽取初筛）优先。

---

## 2. 调研综述

### 2.1 典型产品与平台参考

**（A）商业媒体情报平台**

| 产品 | 核心机制 | 对 TeleScope 的启示 |
|---|---|---|
| **Factiva（道琼斯）** | 全球权威媒体库 + 精细元数据（公司/人物/行业/地区标签）+ 布尔检索与监测 | 元数据体系（source、region、topic、entity 多维标签）是情报平台的骨架 |
| **LexisNexis Newsdesk** | 新闻+社交媒体监测、情感分析、监测主题配置 | "监测主题（watchlist）"应为一等配置对象，用户可自定义关注实体 |
| **Feedly** | RSS 聚合 + AI（Leo）主题训练、优先级排序、团队情报板 | AI 筛选器的"训练-反馈"闭环：用户对筛选结果的纠正应回流为 few-shot/规则 |
| **Inoreader** | 极强定制化 RSS（规则过滤、监控关键词、订阅上限数千） | 规则引擎（关键词过滤/屏蔽/加权）用确定性代码而非 LLM 实现 |
| **Dataminr** | 实时事件检测与预警，AI 从海量公开信号中提取"最早预警" | 事件（event）而非文章（article）才是监测的基本单位；重要性分级 |
| **Recorded Future / Palantir** | 实体-事件知识图谱、多源融合、时序分析 | 实体图谱（国家/人物/组织/事件）支撑"关系变化规律研判"类分析 |

**（B）开放/学术数据平台**

| 平台 | 说明 | 用法 |
|---|---|---|
| **GDELT 2.0** | 全球新闻事件数据库：100+ 语种监测（65 语种实时机器翻译）、每 15 分钟更新、CAMEO 事件编码、免费 API（DOC API / Events / GKG） | 事件层补充源与热度信号；跨语言线索发现 |
| **ACLED** | 240+ 国家/地区政治暴力与抗议事件数据（actor、event type、location、fatalities），含 CAST 预测；研究用途注册免费 | 军事/冲突类周报与月报的结构化底座 |
| **ICG CrisisWatch** | 国际危机组织月度全球冲突追踪与预警（提供 RSS） | 每月形势总结的高质量基准参考源 |
| **ReliefWeb API v2** | 联合国人道主义事务厅全球危机/灾害信息 API | 人道危机维度补充 |
| **SIPRI** | 军费支出数据库（1949–2025）、军火工业数据库 | 国家军事战略与能力分析的结构化数据 |
| **IISS Military Balance(+)** | 170+ 国武装力量、装备、防务经济年度评估 | 同上，作为权威基线 |
| **UN Comtrade / 世界银行 WDI** | 国际贸易商品级统计、宏观指标，免费 API | 产业与经济领域分析的量化底座 |

**（C）技术生态参考**

- **RSSHub**：开源自托管 RSS 生成器，可为无 RSS 的站点（如参考消息、财新部分栏目）生成订阅源 → TeleScope 采集层的兜底方案。
- **Google News RSS**：支持 topic/region/keyword 参数化订阅，多语言多地区聚合的轻量入口。
- **Common Crawl CC-NEWS**：1000+ 站点、约 5 万篇/日的 WARC 新闻数据集 → 可选的批量回填与语料来源。
- **跨语言新闻聚类研究**（Event Registry、multilingual streaming clustering 等）：基于多语言嵌入向量 + 近邻聚类做跨语言事件归并，是业界成熟做法。

### 2.2 关键设计启示

1. **文章 → 事件 → 主题 → 简报** 的四级抽象是媒体情报系统的通用范式（Factiva/GDELT/Event Registry 皆如此）。
2. **RSS 已萎缩但未死**：Reuters 已于 2020 年关闭官方 RSS、AP 不再提供，而 BBC/卫报/NYT/Al Jazeera/Nikkei/SCMP/中新网等仍提供；**采集层必须多协议**（RSS/Atom + 站点适配 + 聚合器 RSS + API）。
3. **重要性判断 = 信号叠加**：来源权重 × 报道源数量（扩散度）× 事件严重度 × 时效衰减，而非单纯 LLM 打分。
4. **商业平台的护城河在元数据与回溯语料**，TeleScope 应从第一天就把"保留原始快照 + 结构化元数据"作为数据纪律。
5. **AI 筛选必须有人机反馈回路**（Feedly Leo 模式），否则筛选质量无法持续校准。

---

## 3. 需求分析

### 3.1 功能需求

**F1 每日：新闻简报生成**
- F1.1 按调度（默认每日 07:00 本地时间）聚合过去 24h 新闻；
- F1.2 热点筛选：按主题（政治/经济/外交/军事/科技/社会）与重要性评分取 Top N；
- F1.3 生成结构化日报：头条要闻（3–5 条）+ 分类速览 + 每条含 2–4 句摘要、影响初判、原文链接；
- F1.4 输出 Markdown / HTML /（可选）PDF，支持推送（本地文件 / Webhook / IM）。

**F2 每日：重要新闻事件溯源**
- F2.0 【核心】对**单个新闻事件**，追溯其与历史库中**既往新闻事件的联系**：找出前因、演进、回应、同行为体、同议题平行等关联事件，判定联系类型与方向，构成可引用的**事件谱系（Event Lineage）**；
- F2.1 联系判定必须可解释、可验证：每条"事件A ↔ 事件B 有联系"的结论均附证据引语（quote_span）与置信度；
- F2.2 溯源结果渲染为时间线 + 关系图（背景 → 演进 → 当前），每个节点挂原文引用；
- F2.3 触发方式：自动（每日简报中 severity ≥ 阈值的事件）/ 人工（指定事件或关键词）/ API；
- F2.4 溯源产出的"事件-事件"联系沉淀为长期事件图谱，供每周 F3.6 国际关系规律研判复用；
- F2.5 无充分证据时输出"孤立/新发事件"结论，**禁止强行关联**（防幻觉铁律）。

**F3 每周：专题研判**
- F3.1 热点地区分析（按地区聚合：中东、东欧、亚太……）；
- F3.2 政治热点国家/地区排行与解读；
- F3.3 热点经济领域分析（能源、半导体、粮食、金融……）；
- F3.4 国家产业分析（指定国家的重点产业动态）；
- F3.5 国家军事战略与能力分析（结合 ACLED/SIPRI/IISS 结构化数据）；
- F3.6 国际关系变化规律研判（实体对关系事件时序：合作/冲突事件比率、基调变化）。

**F4 每月：总结**
- F4.1 产业发展分析月度总结（行业主题聚合 + Comtrade/WDI 量化锚点）；
- F4.2 国际热点形势总结（本月 Top 事件回顾、趋势判断、下月展望）。

**F5 新闻源管理与配置**
- F5.1 源的增删改查：名称、URL、类型（rss/html/api）、语言、地区、意识形态视角标签、权重、抓取频率、解析器、启用状态；
- F5.2 源健康监控：成功率、延迟、去重率，异常告警；
- F5.3 配置热更新：改配置无需重启流水线（配置外置于数据库/文件）。

**F6 通用横切需求**
- F6.1 多语言：采集与摘要输出语言解耦（输出默认中文，可配英文）；
- F6.2 全文检索：按关键词/实体/时间/来源/主题组合查询历史库；
- F6.3 引用与审计：简报每条结论可点击回溯至原文快照与所在段落；
- F6.4 人机协同：筛选结果可人工标注（采纳/误报/漏报），反馈回流。

### 3.2 非功能需求

| 维度 | 要求 |
|---|---|
| 可靠性 | 单源失败不阻断流水线；LLM 调用重试+降级；每日简报按时产出（SLA 99%） |
| 可审计 | 保留原始快照、每步 LLM 输入输出、评分依据 |
| 可扩展 | 新增源/新分析主题不改核心代码；分析器插件化 |
| 成本 | 粗筛用低成本模型/规则，仅 Top 事件进强模型；批量嵌入本地计算 |
| 合规 | 尊重 robots.txt 与站点条款；仅存储摘要+链接+必要片段供分析，快照内部留存；输出注明出处 |
| 可恢复 | 流水线任意步骤可暂停/重跑（幂等） |

---

## 4. 功能设计

### 4.1 每日简报流水线（时序）

```
06:00 采集窗口聚合（滚动24h）
  ↓ 规范化 + 语言检测 + 去重（URL规范化/SimHash/跨语言嵌入聚类）
  ↓ 实体识别与富化（国家/人物/组织/主题标签，确定性词典优先，LLM 兜底）
  ↓ 事件聚类归并（同事件多语言多源合并 → Event）
  ↓ 热点评分（来源权重 × 源扩散度 × 严重度 × 时效衰减）
  ↓ LLM 粗筛（低档模型：主题相关性 + 重要性分档，结构化输出）
  ↓ Top N 进入精析（强模型：摘要/影响初判/关键引语，附 citations）
  ↓ 简报渲染（模板 + 引用锚点）→ 发布
  ↓ 高分事件自动触发"溯源子流水线"（F2）
```

### 4.2 周报/月报生成策略

- **素材复用**：周报 = 本周日报 Event 库 + 结构化数据锚点（ACLED 周统计、Comtrade 快照）聚合，而非重新爬取；
- **分析器插件化**：每个专题（F3.1–F3.6）是一个独立 Analyzer Agent，输入为"周期事件集 + 实体图谱切片 + 量化数据"，输出结构化章节；
- **规律研判方法**（F3.6 示例）：对国家对 (A,B) 拉取周期内 CAMEO/GDELT 风格事件序列 → 统计合作型/冲突型事件比、基调（tone）滑动均值 → LLM 仅负责"解读趋势 + 归因候选"，数字由代码算出。

### 4.3 事件溯源引擎设计（F2 核心：单事件 → 历史事件联系）

**问题定义**：给定当前新闻事件 `E_t`（含聚类文章、实体、主题、时间、地点），从历史事件库中检索与其存在真实联系的既往事件 `{E_1..E_n}`，判定每对 `(E_i → E_t)` 的**联系类型与方向**，输出可引用的事件谱系（lineage graph）。

#### 4.3.1 四阶段流水线：召回（确定性）→ 精判（LLM）→ 谱系构建 → 沉淀

**Stage 1 混合召回（纯代码，不调 LLM）**

| 召回通道 | 方法 | 候选量 |
|---|---|---|
| 向量召回 | 事件标题+摘要的多语言嵌入 kNN（pgvector） | top 50 |
| 实体召回 | 共享 ≥1 关键实体（国家/人物/组织）的事件，图谱查询 | top 50 |
| 主题召回 | 同 topic + 同地区窗口内事件 | top 30 |
| 时间窗 | 默认 180 天，可配 30/90/180/365 | 过滤 |

合并去重后按**关联度初分**排序取 top 20 进入精判：

```
rel(E_i, E_t) = w1·ent_jaccard      // 关键实体 Jaccard 重合
              + w2·cos(emb_i, emb_t) // 事件嵌入相似度
              + w3·time_decay(Δt)    // 时间邻近衰减
              + w4·geo_match         // 地理重合
              + w5·topic_match       // 主题重合
```

**Stage 2 联系精判（EventTracer Agent，小而专注）**

- 输入：目标事件卡 + top-K 候选事件卡（各含多源交叉摘要、关键引语、实体列表）；
- LLM 只做一件事：**判定两事件之间的联系**，不生成新事实；
- 输出结构化（Pydantic 校验）：

```json
{
  "relations": [
    {
      "prior_event": "E_12",
      "target_event": "E_t",
      "type": "causal | escalation | de_escalation | response | background | same_actor | thematic_parallel",
      "narrative": "一句话说明两者如何联系",
      "evidence": [{"article_id": 123, "quote_span": "原文引语"}],
      "confidence": 0.82
    }
  ],
  "isolated": false,
  "gaps": ["可能遗漏的前因线索提示"]
}
```

联系类型字典（可配置扩展）：

| type | 含义 | 示例 |
|---|---|---|
| causal | 前因触发 | 制裁决议 → 被制裁方反制 |
| escalation | 冲突/态势升级 | 交火 → 空袭 |
| de_escalation | 态势缓和 | 停火协议签署 |
| response | 政策/行动回应 | 演习 → 外交抗议 |
| background | 背景脉络 | 长期领土争议 |
| same_actor | 同一行为体关联 | 同一领导人既往动作 |
| thematic_parallel | 同议题平行事件 | 他国同类立法 |

**Stage 3 谱系构建与渲染**

- 节点 = 事件（日期、标题、来源数、严重度）；边 = 联系（类型、方向、证据、置信度）；
- 渲染产物：时间线视图 + Mermaid 关系图 + 文字叙述（背景 → 演进 → 当前）；
- 每个节点/边均挂 `[n]` 引用锚，渲染期校验 quote_span 存在于原文快照。

**Stage 4 沉淀入图谱**

- 联系写入 `event_relations` 表（auto 生成）；置信度 < 阈值者进入人工复核队列；
- 事件图谱随时间累积，成为 F3.6 国际关系规律研判（实体对事件时序统计）的数据底座。

#### 4.3.2 置信度分层与防幻觉

| 级别 | 条件 | 处置 |
|---|---|---|
| 高 | ≥2 独立来源支持同一联系叙述 | 直接入谱系 |
| 中 | 1 来源 + 强实体/时间信号 | 入谱系，标注"待复核" |
| 低 | 仅语义相似 | 标注"疑似"，进人工复核队列 |
| 无 | 召回为空或证据不足 | 输出"孤立/新发事件"，**禁止强行关联** |

#### 4.3.3 边界情况

- **冷启动**：历史库空/浅时明确输出"历史窗口内无关联事件"，不编造；可选触发定向回填（GDELT 历史查询该实体/主题）；
- **实体消歧**：同名人物/机构用别名表 + 时间上下文消歧，不确定时降低置信度而非猜测；
- **联系方向**：因果类联系要求时间先后（E_i 早于 E_t），违反者降级为 thematic_parallel；
- **评估**：小规模人工标注集上计算 precision@k 与"重要前因遗漏率"，纳入 Reviewer 质检。

---

## 5. 模块与组件设计

```
┌──────────────────────────────────────────────────────────┐
│                      接入层 (Triggers)                     │
│        cron 调度 · CLI 手动触发 · Webhook · 未来:IM bot    │
├──────────────────────────────────────────────────────────┤
│ 采集层 Collectors（每源一 worker，多协议）                 │
│   RSS/Atom · HTML适配器 · Google News RSS · RSSHub桥      │
│   商业API适配器(NewsData等,可选) · GDELT/ACLED/ReliefWeb  │
├──────────────────────────────────────────────────────────┤
│ 处理层 Pipeline（确定性为主）                              │
│   规范化 → 语言检测 → 去重 → 跨语言事件聚类 → 实体富化     │
│   → 热点评分引擎（信号叠加，可配置权重）                    │
├──────────────────────────────────────────────────────────┤
│ 智能体层 Agents（小而专注的微智能体）                      │
│   Screener(粗筛) · Summarizer · EventTracer(溯源)         │
│   RegionalAnalyst · EconSectorAnalyst · IndustryAnalyst   │
│   MilitaryAnalyst · IRPatternAnalyst · MonthlySynthesizer │
│   BriefRenderer(模板渲染,非LLM) · Reviewer(质检)           │
├──────────────────────────────────────────────────────────┤
│ 支撑层                                                     │
│   配置中心(源/主题/调度) · 任务队列 · 状态存储(执行态+业务态)│
│   向量+全文检索 · 原文快照库 · 引用服务 · 人机反馈通道      │
├──────────────────────────────────────────────────────────┤
│ 输出层                                                     │
│   Markdown/HTML/PDF · 本地目录 · Web UI(检索与简报浏览)    │
│   Webhook/IM 推送 · OPML 导入导出                          │
└──────────────────────────────────────────────────────────┘
```

各智能体职责边界（小而专注）：

| Agent | 输入 | 输出（结构化） | 模型档位 |
|---|---|---|---|
| Screener | 文章/事件卡片批 | `{id, relevant, topic, severity, reason}` | 低 |
| Summarizer | 单事件多源摘要串 | `{headline, summary, impact, key_quotes[], citations[]}` | 高 |
| EventTracer（溯源） | 目标事件 + 混合召回的候选历史事件集 | `{relations[{prior, type, narrative, evidence[], confidence}], isolated, gaps[]}` | 高 |
| Regional/行业/军事 Analyst | 周期事件聚合 + 量化锚点 | 章节结构体 + citations | 高 |
| IRPatternAnalyst | 实体对事件序列统计 | 趋势解读 + 归因假设（标注推测性） | 高 |
| Reviewer | 简报草稿 | `{issues[], missing_citations[], verdict}` | 中 |

---

## 6. 架构设计

### 6.1 多智能体编排原则

- 编排器（Orchestrator）是**确定性代码**（Python 函数/DAG），不把控制流交给 LLM；
- 每个 Agent 是**无状态纯函数**：`(context, tools) → (output, new_state)`，可单测、可重放；
- Agent 间通过**结构化消息（typed event/action）**通信，全部落库。

### 6.2 12-Factor Agents 映射

| # | Factor | TeleScope 落地方式 |
|---|---|---|
| 1 | Natural Language → Tool Calls | Agent 仅以结构化 JSON（Pydantic schema）输出动作/结论，调度代码执行工具 |
| 2 | Own your prompts | 提示词为版本化文件 `prompts/*.md.j2`，入库 git 管理，带语义版本号与变更记录 |
| 3 | Own your context window | 每个 Agent 显式构造上下文：任务卡 + 精选素材 + 评级规则 + few-shot，不用"聊天历史"当上下文 |
| 4 | Tools are structured outputs | 工具=注册函数（检索/取快照/查ACLED），参数与返回均为 schema 校验的结构体 |
| 5 | Unify execution & business state | 单一状态库（Postgres）既存任务执行态也存业务数据（事件/简报），用 `runs/steps` 表追踪 |
| 6 | Launch/Pause/Resume | 流水线步骤幂等 + 检查点（每步完成即持久化），任意步骤可暂停恢复重跑 |
| 7 | Contact humans via tool calls | `request_review()` 作为工具：简报产出后挂起等待人工采纳/修正，反馈写回标注库 |
| 8 | Own your control flow | 编排用显式代码（DAG），LLM 只在节点内做判断，不做路径决策 |
| 9 | Compact errors into context | 采集/解析/LLM 失败压缩为 `error_card`（类型+摘要+重试策略）注入上下文，而非原始 traceback |
| 10 | Small, focused agents | 上表 8 个窄职责 Agent，每个单测覆盖；禁止"万能分析 Agent" |
| 11 | Trigger from anywhere | 触发器抽象：cron / CLI / Webhook / （规划）IM，产出统一 `run_request` 事件 |
| 12 | Stateless reducer | Agent 不持内存态；"记忆"= 从库中检索重构的上下文，重放同输入必得同输出（温度置 0 或记录 seed） |

### 6.3 部署形态（演进）

- **单机 MVP**：Python + SQLite/Postgres + APScheduler + 本地 `.md` 输出；
- **V1**：Docker Compose（Postgres+pgvector / worker / scheduler / Web UI）；
- **V2**：队列化（Redis/RQ 或 Celery）水平扩展采集与分析 worker。

---

## 7. 数据管理方案

### 7.1 存储选型

| 存储 | 用途 |
|---|---|
| PostgreSQL（+pgvector） | 业务主库：源、文章、事件、实体、简报、运行状态、嵌入向量 |
| 对象存储/本地卷 | 原文 HTML/AMP 快照、图片、PDF 附件 |
| 全文检索 | Postgres FTS（中英分词）起步；量大后接 Meilisearch/ES |
| 缓存/队列 | Redis（去重布隆、任务队列、源健康计数） |

### 7.2 核心数据模型（简化 ER）

```
sources(id, name, url, type[rss|html|api|gnews|rsshub], language, region,
        perspective_tag, weight, fetch_interval, parser, enabled, health_json)

articles(id, source_id FK, url, url_hash, title, title_trans, content_text,
         lang, published_at, fetched_at, snapshot_path, embeddings vector,
         dedup_key, raw_meta jsonb)
         UNIQUE(url_hash), INDEX(dedup_key), INDEX(published_at)

events(id, title, title_zh, summary, category, severity, first_seen, last_seen,
       article_count, source_count, score, status)
event_articles(event_id FK, article_id FK, relation[origin|followup])

entities(id, type[country|person|org|topic|industry], canonical_name, aliases[])
event_entities(event_id, entity_id, role[actor|target|location|topic])

-- F2 事件溯源：单事件与历史事件的联系（事件谱系边表）
event_relations(id, prior_event_id FK, target_event_id FK,
                type[causal|escalation|de_escalation|response|background|same_actor|thematic_parallel],
                narrative, evidence jsonb,          -- [{article_id, quote_span}]
                confidence, created_by[auto|human], reviewed bool, created_at)
                UNIQUE(prior_event_id, target_event_id, type)

analyses(id, kind[daily|weekly|monthly|trace|regional|...], target_ref,
         period_start, period_end, model, prompt_version, output jsonb, status)

briefs(id, date, kind, title, body_md, body_html, analysis_id FK, published_at)
citations(id, brief_id, article_id, quote_span, url, verified)

runs(id, kind, trigger, status, created_at, checkpoint jsonb)
steps(id, run_id, agent, input_digest, output_ref, error_card, started_at, ended_at)

feedback(id, article_id|brief_id, action[accept|false_positive|miss], note, user)
```

### 7.3 数据生命周期

| 数据 | 在线保留 | 归档策略 |
|---|---|---|
| 原文快照 | 90 天热 | 之后压缩归档；仅保留标题/摘要/URL/元数据 |
| 嵌入向量 | 长期（事件级） | 文章级向量随快照归档 |
| 事件/实体/简报 | 永久 | — |
| 运行日志 steps | 30 天 | 聚合指标留存 |

### 7.4 溯源设计

- 简报中每个论断渲染为 `[n]` 引用锚，`citations` 表存 `article_id + 原文引语 span + URL`；
- 渲染期自动校验：引用 span 必须存在于快照文本中，校验失败则该结论标记"低置信"或剔除（Reviewer Agent 复核）。

---

## 8. 新闻源初选清单（v0）

> 原则：多极视角平衡（美欧 / 中 / 区域第三方 / 南方国家）；官方通讯社优先（事实层）；分析类媒体单独标注（观点层）；付费墙内容仅取标题+摘要做线索。

### 8.1 国际通讯社 / 综合媒体（事实层，权重高）

| 源 | 语言 | 获取方式 | 备注 |
|---|---|---|---|
| Reuters 路透 | EN | 官方 RSS 已停（2020）；经 Google News RSS / RSSHub 桥接 | 事实基准源 |
| AP 美联社 | EN | 官方 RSS 已停；Google News RSS / 第三方生成 | 同上 |
| AFP 法新 | FR/EN | Google News RSS 桥接 / RSSHub | — |
| BBC News | EN | 官方 RSS（feeds.bbci.co.uk） | 分频道订阅 |
| The Guardian | EN | 官方 RSS | world/politics/business 分频道 |
| New York Times | EN | 官方 RSS（nytimes.com/rss） | 摘要级 |
| Al Jazeera 半岛 | EN/AR | 官方 RSS | 中东视角 |
| DW 德国之声 | DE/EN/CN | 官方 RSS | 含中文版 |
| France 24 | FR/EN | 官方 RSS | — |
| CNN / WSJ / WP / FT / Bloomberg / Economist | EN | RSS 部分/桥接；付费内容仅线索 | 观点+财经 |

### 8.2 区域与多极视角（降低单一叙事偏差）

| 源 | 地区 | 获取 |
|---|---|---|
| SCMP 南华早报 | 香港/亚洲 | 官方 RSS（scmp.com/rss） |
| Nikkei Asia 日经亚洲 | 日本/亚太 | 官方 RSS（asia.nikkei.com/rss） |
| The Straits Times 海峡时报 | 新加坡/东南亚 | 官方 RSS |
| The Diplomat | 亚太外交 | RSS |
| Asia Times | 亚洲 | RSS |
| Times of India / Hindustan Times | 南亚 | RSS |
| RT / TASS（俄） | 俄罗斯视角 | RSS（标注：国家媒体，观点权重低、线索用） |
| Global Times 环球时报英文 | 中国视角 | 站点/桥接（同上标注） |
| Daily Sabah / Al Arabiya / Times of Israel | 中东多方 | RSS |
| Anadolu / African Arguments / Mail & Guardian | 非洲/南方 | RSS |

### 8.3 财经 / 科技 / 产业

FT、Bloomberg、Reuters Business、WSJ Tech、Nikkei、Caixin 财新、SCMP Tech、Ars Technica/The Verge（科技产业）、IEA/OPEC 报告 RSS（能源）、WTO/IMF/世界银行新闻（机构层）。

### 8.4 中文源

| 源 | 获取 | 备注 |
|---|---|---|
| 新华社（中文/英文） | 英文版提供 RSS；中文经桥接 | 官方通讯社 |
| 中新网 | 官方 RSS（chinanews.com.cn/rss/scroll-news.xml 等） | 官方通讯社 |
| 人民网/环球网/中国日报 | RSS/桥接 | 官方媒体 |
| 参考消息 | 无官方 RSS → RSSHub 路由 | 外媒编译，高价值对冲源 |
| 财新 | RSSHub（付费墙内容仅标题线索） | 财经深度 |
| 澎湃新闻/界面/南方周末 | RSSHub | 市场化媒体 |
| 求是网/瞭望 | 桥接 | 政策风向参考 |

### 8.5 结构化数据 / 事件数据 API

| 源 | 类型 | 接入 |
|---|---|---|
| GDELT 2.0（DOC/Events/GKG） | 事件+语调，100+语种/15min | 免费 API，配额轮询 |
| ACLED | 冲突/抗议事件 | 注册 key，周级拉取 |
| ReliefWeb API v2 | 人道危机更新 | 免费 API |
| Google News RSS（多语言多地区实例） | 聚合入口 | hl/gl/ceid 参数化 |
| UN Comtrade / 世界银行 WDI | 贸易与宏观 | 免费 key |
| SIPRI Milex / Arms Industry | 军费与军工业 | 数据集下载 |
| IISS Military Balance（公开摘要） | 军力基线 | 网页/RSS 线索 |
| 商业 News API（NewsData.io / NewsCatcher / GNews） | 备选补充 | 付费/免费额度，按需 |

### 8.6 智库与深度分析（观点层，周/月报素材）

ICG（CrisisWatch，RSS）、CSIS、RAND、Brookings、Chatham House、Lowy Institute（The Interpreter）、War on the Rocks、Carnegie、MERICS、SIPRI/IISS 评论。

> 源清单将以 `config/sources.yaml` 落地（含上述字段），并支持 OPML 导入。首版目标：**60–80 个有效源，覆盖 12+ 语种、6 大区域**。

---

## 9. 技术选型建议

| 层 | 选型（MVP 优先） |
|---|---|
| 语言 | Python 3.12 |
| 采集 | feedparser + httpx + trafilatura（正文抽取）+ tenacity 重试 |
| 多语言 | lingua/fasttext 语言检测；多语言嵌入（bge-m3 / multilingual-e5，本地推理） |
| LLM | 提供商抽象层（OpenAI 兼容接口），支持本地/云切换；结构化输出用 Pydantic + JSON schema |
| 调度 | APScheduler（MVP）→ Celery/Redis（V1） |
| 存储 | Postgres 16 + pgvector；对象存储本地卷起步 |
| Web/检索 | FastAPI + Jinja2（V1）；Meilisearch（V2 可选） |
| 渲染 | Jinja2 模板 → Markdown/HTML；weasyprint（PDF 可选） |
| 可观测 | structlog + 每步 error_card；runs/steps 表即审计日志 |

---

## 10. 实施路线图

**M0（1–2 周）骨架**
- 仓库/CI/AGENTS.md；`sources.yaml` 20 个核心 RSS；采集→去重→落库→日简报（Screener+Summarizer+模板）端到端跑通；每日 07:00 定时产出 `briefs/YYYY-MM-DD.md`。

**M1（3–6 周）核心闭环**
- 事件聚类+热点评分；引用锚与校验；EventTracer 溯源；源管理 CRUD + 健康监控；人机反馈标注回流。

**M2（6–10 周）周/月报**
- 六类周报 Analyzer；GDELT/ACLED/Comtrade 接入；月度总结；Web UI（检索+简报浏览+源配置）。

**M3（10 周+）增强**
- 实体图谱可视化；关系规律时序统计；多输出渠道（IM/Webhook/PDF）；OPML 导入导出；回填（CC-NEWS/GDELT 历史）。

---

## 11. 风险与合规

| 风险 | 缓解 |
|---|---|
| 版权/ToS | 尊重 robots.txt；不全文转售；简报以摘要+链接+短引语（合理引用）形式；付费墙仅存线索；快照仅内部留存并限期 |
| RSS 源失效/反爬 | 多协议适配层 + RSSHub 兜底 + 源健康监控自动降权/告警 |
| LLM 幻觉 | 强制引用校验；数字与统计由代码计算；Reviewer 质检；推测性结论显式标注 |
| 叙事偏差 | 源 `perspective_tag` 显式标注，简报展示视角分布；多极源配额 |
| 成本失控 | 分级模型策略；批次化；缓存（同事件不重复精析） |
| 法律敏感 | 输出仅基于公开信息；不提供行动建议级结论；免责声明 |

---

## 12. 参考资料

- 12-Factor Agents: https://github.com/humanlayer/12-factor-agents
- GDELT: https://www.gdeltproject.org/ ；ACLED: https://acleddata.com/
- ReliefWeb API: https://apidoc.reliefweb.int/ ；ICG RSS: https://www.crisisgroup.org/rss-0
- SIPRI: https://www.sipri.org/databases/milex ；IISS: https://www.iiss.org/publications/the-military-balance/
- RSSHub: https://github.com/DIYgod/RSSHub ；Google News RSS 参数: https://www.newscatcherapi.com/blog-posts/google-news-rss-search-parameters
- Reuters RSS 停服背景: https://www.fivefilters.org/2021/reuters-rss-feeds/
- 参考产品：Factiva / LexisNexis Newsdesk / Feedly / Inoreader / Dataminr 官网
