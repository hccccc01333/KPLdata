# -*- coding: utf-8 -*-
"""环境锁定自检：训练 / 发布 / CI 都应在 Python 3.14 + 锁定依赖下运行。

用法：python scripts/check_env.py
一致返回 0；解释器或关键包版本不一致返回 1。
"""
from __future__ import annotations

import importlib.metadata as md
import sys

EXPECTED = {
    "python": "3.14",
    "pandas": "3.0.2",
    "numpy": "2.4.4",
    "requests": "2.33.1",
    "scikit-learn": "1.8.0",
    "scipy": "1.17.1",
    "joblib": "1.5.3",
    "plotly": "6.7.0",
    "streamlit": "1.57.0",
}


def main() -> int:
    got = {"python": f"{sys.version_info.major}.{sys.version_info.minor}"}
    for name in EXPECTED:
        if name == "python":
            continue
        try:
            got[name] = md.version(name)
        except md.PackageNotFoundError:
            got[name] = "(未安装)"

    bad: list[str] = []
    print("环境自检：")
    for name, want in EXPECTED.items():
        have = got[name]
        ok = have == want
        print(f"  {'OK       ' if ok else 'MISMATCH '}{name}: {have}（期望 {want}）")
        if not ok:
            bad.append(name)

    if bad:
        print("\n环境不一致：" + ", ".join(bad))
        print("请使用 Python 3.14，并执行 `python -m pip install -r requirements.txt`。")
        return 1
    print("\n环境一致。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
