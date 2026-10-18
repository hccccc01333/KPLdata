# V5 阶段一 · 统一分析事实表与指标字典规格

> **文档性质**：规格（spec）。本文只定义数据模型与指标口径，**不代表任何模型结果已经跑出**，也不宣称市场上不存在同类产品。
> **本阶段边界**：只交付本文档供评审；**不改采集 / 训练 / 站点任何代码**，不动任何页面。
> **依据**：核心仓库（KPLdata）与站点仓库（KPLdata-site）现有源码 + 2026-10-18 落盘数据的静态盘点。
> **上游文档**：[V4-产品重构路线图.md](./V4-产品重构路线图.md)（阶段一缺陷修复记录）、[00-总览与信息架构.md](./00-总览与信息架构.md)、[../数据字典.md](../数据字典.md)（字段真相源）。

---

## 0. 问题陈述：为什么必须先建这一层

V5 的目标是把已有赛事数据变成可持续产出的分析产品。但现在**同一场比赛的"事实"分散在四处，各算一套口径**：

- 站点榜单从 `data/history` 重算一遍胜率与均值；
- `data/analysis/battles.csv` 另有一套 `gold_diff / objective_diff`；
- `data/processed/battles.csv` 又是 `camp1/camp2` 宽表；
- 实时链路 `data/realtime/frames` 第三个口径。

结果是：**同一张"平均线"在不同页面数值不一致**、**KDA/经济有三处定义**、**分路字段两套编码**。不做统一事实表，往后每加一个（周最佳、战力、战术 DNA）都要再分裂一次。

因此 V5 的第一个交付不是页面，而是**事实表 + 指标字典**。

---

## 1. 前置阻塞（必须在写代码之前处理）

### B1 · 分路映射未规范化 —— 阻塞全部"同位置"类分析

