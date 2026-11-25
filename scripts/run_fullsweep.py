#!/usr/bin/env python3
"""Launch PAL benchmark sweep across N models x M personas with bounded concurrency.

Layout: one runs-file per persona, so 2 concurrent jobs are always working on
different files and cannot collide. Within a persona file, models are dispatched
in parallel up to CONCURRENCY; each persona-file is only ever touched by one
in-flight job at a time.
"""
import argparse
import subprocess
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LOG_DIR = REPO / "logs" / "fullsweep"

# (api_model_id, logical_name)
MODELS = [
    ("gemini-2.5-flash",              "gemini-2.5-flash"),
    ("gemini-3-flash-preview",        "gemini-3-flash-preview"),
    ("gemini-3.1-flash-lite-preview", "gemini-3.1-flash-lite-preview"),
    ("claude-4.5-haiku",              "claude-4.5-haiku"),
    ("gpt-oss-20b",                   "gpt-oss-20b"),
    ("gpt-oss-120b",                  "gpt-oss-120b"),
    ("gpt-5.2",                       "gpt-5.2"),
    ("gpt-5.4",                       "gpt-5.4"),
    ("glm-4.7",                       "glm-4.7"),
]

# (persona_short_name, persona_file)
PERSONAS = [
    ("ashley", "ashley_ALL_new.md"),
    ("noah",   "noah_ALL_new.md"),
    ("ryan",   "ryan_ALL_new.md"),
    ("sophie", "sophie_ALL_new.md"),
]

JUDGE_MODEL     = "claude-opus-4-7"
ITERATIONS      = 3
THREADS_PER_JOB = 4
CONCURRENCY     = 2
HEARTBEAT_SEC   = 120

_persona_locks: dict[str, threading.Lock] = {p[0]: threading.Lock() for p in PERSONAS}
_active: dict[int, dict] = {}
_active_lock = threading.Lock()
_active_counter = 0
_stop_heartbeat = threading.Event()
_print_lock = threading.Lock()


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _say(msg: str) -> None:
    with _print_lock:
        print(msg, flush=True)


def heartbeat() -> None:
    while not _stop_heartbeat.wait(HEARTBEAT_SEC):
        with _active_lock:
            snapshot = list(_active.values())
        if not snapshot:
            continue
        now = time.time()
        lines = [f"[{_ts()}] heartbeat — {len(snapshot)} in-flight:"]
        for info in snapshot:
            elapsed = (now - info["start"]) / 60
            log = info["log"]
            size_kb = (log.stat().st_size / 1024) if log.exists() else 0
            lines.append(
                f"   * {info['persona']:7s} / {info['model']:33s}  "
                f"{elapsed:5.1f}min  log={size_kb:6.0f}KB"
            )
        _say("\n".join(lines))


def run_task(persona_name: str, persona_file: str,
             model_api: str, model_logical: str) -> tuple:
    global _active_counter

    runs_file     = REPO / f"fullsweep_{persona_name}.json"
    elo_file      = REPO / f"fullsweep_elo_{persona_name}.json"
    pals_elo_file = REPO / f"fullsweep_pals_elo_{persona_name}.json"
    log_path      = LOG_DIR / f"{persona_name}__{model_logical.replace('/', '_')}.log"
    cmd = [
        sys.executable, "eqbench3.py",
        "--test-model",            model_api,
        "--model-name",            f"{persona_name}_ALL_new ({model_logical})",
        "--judge-model",           JUDGE_MODEL,
        "--pals",
        "--pal-persona",           persona_file,
        "--iterations",            str(ITERATIONS),
        "--runs-file",             str(runs_file),
        "--elo-results-file",      str(elo_file),
        "--pals-elo-results-file", str(pals_elo_file),
        "--threads",               str(THREADS_PER_JOB),
    ]

    with _active_lock:
        _active_counter += 1
        tid = _active_counter
        _active[tid] = {
            "persona": persona_name,
            "model":   model_logical,
            "start":   time.time(),
            "log":     log_path,
        }

    _say(f"[{_ts()}] START  {persona_name:7s} / {model_logical}")
    start = time.time()
    try:
        with _persona_locks[persona_name]:
            with open(log_path, "w", encoding="utf-8") as logf:
                logf.write("CMD: " + " ".join(cmd) + "\n\n")
                logf.flush()
                rc = subprocess.call(cmd, cwd=REPO, stdout=logf, stderr=subprocess.STDOUT)
    finally:
        with _active_lock:
            _active.pop(tid, None)

    return persona_name, model_logical, rc, time.time() - start, log_path


def _log_tail(path: Path, n: int = 6) -> list[str]:
    try:
        return path.read_text(encoding="utf-8", errors="replace").splitlines()[-n:]
    except Exception:
        return ["(could not read log)"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="Print planned invocations and exit without running them.")
    ap.add_argument("--concurrency", type=int, default=CONCURRENCY)
    args = ap.parse_args()

    LOG_DIR.mkdir(parents=True, exist_ok=True)
    tasks = [
        (p_name, p_file, m_api, m_log)
        for m_api, m_log in MODELS
        for p_name, p_file in PERSONAS
    ]
    total = len(tasks)
    _say(f"Planned: {total} tasks ({len(MODELS)} models x {len(PERSONAS)} personas), "
         f"concurrency={args.concurrency}, heartbeat every {HEARTBEAT_SEC}s")

    if args.dry_run:
        for p_name, p_file, m_api, m_log in tasks:
            print(f"  {p_name:7s}  <-  {m_log}")
        return

    hb = threading.Thread(target=heartbeat, daemon=True)
    hb.start()

    done = 0
    t0 = time.time()
    try:
        with ThreadPoolExecutor(max_workers=args.concurrency) as ex:
            futures = {ex.submit(run_task, *t): t for t in tasks}
            for fut in as_completed(futures):
                p, m, rc, dur, log = fut.result()
                done += 1
                elapsed = (time.time() - t0) / 60
                status = "OK  " if rc == 0 else f"FAIL"
                _say(f"[{_ts()}] {status}  [{done:2d}/{total}] {p:7s} / {m:33s} "
                     f"{dur/60:5.1f}min  (total {elapsed:5.1f}min)")
                if rc != 0:
                    _say(f"   last lines of {log.name}:")
                    for line in _log_tail(log):
                        _say(f"   | {line[:200]}")
    finally:
        _stop_heartbeat.set()

    _say(f"\nAll {total} tasks finished in {(time.time() - t0)/60:.1f} min.")


if __name__ == "__main__":
    main()
