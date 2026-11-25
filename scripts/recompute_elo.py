#!/usr/bin/env python3
"""Re-run ELO analysis for the 4 pre-patch gemini-2.5-flash runs.

Rubric scoring and conversations are already saved (tasks at 'rubric_scored'
status); eqbench3 will skip those and only retry the failed ELO step, which
now has the rank_window fix.
"""
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LOG_DIR = REPO / "logs" / "elo_recompute"

JOBS = [
    # (persona, run_id_prefix, persona_file)
    ("ashley", "1297d897", "ashley_ALL_new.md"),
    ("noah",   "058fc857", "noah_ALL_new.md"),
    ("ryan",   "6754cd6b", "ryan_ALL_new.md"),
    ("sophie", "95467e57", "sophie_ALL_new.md"),
]
MODEL_API     = "gemini-2.5-flash"
MODEL_LOGICAL = "gemini-2.5-flash"
JUDGE_MODEL   = "claude-opus-4-7"
ITERATIONS    = 3
THREADS       = 4
CONCURRENCY   = 2


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def run_job(persona: str, run_id: str, persona_file: str) -> tuple:
    runs_file     = REPO / f"fullsweep_{persona}.json"
    elo_file      = REPO / f"fullsweep_elo_{persona}.json"
    pals_elo_file = REPO / f"fullsweep_pals_elo_{persona}.json"
    log_path      = LOG_DIR / f"{persona}__{MODEL_LOGICAL}.log"
    cmd = [
        sys.executable, "eqbench3.py",
        "--test-model",            MODEL_API,
        "--model-name",            f"{persona}_ALL_new ({MODEL_LOGICAL})",
        "--judge-model",           JUDGE_MODEL,
        "--pals",
        "--pal-persona",           persona_file,
        "--iterations",            str(ITERATIONS),
        "--runs-file",             str(runs_file),
        "--elo-results-file",      str(elo_file),
        "--pals-elo-results-file", str(pals_elo_file),
        "--threads",               str(THREADS),
        "--run-id",                run_id,
    ]
    print(f"[{_ts()}] START  {persona} (run_id={run_id})", flush=True)
    start = time.time()
    with open(log_path, "w", encoding="utf-8") as logf:
        logf.write("CMD: " + " ".join(cmd) + "\n\n")
        logf.flush()
        rc = subprocess.call(cmd, cwd=REPO, stdout=logf, stderr=subprocess.STDOUT)
    dur = time.time() - start
    return persona, rc, dur, log_path


def main():
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Recomputing ELO for {len(JOBS)} gemini-2.5-flash runs, concurrency={CONCURRENCY}")
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=CONCURRENCY) as ex:
        futs = {ex.submit(run_job, *j): j for j in JOBS}
        for fut in as_completed(futs):
            persona, rc, dur, log = fut.result()
            status = "OK" if rc == 0 else f"FAIL(rc={rc})"
            print(f"[{_ts()}] {status:10s} {persona:7s}  {dur/60:.1f}min  -> {log.name}", flush=True)
    print(f"\nDone in {(time.time()-t0)/60:.1f} min.")


if __name__ == "__main__":
    main()