**证据**：站点 [`build_replay_frames.py`](file:///d:/AI%E6%95%B0%E6%8D%AE%E5%88%86%E6%9E%90/%E9%A1%B9%E7%9B%AE%E4%BD%9C%E5%93%81%E9%9B%86/kpl-data-center-site/build_replay_frames.py) 的 `_pos_golds()` 按 `player_name` / `actual_player_name` **姓名排序**取前 5 名金币，而不是按 `position` 索引对齐。

**后果**：同位置经济曲线可能把不同位置的选手错位对齐。而"分路经济效率""同位置基准""周月最佳按实际出场位置归属"**全部建立在这个映射上**。

**要求**：事实表先落双字段 `position_desc`（官方文字：对抗路/打野/中路/发育路/游走）与 `position`（数字编码 0–4），再派生稳定的 `position_ordinal`；分钟快照的分路序列按 `ordinal` 对齐，**不按姓名字典序**。

### B2 · 分钟级覆盖率边界 —— 阻塞战术 DNA / 转折诊断 / 翻盘路径

实测（2026-10-18 落盘）：

| 指标 | 实测值 |
|---|---|
| `data/realtime/raw_snapshots` battle 目录 | **753** 个 |
| 其中含 **≥3 帧**（有可用序列） | **221** 个 |
| 其中含 **≤1 帧**（仅终局快照） | **531** 个 |
| `data/realtime/frames` CSV | 57 个，仅 **36** 个 ≥30 行 |
| 站点逐帧回放索引 | **211 局 / 62 场** |
| 全量小局 | **11,126 局** |

**结论**：分钟级样本 ≈ **221 / 11,126 = 2.0%**，且集中在 2026 年近期赛事。

**红线**：任何依赖分钟序列的指标必须携带 `coverage` 元数据（样本局数占比 + 时间范围）并在界面标注；**禁止用缺失数据填充出看似完整的曲线**；禁止把 2% 子集上的发现宣称为"全历史规律"。

---

## 2. 现状盘点：事实数据现在分散在哪

| 层 | 位置 | 内容 | 实测规模 | 覆盖面 |
|---|---|---|---|---|
| 全量历史真相源 | `data/history/{league_id}/` | `schedule.json` + `matches/` | 33 个联赛目录 | **2885 大场 / 11126 小局** |
| 扁平化宽表 | `data/processed/` | `matches / battles / players / bp .csv` | 127 场 · players 6900 行 · bp 2505 行 | 仅被 raw_snapshots 覆盖的场次 |
| 派生分析表 | `data/analysis/` | `matches / battles / teams / events .csv` | 173 场 · 690 局 · events 2836 行 | 同上，逐局字段有裁剪 |
| 实时链路 | `data/realtime/` | `raw_snapshots / frames / predictions` | 753 / 57 / 221 | 直播中与近期 |

**具体不一致清单**

1. **口径分裂**：`analysis/battles.csv` 有 `snapshot_count / has_timeline / objective_diff`；`processed/battles.csv` 是 camp1/camp2 宽表（`camp1_kill_big_dragon_num` 等 37 列）；站点另从 `history` 重算。
2. **主键不统一**：`analysis/teams.csv` 用 `(battle_id, team)`，`processed/battles.csv` 用 `battle_id` 单键，早前版本还出现过 `row`。
3. **分路两套编码**：`position`(int) 与 `position_desc`(str) 并存；且 `bp.csv` 里的 `position` 含义是**该 pick 的英雄位置**，与选手表不同义。
4. **无赛段/赛季维表**：`analysis/matches.csv` 的 `stage` 出现 `未知赛段` 占位值，跨期比较无稳定分组依据。
5. **选手/战队名未归一**：`processed/battles.csv` 里同时存在 `SYG`（缩写）与 `上海EDG.M`（全名）；`player_name` 与 `actual_player_name` 两个字段。

---

## 3. 目标：统一分析事实表（V5 分析数据层）

```
官方 JSON (data/history/*, data/realtime/raw_snapshots/*)
        │  staging（逐局规范化：编码统一、名称归一、主键统一）
        ▼
事实表 facts（5 张）          维度表 dims（战队/选手/英雄/赛段）
        │
        ▼
指标服务 metrics（唯一口径出口：registry + baseline service）
        │
        ▼
V5 用户产品（榜单 / 荣誉 / 复盘 / 对比 / 分享图）
```

拟落盘位置（供评审，不在本阶段创建）：`data/facts/*.parquet` + `config/metrics/*.json`（机器可读注册表）。

### 3.1 维度表

#### `dim_league_period`（联赛 · 赛段）

| 字段 | 类型 | 键 | 说明 |
|---|---|---|---|
| `period_id` | str | PK | 规范化赛段键，如 `20260003` |
| `league_id` | str | IDX | 官方 league_id |
| `league_name` | str | | 联赛/杯赛全名 |
| `season` | int | IDX | 自然年（2019–2026） |
| `stage` | str\|null | IDX | 标准化赛段（常规赛/季后赛/杯赛阶段）；无法判定时 **null**，不写"未知赛段" |
| `period_start` / `period_end` | date | | 赛段起止 |
| `bo_type` | int | | BO 局数 |

#### `dim_team`

| 字段 | 类型 | 键 | 说明 |
|---|---|---|---|
| `team_id` | str | PK | 官方 team_id |
| `name` | str | IDX | **规范名**（全名，如 `上海EDG.M`） |
| `alias` | list[str] | | 含缩写（`SYG`）、历史名、改名前后名 |
| `abbreviation` / `icon` | str | | |
| `active_from` / `active_to` | date\|null | | 战队存续区间（用于跨期归属判断） |

#### `dim_player`

| 字段 | 类型 | 键 | 说明 |
|---|---|---|---|
| `player_id` | str | PK | 若官方无稳定 ID，用规范化姓名哈希生成，并在别名表维护 |
| `name` | str | IDX | 规范 ID（`player_name`） |
| `alias` | list[str] | | `actual_player_name`（含战队前缀）、历史 ID、转会前后 |
| `usual_position` | str\|null | | 主页惯用位置（**仅参考**，评奖按实际出场位置，见 §5.4） |

#### `dim_hero` / `dim_rune`

- `dim_hero`：`hero_id`(PK) / `hero_name` / `position`(主分路) / `icon`
- `dim_rune`：**待建**。`数据字典` 已标 TODO：接口只给 `symbol_ids`，需先做铭文 ID→名字典。

### 3.2 事实表

#### `fact_match`（大场）

| 字段 | 类型 | 键 | 来源 |
|---|---|---|---|
| `match_id` | str | PK | `history/*/matches` |
| `league_id` / `period_id` | str | FK/IDX | |
| `date` / `start_time` | date / datetime | IDX | 榜单按 `date` 归属周期 |
| `team1_id` / `team2_id` | str | FK | 归一后的 `dim_team` |
| `bo_type` | int | | |
| `set_score` | str | | 大场比分 |
| `winner_team_id` | str\|null | | 未完赛为 null |
| `status` | str | IDX | finished / live / scheduled |

#### `fact_battle`（小局）

| 字段 | 类型 | 键 | 说明 |
|---|---|---|---|
| `battle_id` | str | PK | |
| `match_id` | str | FK/IDX | |
| `game_no` | int | | BO 内第几局 |
| `date` / `start_time` | date / datetime | IDX | 跨午夜按**赛事归属日期**（见 §5.4） |
| `team1_id` / `team2_id` | str | FK | |
| `winner_camp` / `winner_team_id` | int / str | | `1`=蓝 `2`=红 |
| `duration_sec` | float | | 原始 API 为毫秒，入表统一为**秒** |
| `snapshot_count` | int | | 该局采集到的帧数 |
| `has_timeline` | bool | IDX | 是否具备可用分钟序列（**coverage 唯一依据**） |
| `gold_diff` / `kill_diff` / `tower_diff` / `objective_diff` | int | | 终局差值（camp1 − camp2 口径，**入表时固定方向**） |
| `total_kills` / `total_towers` | int | | |

#### `fact_player_battle`（选手逐局）★ 周月荣誉与分路评分的基础表

复合主键 `(battle_id, camp, position_ordinal)`

| 字段 | 类型 | 说明 |
|---|---|---|
| `battle_id` / `camp` / `position_ordinal` | str/int/int | PK；`camp` 1/2 |
| `player_id` / `player_name` | str | FK `dim_player` |
| `team_id` / `team_name` | str | FK `dim_team` |
| `position_desc` | str | 官方文字：对抗路/打野/中路/发育路/游走 |
| `position` | int | 官方数字编码 0–4 |
| `hero_id` / `hero_name` | int/str | |
| `kill_num` / `death_num` / `assist_num` | int | |
| `kda` | float | |
| `gold` | int | 个人经济（终局） |
| `hurt_total` / `hurt_to_hero_total` | int | 总输出 / 对英雄输出 |
| `be_hurt_total` / `be_hurt_by_hero_total` | int | 总承伤 / 被英雄输出 |
| `hurt_to_hero_total_rate` / `be_hurt_by_hero_total_rate` | float | 占队伍比 |
| `participation_rate` | float | 参团率（%） |
| `mvp_score` | float | |
| `is_mvp` / `is_lose_mvp` | int | |
| `win` | int | 该选手本局胜负 |

> **保留代理边界**：`participation_rate` 只代表"团队参与代理"，**不能**宣称为支援能力；`be_hurt_*` **不能**推断开团质量或视野贡献。事实表存原字段，代理语义写在指标字典里（§4）。

#### `fact_bp_action`（BP 操作序列）

复合主键 `(battle_id, seq)`

| 字段 | 类型 | 说明 |
|---|---|---|
| `battle_id` / `seq` | str/int | PK，`seq` = `bp_list` 顺序（0–19） |
| `camp` | int | 操作阵营 |
| `is_ban_or_pick` | int | `0`=ban `1`=pick |
| `hero_id` / `hero_name` | int/str | |
| `hero_position` | int | **该 pick 的英雄位置**（与选手表 `position` 不同义，故改名） |
| `phase` | str | 阶段（一阶段 ban / 一阶段 pick / 二阶段 ban / 二阶段 pick） |

> 注：站点 [`build_bp_data.py`](file:///d:/AI%E6%95%B0%E6%8D%AE%E5%88%86%E6%9E%90/%E9%A1%B9%E7%9B%AE%E4%BD%9C%E5%93%81%E9%9B%86/kpl-data-center-site/build_bp_data.py) 目前只保留 `bp_list` 长度 ≥20 的局（实测 2505 行 / 覆盖 3416 局中的一部分）——覆盖率同样要作为元数据记录。

#### `fact_battle_minute`（分钟快照）★ 覆盖率受限表

复合主键 `(battle_id, minute)`

| 字段 | 类型 | 说明 |
|---|---|---|
| `battle_id` / `minute` | str/float | PK；`minute` 允许小数（快照时间不整分） |
| `camp1_gold` / `camp2_gold` / `gold_diff` | int | |
| `camp1_kill` / `camp2_kill` / `kill_diff` | int | |
| `camp1_tower` / `camp2_tower` / `tower_diff` | int | |
| `objective_diff` | int | 资源控制代理 |
| `status` / `win_camp` | int | |
| `camp1_win_prob` | float\|null | 来自 V12 模型；**归档时须记录 model_version** |
| `coverage_flag` | str | `timeline` / `final_only`（后者不参与时间序列分析） |

**入表前置**：分路金币序列必须按 `position_ordinal` 重建（B1），否则该表只提供队伍级差值、不提供分路级曲线。

---

## 4. 指标字典（Metric Registry）

### 4.1 注册表字段（每条指标必须齐备）

| 字段 | 含义 |
|---|---|
| `metric_id` | 稳定标识，如 `player.hero_damage_share` |
| `name_cn` | 中文名 |
| `definition` | 可复算公式（引事实表字段） |
| `unit` | 单位 / 百分比 |
| `caliber` | **口径等级**：`L1` 官方原样 / `L2` 代理 / `L3` 估算 |
| `grain` | 粒度：per-battle / per-player-battle / per-match / per-period |
| `source_facts` | 依赖的事实表与字段 |
| `window` | 统计窗口（自然周 / 自然月 / 赛段 / 赛季 / 近 N 场） |
| `min_sample` | 最低样本门槛（低于则不出正式结论） |
| `baseline_ref` | 引用的基准 id（§4.3） |
| `algo_version` | 算法版本号（权重、模型权重变更必须升版本） |
| `refresh` | 更新频率与触发条件 |
| `confidence_policy` | 是否给区间、区间方法 |
| `public` | 是否可对外展示 |

> 站点与核心仓库必须**只从注册表取口径**，不再在页面里硬编码公式。

### 4.2 本期定义的指标清单（按组）

**A · 赛事 / 对局**（全部 `L1`，`grain=per-match`）

| metric_id | 定义 | 门槛 | 备注 |
|---|---|---|---|
| `match.set_score` | 大场比分 | — | 未完赛不显示 |
| `match.win_rate` | 胜场 / 有效大场 | ≥ 30 大场 | 低于门槛显示"—/样本不足" |
| `match.recent_form` | 近 5 / 近 10 场胜负序列 | — | 标注对手强弱（§C） |

**B · 选手分路**（`L1` 原字段 + `L2` 派生，`grain=per-player-battle` → 聚合）

| metric_id | 口径 | 说明 |
|---|---|---|
| `player.kda` | L1 | (K+A)/D，D=0 按 1 计（须在定义中写死） |
| `player.gold_per_min` | L2 | gold ÷ duration_min；**仅同位置可比** |
| `player.dmg_share` | L1 | `hurt_to_hero_total_rate` |
| `player.tank_share` | L1 | `be_hurt_by_hero_total_rate` |
| `player.participation` | L2 | `participation_rate` —— **代理指标**：团队参与，非支援能力 |
| `player.mvp_score` | L1 | 官方 MVP 评分 |
| `player.death_control` | L2 | 1 − 死亡分位（同位置） |
| `player.rating` | L3 | 分路综合评分 S（§5），带不确定性区间 |

**C · 战队战力**（`L3`，`grain=per-period`）

| metric_id | 定义 | 备注 |
|---|---|---|
| `team.power` | 时间动态 Elo / Glicko 类评分，含**对手强度校正** | 需历史回测验证，不照搬论文 |
| `team.power_ci` | 评分区间 | bootstrap **按大场成组**重采样 |
| `team.trend_5` / `team.trend_10` | 近 5 / 10 场走势 | |
| `team.vs_strong` / `team.vs_weak` | 对强弱对手表现差异 | 说明"优势是否会消失" |
| `team.stability` | 局分方差 / 波动 | 周最佳战队用 |

**D · 英雄 / BP**（`L1` 统计 + `L3` 组合，`grain=per-battle`）

| metric_id | 口径 | 备注 |
|---|---|---|
| `hero.pick_rate` / `hero.ban_rate` / `hero.win_rate` | L1 | 分母 = 有 BP 记录的局 |
| `hero.pos_win_rate` | L1 | 按 `hero_position` |
| `combo.cooccur` | L1 | Support / Confidence / Lift（FP-Growth） |
| `combo.cond_win_rate` | L1 | 贝叶斯平滑后的条件胜率 |
| `combo.adjusted_synergy` | L3 | 控制可观测因素（战队/赛段/对手）后的交互项 |

> **因果红线**：`combo.adjusted_synergy` 是**关联**，不是因果。强队本身更常使用某些阵容，不得把强队效应误认为英雄协同。该指标默认不对外，先留在实验层（对应 V5 算法路线的"第四级"）。

### 4.3 基准服务（Baseline Service）

统一 `baseline_id` 枚举，**所有页面从同一份基准取值**：

| baseline_id | 范围 |
|---|---|
| `baseline.tournament` | 本届赛事全部战队 |
| `baseline.period` | 同赛段 |
| `baseline.season` | 同年度各赛事 |
| `baseline.position` | 同位置（选手指标必须用这个） |
| `baseline.opponent` | 只看相同对手 |
| `baseline.history` | 指定历史时期 |

**跨期可比性规则（强制）**：跨赛季比较**禁止**两个赛段各自 min-max 到 0–100 后直接对比。统一做法：

```
原始值 → 同赛段同位置中位数/IQR 基准 → z-score → 异常值截断 → 贝叶斯收缩 → 统一映射
```

每个页面必须展示"这条平均线来自哪个 baseline、多少样本"。

---

## 5. 分路评分模型（周月荣誉的最小可用规格）

### 5.1 可解释的基础公式

$$S_{i,r} = 50 + 10 \sum_{k=1}^{K} w_{r,k}\,\tilde{z}_{i,r,k}$$

- $i$：选手；$r$：位置；$w_{r,k}$：该位置第 $k$ 个指标的权重
- $\tilde{z}$：相对**同赛段同位置基准**、经异常值截断与样本收缩后的标准化表现
- 50 分 = 该统计范围内的基准表现，**不代表所有选手都恰好 50 分**

### 5.2 分位置评分维度

| 位置 | 评分维度（初版） |
|---|---|
| 对抗路 | 输出效率与承伤效率、经济表现、参团、死亡控制 |
| 打野 | 经济效率、击杀参与、资源控制**可观测代理**、MVP 表现 |
| 中路 | 对英雄输出、参团、经济转化、稳定性 |
| 发育路 | 输出效率、经济利用、死亡风险、后期表现 |
| 游走 | 参团、承伤、死亡控制、团队配合**可观测代理** |

### 5.3 标准化五步 + 不确定性

1. **基准**：同赛段同位置的中位数与 IQR/σ；
2. **截断**：异常值按 ±3σ 或 1%/99% 分位截断；
3. **收缩**：$n$ 局样本 $\hat z = \frac{n}{n+\lambda}\,z$（$\lambda$ 待历史数据标定），避免 3 局暴发冲榜；
4. **加权求和**：按位置权重；
5. **区间**：bootstrap **按大场成组**重采样（同场 10 人结果相关，不得独立重采样），输出评分区间与名次区间。

### 5.4 权重：本阶段不宣布权重

权重必须通过以下三步确定，并**记录版本号**：

- **历史回测**：用往年数据验证权重的稳定性；
- **冗余检查**：相关系数 > 0.8 的指标合并，避免重复计分；
- **敏感性分析**：权重 ±20% 时排名变化幅度，变化过大说明模型不可用。

**红线**：不得随手选几个权重就宣称得到"真实选手实力"。

### 5.5 荣誉规则（原样固化）

- **周榜**：北京时间周一 00:00 – 周日 23:59；**月榜**：自然月。
- **跨午夜**按**赛事归属日期**处理；同一 BO 系列不拆到不同周期。
- **五路分别评奖**，按该段**实际出场位置**（`fact_player_battle.position_ordinal`），不依赖选手主页惯用位置。
- **门槛**：最低有效局数 + 有效大场数 + 数据完整率（阈值待 Phase 2 依历史分布标定；本阶段只要求"必须存在"）。
- 样本不足 → **显示候选榜，不强行颁奖**；无比赛的周不评奖。
- **正式榜**在当期比赛结束、结果校验通过后发布；比赛期间展示"暂定排名"。
- 每期必须展示：候选人、评分公式、各项指标值、相对位置均值、评分不确定性。
- 必须形成**历史档案**（往期榜单可回溯）。

### 5.6 每周最佳战队（独立模型，非"胜率最高者"）

维度：大场表现 + 对手强度 + 局分优势 + 稳定性 + 近期状态，各自权重与门槛同样走 §5.4 的验证流程。

---

## 6. 赛季 / 赛段 / 基准 的统一定义

| 概念 | 定义 | 现存问题 |
|---|---|---|
| `season` | 自然年（2019–2026） | 无维表 |
| `league` | 联赛 / 杯赛 | 与 `league_id` 混用 |
| `period` | 赛段（常规赛 / 季后赛 / 杯赛阶段） | `stage` 存在 `未知赛段` 占位 → 需回填或置 null 并在界面显式标注"未分类" |
| `baseline` | 比较基准（§4.3） | 各页面各自 min-max |

**统一要求**：任何对外数字都要能回答——"在哪个范围、多少样本、什么位置基准、哪个算法版本上算出来的"。

---

## 7. 本阶段交付物与验收（Phase 1）

**交付物**：本文档。

**验收 = 评审通过以下 5 项**：

- [ ] 事实表清单与主键确认（5 张事实表 + 4 张维表）
- [ ] 每张表字段可追溯到现有落盘字段（附对照，`数据字典` 为字段真相源）
- [ ] 两条前置阻塞的处理方案确认：
      B1 分路映射修复方案（`position_ordinal` 对齐）· B2 覆盖率标注方案（`coverage_flag` + 界面标注）
- [ ] 指标字典的注册表字段集确认（据此可生成机器可读 registry）
- [ ] 分路评分模型的可复算方案确认（含权重验证流程，**不含具体权重数值**）

**本阶段明确不做**：任何代码改动、任何页面改动、任何"已算出结果"的宣称。

---

## 8. Phase 2 建议的首批可交付（收敛范围，不承诺全部 12 个产品）

围绕用户提出的三个拳头产品（**Power / Insight / Draft Lab**）先落最小闭环：

1. **统一基准口径**：用事实表替换站点现有分散的均值计算，先解决"同一平均线在不同页面不一致"。
2. **一期待发布的周最佳榜**：选定一个**已完赛的自然周**，产出五路候选 + 公式 + 各项指标 + 不确定性区间（可复算、可核对）。
3. **分路映射修复 + 回归验证**：按 B1 改造分路对齐，跑既有 `_regress.js` 五层离线回归确认不破坏现有页面。

分钟级依赖类产品（战术 DNA / 转折诊断 / 翻盘路径）在 **B2 覆盖率如实标注**的前提下再排期，且只对具备 `has_timeline` 的局开放入口。

---

## 9. 未决问题（留给评审）

1. `dim_player.player_id`：官方是否提供稳定选手 ID？若无，别名归一的准确率如何保证（同名/转会）？
2. `stage` 回填策略：从 `schedule.json` 联赛名与时间推断，还是留 null 并接受"未分类"？
3. 收缩系数 $\lambda$ 与异常值截断阈值：需先用历史分布标定，是否纳入 Phase 2？
4. `fact_battle_minute` 是否需要保存队伍级分路金币（依赖 B1），还是先只做队伍级差值？
5. 事实表落盘格式：Parquet（`data/facts/`）与现有 CSV 并存多久？迁移期如何避免站点双读？
