# Data 目录说明

本项目数据目录：大体积数据（快照 / 预测时间线等）由 `.gitignore` 排除、仅本地保留；赛程归档、训练状态、数据分层 manifest 等关键样例入库。

## 子目录

```
data/
├── raw/         # 早期原始爬虫 JSON（本地）
├── processed/   # 早期清洗后宽表 CSV（本地）
├── analysis/    # 分析宽表样例（本地）
├── realtime/    # 现行实时链路数据：快照 / frames / 预测 / 数据集分层（见 realtime/README.md）
└── meta/        # 本地映射表（如 rune_dict.json；缺省时界面显示「待映射」）
```

## 数据获取方式

```bash
# 1. 验证官方接口连通性
python scripts/01api.py

# 2. 赛程归档 → 历史数据集 → clean / quarantine 分层
python scripts/build_schedule_archive.py
python scripts/build_history_dataset.py
python scripts/classify_realtime_battles.py --materialize

# 3. 实时采集（常驻；自动识别对局并异步预测）
python scripts/official_match_monitor.py --interval 3
```

## 数据来源声明

数据来自腾讯王者荣耀职业联赛官方公开接口，**仅用于个人学习项目**，不做商业用途、不传播。
