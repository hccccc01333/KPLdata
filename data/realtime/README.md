# Realtime Data

实时采集链路产生的数据（官方赛程 / 对局 / 局内快照 / 预测）。

## 本地保留（不入库）

- `raw_snapshots/`：每次轮询的原始 JSON 响应（每 battle 一个目录）
- `frames/`：高频采集（0.1s）逐帧 CSV
- `predictions/`：实时胜率 CSV（每 battle 一条秒级时间线）
- `backup_snapshots/`：手工备份
- `logs/`：监控常驻日志 `monitor_YYYYMMDD.log`

## 入库关键样例

- `schedule_archive.csv`：跨赛季赛程索引
- `train_status.json`：最近一次训练状态与 Holdout 指标
- `datasets/`：`catalog.json` 与 clean / quarantine manifest
- `model_select_v11_report.json`、`ablation_v11_report.json`、`backtest_v9_report.json`、`diagnose_*.json`：模型选型 / 消融 / 回测 / 坏局诊断样例

## Important

Do not overwrite snapshots from the same battle. Realtime modeling depends on preserving the full time series.
