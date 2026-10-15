"""
回补缺失结果的对局（胜方未采集）

场景：采集在比赛结束前中断，某对局的 raw_snapshots 里没有任何
``status=2`` 且带 ``win_camp`` 的最终帧，导致分析表中 winner 为空
（旧逻辑会把双方都记成负场 → 积分榜/胜率全部偏低）。

做法：
1. 扫描 data/realtime/raw_snapshots/*：找出所有快照均不含最终结果的对局；
2. 对每个 battle_id 调官方接口拉取最新帧（fetch_freshest_battle），
   校验 battle_id 一致、``status=2``、``win_camp ∈ {1,2}``；
3. 将整包原始响应按采集时间戳写入该对局的快照目录（与监控脚本同格式）。

之后运行 ``python scripts/build_history_dataset.py`` 重建分析表即可。

运行：
    python scripts/repair_missing_results.py --dry-run
    python scripts/repair_missing_results.py
    python scripts/repair_missing_results.py --sleep 0.8 --limit 50
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

from kpl_official_core import RAW_DIR, fetch_freshest_battle, load_battle_jsons


def _camp_team(camp: Any) -> str:
    if isinstance(camp, dict):
        for key in ("team_name", "team", "name"):
            if camp.get(key):
                return str(camp[key])
    return "?"


def has_final_result(snapshots: list[dict]) -> bool:
    return any(
        int(s.get("status", 0) or 0) == 2 and int(s.get("win_camp", 0) or 0) in (1, 2)
        for s in snapshots
    )


def scan_missing() -> list[str]:
    missing: list[str] = []
    for d in sorted(p for p in RAW_DIR.iterdir() if p.is_dir()):
        snapshots = load_battle_jsons(d)
        if not snapshots or not has_final_result(snapshots):
            missing.append(d.name)
    return missing


def save_final_payload(battle_id: str, raw: dict) -> Path:
    d = RAW_DIR / battle_id
    d.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
    path = d / f"{stamp}.json"
    path.write_text(json.dumps(raw, ensure_ascii=False), encoding="utf-8")
    return path


def main() -> None:
    ap = argparse.ArgumentParser(description="Refetch final frames for battles with missing results")
    ap.add_argument("--dry-run", action="store_true", help="只扫描不请求接口")
    ap.add_argument("--sleep", type=float, default=0.6, help="每次请求间隔秒")
    ap.add_argument("--limit", type=int, default=0, help="最多处理多少个（0=全部）")
    args = ap.parse_args()

    missing = scan_missing()
    print(f"扫描完成：{len(missing)} 个对局缺少最终结果")
    if args.dry_run or not missing:
        for b in missing:
            print("  -", b)
        return

    todo = missing[: args.limit] if args.limit else missing
    ok = fail = 0
    for i, bid in enumerate(todo, 1):
        try:
            raw = fetch_freshest_battle(bid, n_probes=3, gap_sec=0.3)
            d = (raw or {}).get("data") or {}
            same_id = str(d.get("battle_id") or "") == bid
            status = int(d.get("status", 0) or 0)
            win_camp = int(d.get("win_camp", 0) or 0)
            if same_id and status == 2 and win_camp in (1, 2):
                path = save_final_payload(bid, raw)
                ok += 1
                print(f"[{i}/{len(todo)}] {bid} -> win_camp={win_camp} "
                      f"({_camp_team(d.get('camp1'))} vs {_camp_team(d.get('camp2'))}) -> {path.name}")
            else:
                fail += 1
                print(f"[{i}/{len(todo)}] {bid} -> 仍无结果 (status={status} win_camp={win_camp} same_id={same_id})")
        except Exception as e:
            fail += 1
            print(f"[{i}/{len(todo)}] {bid} -> ERROR {type(e).__name__}: {str(e)[:100]}")
        time.sleep(max(0.0, args.sleep))

    print(f"\n处理完成：成功 {ok} / 失败 {fail} / 总计 {len(todo)}")
    if ok:
        print("下一步：python scripts/build_history_dataset.py  重建分析表")


if __name__ == "__main__":
    main()
