# -*- coding: utf-8 -*-
"""监视数据变化并自动重建网站数据（比赛日配合监控脚本使用）。

监视：训练状态 / 监控状态 / 分析宽表 / 历史回补目录。
检测到变化后，重跑网站侧构建脚本（../kpl-data-center-site/）。

用法：
  python watch_site_data.py --once            检查一次，有变化就重建（默认全量）
  python watch_site_data.py --once --quick    只重建当前赛季数据（比赛日高频用）
  python watch_site_data.py                   常驻，每 60 秒检查一次
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SITE = PROJECT_ROOT.parent / "kpl-data-center-site"
STATE_PATH = PROJECT_ROOT / "data" / "realtime" / "site_watch_state.json"

WATCH_PATHS = [
    PROJECT_ROOT / "data" / "realtime" / "train_status.json",
    PROJECT_ROOT / "data" / "analysis" / "battles.csv",
    PROJECT_ROOT / "data" / "analysis" / "matches.csv",
    PROJECT_ROOT / "data" / "history" / "leagues.json",
    PROJECT_ROOT / "data" / "realtime" / "site_live_history.json",
]

BUILD_FULL = ["build_data.py", "build_history_data.py", "build_game_details.py", "build_player_details.py"]
# 比赛日快速链路：局列表/对局详情/比分 ~1 分钟内更新（曲线详情等低频项走 --full）
BUILD_QUICK = ["build_history_data.py", "build_game_details.py", "build_predict_data.py",
               "build_search_index.py", "build_replay_frames.py", "build_team_data.py"]
BUILD_DAILY = ["build_history_dataset.py", "build_data.py", "build_player_details.py"]


def snapshot() -> dict:
    out = {}
    for p in WATCH_PATHS:
        try:
            out[str(p)] = p.stat().st_mtime
        except OSError:
            out[str(p)] = 0
    return out


def load_state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")


SITE_DIR = SITE


def git_push_site(msg: str) -> bool:
    """把网站目录的改动提交并推送；返回是否推送成功（失败则不要继续部署）。

    注意：这里**不能**用 `git add -A`。2026-10-18 就是它把浏览器临时 profile
    （.edge-tmp3，291 个文件）提交进了公开仓库。只暂存已跟踪文件的改动 + 生成目录 assets/。
    """
    if not (SITE_DIR / ".git").exists():
        print("  （网站目录未初始化 git 仓库，跳过推送）")
        return False

    def run(c: list[str]) -> tuple[int, str]:
        r = subprocess.run(c, cwd=str(SITE_DIR), capture_output=True, text=True,
                           encoding="utf-8", errors="replace")
        out = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()
        if out:
            print("  git:", out[-1][:110])
        return r.returncode, (out[-1] if out else "")

    run(["git", "add", "-u"])
    if (SITE_DIR / "assets").exists():
        run(["git", "add", "assets"])
    run(["git", "-c", "user.name=hccccc01333",
         "-c", "user.email=hccccc01333@users.noreply.github.com", "commit", "-m", msg])
    code, _ = run(["git", "push"])
    if code != 0:
        print("  !! git push 失败，跳过 Cloudflare 部署（避免线上与仓库版本不一致）")
        return False

    # 直接部署到 Cloudflare（不依赖 Git 集成，比赛日数据即时上线）
    r = subprocess.run(["npx", "--yes", "wrangler@latest", "deploy"],
                       cwd=str(SITE_DIR), shell=True, capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    tail = ((r.stdout or "") + (r.stderr or "")).strip().splitlines()
    for line in tail[-3:]:
        print("  wrangler:", line[:110])
    return True


def run_builds(scripts: list[str]) -> None:
    for name in scripts:
        script = SITE / name
        if not script.exists():
            print(f"  !! 缺失 {script}")
            continue
        t0 = time.time()
        print(f"  -> {name} ...", flush=True)
        r = subprocess.run([sys.executable, str(script)], cwd=str(SITE),
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
        tail = (r.stdout or "").strip().splitlines()[-2:]
        for line in tail:
            print(f"     {line}")
        if r.returncode != 0:
            print(f"     !! 退出码 {r.returncode}: {(r.stderr or '')[-200:]}")
        print(f"     ({time.time()-t0:.0f}s)", flush=True)


RECENT_LEAGUES = ["20260004", "20260003", "20260002"]


def run_backfill_recent() -> None:
    """增量刷新近期联赛（今日场次强制重拉；其余缓存跳过）。"""
    script = PROJECT_ROOT / "scripts" / "backfill_league_history.py"
    if not script.exists():
        return
    r = subprocess.run([sys.executable, str(script), "--leagues", *RECENT_LEAGUES, "--jobs", "4"],
                       cwd=str(PROJECT_ROOT / "scripts"),
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    tail = (r.stdout or "").strip().splitlines()[-1:] if r.stdout else []
    if tail:
        print("  backfill:", tail[0][:120])


PUSH_ENABLED = False


def check_once(quick: bool) -> bool:
    run_backfill_recent()
    prev = load_state()
    cur = snapshot()
    changed = [k for k, v in cur.items() if prev.get(k) != v]
    if not changed:
        print("无变化。")
        return False
    print(f"检测到 {len(changed)} 个变化：")
    for c in changed:
        print("  ·", Path(c).name)
    if quick:
        run_builds(BUILD_QUICK)
    else:
        # 变化时：先快速链路，再补低频全量链路
        run_builds(BUILD_QUICK)
        run_builds(BUILD_DAILY)
    save_state(cur)
    print("重建完成。")
    if PUSH_ENABLED:
        import datetime as _dt
        print("推送到发布仓库...")
        git_push_site("data update " + _dt.datetime.now().strftime("%Y-%m-%d %H:%M"))
    return True


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--once", action="store_true")
    ap.add_argument("--quick", action="store_true", help="只重建当前赛季数据")
    ap.add_argument("--interval", type=int, default=60)
    ap.add_argument("--push", action="store_true",
                    help="每次重建后自动提交推送到发布仓库（比赛日无人值守）")
    args = ap.parse_args()
    global PUSH_ENABLED
    PUSH_ENABLED = bool(args.push)
    if not SITE.exists():
        raise SystemExit(f"网站目录不存在：{SITE}")
    if args.once:
        check_once(args.quick)
        return
    print(f"常驻监视中（每 {args.interval}s 检查一次，Ctrl+C 退出）...")
    rounds = 0
    while True:
        try:
            check_once(args.quick)
            rounds += 1
            if rounds % 30 == 0:
                print("低频全量维护（首页战报 / 详情曲线 / 选手数据）...")
                run_builds(BUILD_DAILY)
            time.sleep(args.interval)
        except KeyboardInterrupt:
            print("\n退出。")
            break


if __name__ == "__main__":
    main()
