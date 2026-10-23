# 峡谷有数 · KPL Insight

**一个从赛事数据采集、整理，到查询、实时胜率预测和赛后复盘的 KPL 开源项目。**

峡谷有数把公开赛事数据整理成可查询、可对比的产品：先看赛程与比分，再了解战队、选手和英雄表现；比赛日跟踪局内状态，赛后利用已有快照做数据复盘。项目由个人持续开发，欢迎观众使用，也欢迎开发者交流和改进。

本仓库负责**数据与模型**；已经存在的 [KPLdata-site](https://github.com/hccccc01333/KPLdata-site) 负责**静态网站**。普通用户可以直接浏览静态站，不需要安装训练环境或准备模型。

[打开静态网站](https://hccccc01333.github.io/KPLdata-site/) · [下载静态站体验包](https://github.com/hccccc01333/kpl-insight/releases/download/static-site-20261023/kpl-insight-static-20261023.zip) · [反馈与交流](https://github.com/hccccc01333/kpl-insight/issues) · [参与贡献](CONTRIBUTING.md)

> **访问说明**：静态网站部署在 GitHub Pages；另有 [Workers 备用地址](https://kpldata-site.hccccc01333.workers.dev)，后者在部分网络下需要代理。在线站点可用性受网络影响；访问不通时，可以使用随项目提供的静态站体验包。包内已有网页、字体和展示数据，核心查询与复盘图表通过本机加载，不依赖海外站点；第三方图片和原始比赛录像仍需联网。

## 项目能做什么

### 1. 查赛程、比分与历史比赛

从赛事与赛季开始，查看赛程、比赛结果、系列赛进程，再进入单局详情。历史归档覆盖 2019–2026，便于查询当届比赛和回看以往赛季。

### 2. 看战队、选手和英雄数据

查看战队表现、交手记录、选手统计与英雄池、英雄选禁及组合数据；按赛季、位置和对手做对比。先找到对象和样本范围，再看具体指标。

### 3. 跟踪实时胜率，做赛后数据复盘

比赛日采集局内快照并估算实时胜率；在已有分钟快照的对局中，联动查看胜率、经济、击杀、推塔、资源和选手表现。支持区分比赛当时保存的预测与赛后模型重放。静态体验包只能回看其内含数据，不会自行采集直播或训练模型。

### 4. 更多分析工具

在这些基础能力之外，还提供 BP 分析与逐手回放、系列赛研究、对比与找局、大场模拟、胜率沙盘等工具。它们用于补充分析与探索，不能替代原始比赛录像或保证预测结果。

## 怎么体验

**普通观众：直接用已有静态站，或下载体验包。**

1. 先打开 [GitHub Pages 静态网站](https://hccccc01333.github.io/KPLdata-site/)。
2. 如果页面访问不通，使用[静态站体验包](https://github.com/hccccc01333/kpl-insight/releases/download/static-site-20261023/kpl-insight-static-20261023.zip)：完整解压后，在 Windows 双击 **启动网站.bat**，浏览器会自动打开本地网站。无需 Python、Node、模型或管理员权限；使用时保留启动窗口，关闭该窗口即可停止。包也可作为附件转发给无法访问 GitHub 的用户。
3. 体验包是 **2026-10-23 的固定快照**，不会自动更新。macOS / Linux 或已有 Python 的用户，可在包内 `site` 目录运行下方命令。

```bash
python3 -m http.server 8000 --bind 127.0.0.1
```

浏览器打开 `http://127.0.0.1:8000`。也可直接下载[站点仓库](https://github.com/hccccc01333/KPLdata-site)中的 HTML 与 `assets/` 自行预览。不要直接双击 HTML，部分比赛数据需要通过本地 HTTP 加载。

**开发者：从 GitHub 上的数据仓或站点仓开始。** 本仓库负责数据采集、特征、训练、回测和 Streamlit 工作台；站点仓负责界面与静态数据构建。体验包已有展示数据，但数据仓库不包含完整采集快照和预训练模型；训练复现需要另外准备合规数据。选择自己关心的一侧即可。

## 开发者从哪里开始

本仓训练与验证环境按 `.python-version` 和 `requirements.txt` 锁定为 Python 3.14。推荐先阅读[复现说明](REPRODUCIBILITY.md)，在虚拟环境中安装依赖。

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS / Linux: source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/check_env.py
python -m compileall -q scripts
```

只有在准备好有权使用、符合输入格式的数据后，再运行训练与工作台：

```bash
python scripts/train_realtime_model_v9.py
python scripts/backtest_realtime_v9.py --gates
streamlit run scripts/dashboard.py
```

核心入口：

- `scripts/official_match_monitor.py`：比赛日监控、快照采集与预测。
- `scripts/kpl_official_core.py`：统一解析、因果特征、预测与复盘逻辑。
- `scripts/train_realtime_model_v9.py`：当前 V12 训练流程，文件名保留旧版本号以兼容现有产物。
- `scripts/backtest_realtime_v9.py`：独立测试集评估与门禁。
- `scripts/regression_replay_vs_live.py`：直播记录与当前模型重放的偏差检查。
- `scripts/dashboard.py`：内部 Streamlit 数据工作台。

## 数据与模型，先知道这些

- **历史覆盖**：公开赛事归档覆盖 2019–2026。站点构建资产在 2026-10-23 的快照为 33 个赛事、2,901 场大场、11,138 局小局；有分钟快照的复盘覆盖 65 场、222 局。**历史赛果数量与可做分钟复盘的数量不同**，这些数字会随数据更新改变。
- **模型版本**：实时胜率模型为 V12，采用按时间、按整局分开的 train / calibrate / test。模型版本与站点产品版本分别维护。
- **评估范围**：已归档独立测试报告为 20 局、298 个时点，Brier 约 0.177、方向准确率约 71.8%。这是特定样本上的历史结果；样本量有限，早期翻盘局仍有明显问题，不能据此承诺未来比赛表现。报告见 [`backtest_v9_report.json`](data/realtime/backtest_v9_report.json)。
- **复现条件**：仓库不包含完整赛事快照与预训练模型；缺少数据时，部分工作台功能会为空或无法运行。详见[复现说明](REPRODUCIBILITY.md)。
- **仍在研究**：第一视角视频解析尚未完成真实验收，不能作为稳定的选手轨迹分析功能使用。

## 希望和你一起改进什么

如果你是观众，欢迎描述一次具体体验：想查什么、在哪一步没找到、希望看到怎样的对比。截图、页面地址和比赛信息会让反馈更容易复现。

如果你是开发者，欢迎从一个范围明确的问题开始：

- **数据正确性**：换边后的胜负归属、缺失字段、重复记录、跨页口径一致性。
- **模型评估**：时间泄漏、概率校准、翻盘样本、直播与回放偏差。
- **产品体验**：比赛检索、复盘交互、手机布局、解释是否容易理解。
- **工程与文档**：可复现步骤、边界测试、异常提示，以及更可靠的访问和部署方案。

欢迎通过 Issue 交流，或提交一个只解决一件事的 PR。请附上复现过程、数据范围和验证结果；具体要求见[贡献指南](CONTRIBUTING.md)。不需要先做一个“大功能”，清楚指出一个问题同样有价值。

## 许可与来源

原创代码和文档采用 [MIT License](LICENSE)。本项目为非官方个人项目，与腾讯及 KPL 官方无关联。

赛事信息来自腾讯 KPL 公开赛事接口；商标、接口服务、比赛数据、图片及其他第三方资源仍归相应权利人所有，不随本仓 MIT 许可一并授权。模型输出用于学习、分析和复盘参考。
