# Reproducibility / 复现说明

仓库主要公开采集、建模、回测和 Dashboard 代码；**不包含完整赛事快照和已训练模型文件**。没有合法获取的数据时，不应期待复现 README 中的历史评估指标。

## 本地准备

建议在 Python 虚拟环境、仓库根目录执行：

```bash
python -m pip install -r requirements.txt
python -m compileall -q scripts
```

第二条仅检查源文件语法，不代表训练和实时接口验证通过。依赖采用最低版本约束，尚未固定完整环境。

## 需要数据之后才能运行的流程

- 数据目录由 `scripts/kpl_official_core.py` 定义：`data/realtime/raw_snapshots/`、`data/realtime/datasets/` 等。
- 在遵守赛事数据来源的服务条款和访问规则前提下，按现有脚本采集或准备你有权使用的数据；不要公开原始接口响应。
- 在数据格式满足脚本预期后，才尝试：

```bash
python scripts/train_realtime_model_v9.py
python scripts/backtest_realtime_v9.py --gates
streamlit run scripts/dashboard.py
```

训练模型通常写入 `output/models/`，此处没有提供可直接使用的预训练模型；Dashboard 在缺少数据/模型时可能只显示空视图或无法执行部分功能。具体输入字段参见 `docs/数据字典.md` 和源码。

## 外部访问与结果限制

- 采集脚本依赖外部赛事接口，接口可用性、速率限制、访问条件及结构可能变化；本仓库不保证持续可用。
- 公开报告记录的是特定时间、样本和模型版本的历史结果，不等于在新数据上已经重新验证。
- `data/README.md` 中部分旧命令标有「待开发」，请以仓库现存脚本为准。
- 复现时请保留输入数据时间范围、划分策略、代码版本、模型哈希和评估指标口径；必要时使用不含第三方数据的合成样例。

## 授权说明

MIT 许可覆盖作者有权授权的原创软件与文档；腾讯 / KPL 商标、赛事数据、接口服务和其他第三方内容均需分别遵守权利人条款。
