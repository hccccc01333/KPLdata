"""Cross-platform monitor supervisor (works in Git Bash / PowerShell / cmd).

Writes a rotating-ish log under data/realtime/logs/ so silent BAT exits are diagnosable.
"""
from __future__ import annotations

import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = Path(__file__).resolve().parent / "official_match_monitor.py"
LOG_DIR = ROOT / "data" / "realtime" / "logs"
RESTART_SEC = 30


def _log_path() -> Path:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    return LOG_DIR / f"monitor_{datetime.now().strftime('%Y%m%d')}.log"


def log(msg: str) -> None:
    line = f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}"
    print(line, flush=True)
    try:
        with _log_path().open("a", encoding="utf-8") as f:
            f.write(line + "\n")
    except OSError:
        pass


def main() -> None:
    extra = sys.argv[1:]
    log(f"supervisor start python={sys.executable} script={SCRIPT} args={extra}")
    while True:
        log("official_match_monitor.py starting...")
        try:
            proc = subprocess.run(
                [sys.executable, "-u", str(SCRIPT), *extra],
                cwd=str(ROOT),
            )
            code = proc.returncode
        except KeyboardInterrupt:
            log("STOP supervisor (KeyboardInterrupt)")
            break
        except Exception as exc:
            log(f"supervisor spawn failed: {exc}")
            log(traceback.format_exc())
            code = -1
        log(f"exited (code={code}), restart in {RESTART_SEC}s. Ctrl+C to stop.")
        try:
            time.sleep(RESTART_SEC)
        except KeyboardInterrupt:
            log("STOP supervisor exited.")
            break


if __name__ == "__main__":
    main()
