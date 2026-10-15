# -*- coding: utf-8 -*-
"""Showcase 截图工具：对运行中的 Dashboard 逐模块截图，输出到 docs/showcase/。

前置：本机启动 Dashboard（``streamlit run scripts/dashboard.py``）。

运行：
    python scripts/capture_showcase.py                    # 全部模块
    python scripts/capture_showcase.py --only schedule sim
    python scripts/capture_showcase.py --url http://127.0.0.1:8501 --out docs/showcase

说明：
- 文件名按模块固定映射（07-ops / 08-sim），避免按序号命名漂移；
- 默认 Chromium 附加 ``--no-proxy-server``（本地 KPL 直连环境；代理故障不影响截图）；
  需要走系统代理时加 ``--use-proxy``；
- 浏览器可执行文件优先取 ``--exe``，其次环境变量 ``KPL_CHROMIUM``，否则用 Playwright 自带浏览器；
- 依赖：``pip install playwright``。
"""
from __future__ import annotations

import argparse
import asyncio
import os
import sys

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from playwright.async_api import async_playwright

HIDE_CSS = """
[data-testid="stToolbar"]{display:none !important}
[data-testid="stStatusWidget"]{display:none !important}
[data-testid="stDecoration"]{display:none !important}
[data-testid="stAppDeployButton"]{display:none !important}
#MainMenu{visibility:hidden !important}
"""

# (module, 侧栏标签, 页面标题, 底部内容标记, 附加等待 ms, 输出文件名)
MODULES = [
    ("schedule", "◆ 赛事中心", "赛事中心", "大场列表", 2500, "01-schedule.png"),
    ("live", "▲ 实时中控", "实时中控", "与金差先验对标", 3000, "02-live.png"),
    ("replay", "■ 单局复盘", "单局复盘", "快照切片", 4500, "03-replay.png"),
    ("teams", "● 战队画像", "战队画像", "英雄池", 3500, "04-teams.png"),
    ("players", "◀ 选手排行", "选手排行", "排行榜", 3000, "05-players.png"),
    ("heroes", "◇ 英雄 Meta", "英雄 Meta", "英雄梯度榜", 3500, "06-heroes.png"),
    ("ops", "▼ 数据健康", "数据健康", "数据表规模", 3000, "07-ops.png"),
    ("sim", "▣ 大场模拟", "大场模拟", "局分分布", 3000, "08-sim.png"),
]


async def wait_ready(page) -> None:
    for _ in range(150):
        try:
            ok = await page.evaluate(
                "() => document.querySelector('.css-sentinel') !== null && "
                "document.querySelectorAll('[data-testid=stSpinner]').length === 0"
            )
            if ok:
                return
        except Exception:
            pass
        await page.wait_for_timeout(600)


async def wait_title(page, title: str, timeout_ms: int = 30000) -> bool:
    for _ in range(timeout_ms // 500):
        try:
            t = await page.evaluate("() => (document.querySelector('.page-title')||{}).innerText || ''")
            if t.strip() == title:
                return True
        except Exception:
            pass
        await page.wait_for_timeout(500)
    return False


async def capture_replay_tabs(page, out_dir: str) -> None:
    """复盘页附加：选手面板与事件归因（滚动到阶段切片）两张。"""
    for tab, fname, scroll in (
        ("选手面板", "03b-replay-players.png", False),
        ("事件归因", "03c-replay-attribution.png", True),
    ):
        try:
            await page.locator(f"button[role='tab']:has-text('{tab}')").first.click(timeout=8000)
            await page.wait_for_timeout(4500)
            if scroll:
                try:
                    await page.wait_for_selector(".at-card", timeout=20000, state="attached")
                except Exception:
                    pass
                await page.evaluate(
                    """() => {
                        const els = [...document.querySelectorAll('.panel-title')];
                        const t = els.find(e => e.innerText.includes('阶段切片'));
                        if (t) { (t.closest('.panel') || t).scrollIntoView({block: 'start'}); }
                    }"""
                )
                await page.wait_for_timeout(1600)
            await page.screenshot(path=os.path.join(out_dir, fname))
            print(f"  [replay] {tab} -> {fname}", flush=True)
        except Exception as e:
            print(f"  [replay] {tab} skipped: {str(e)[:120]}", flush=True)


async def main() -> None:
    ap = argparse.ArgumentParser(description="Capture dashboard module screenshots")
    ap.add_argument("--url", default="http://127.0.0.1:8501")
    ap.add_argument("--out", default=os.path.join("docs", "showcase"))
    ap.add_argument("--only", nargs="*", default=None, help="只截指定模块（如 schedule sim）")
    ap.add_argument("--exe", default=os.environ.get("KPL_CHROMIUM") or None,
                    help="Chromium 可执行文件；缺省用 Playwright 自带浏览器")
    ap.add_argument("--use-proxy", action="store_true", help="浏览器走系统代理（默认绕过）")
    args = ap.parse_args()

    os.makedirs(args.out, exist_ok=True)
    launch_args = [] if args.use_proxy else ["--no-proxy-server"]
    errs: list[str] = []

    async with async_playwright() as p:
        browser = await p.chromium.launch(executable_path=args.exe, headless=True, args=launch_args)
        ctx = await browser.new_context(viewport={"width": 1500, "height": 950}, locale="zh-CN")
        page = await ctx.new_page()
        page.on("pageerror", lambda e: errs.append(f"pageerror: {e}"))
        page.on("console", lambda m: errs.append(f"console.error: {m.text}") if m.type == "error" else None)

        sel = [m for m in MODULES if not args.only or m[0] in set(args.only)]
        for name, label, title, marker, settle, fname in sel:
            status = "?"
            for attempt in range(1, 4):
                try:
                    await page.goto(args.url, wait_until="domcontentloaded", timeout=60000)
                    await page.add_style_tag(content=HIDE_CSS)
                    await wait_ready(page)
                    if name != "schedule":
                        await page.locator(f"label:has-text('{label}')").first.click(timeout=20000)
                    if not await wait_title(page, title, 30000):
                        status = f"title-miss(attempt{attempt})"
                        await page.wait_for_timeout(3000)
                        continue
                    try:
                        await page.wait_for_selector(f"text={marker}", timeout=25000, state="attached")
                        status = "ok"
                    except Exception:
                        status = f"marker-miss:{marker}(attempt{attempt})"
                    await page.wait_for_timeout(settle)
                    if status == "ok":
                        break
                except Exception as e:
                    errs.append(f"{name} attempt{attempt}: {e}")
                    status = f"error(attempt{attempt})"
                    await page.wait_for_timeout(2000)
            await page.screenshot(path=os.path.join(args.out, fname))
            print(f"[{name}] {status} -> {fname}", flush=True)

            if name == "replay":
                await capture_replay_tabs(page, args.out)

        await browser.close()

    print(f"page errors: {len(errs)}")
    for e in errs[:10]:
        print("  ", e)


if __name__ == "__main__":
    asyncio.run(main())
