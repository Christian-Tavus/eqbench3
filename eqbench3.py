# File: ai/eqbench3/eqbench3.py

"""
Main entry point for the EQBench3 benchmark based on multi-turn scenarios.
Includes scenario simulation, debriefing, optional rubric scoring, and optional ELO analysis.
"""
import argparse
import sys
import signal
import logging
from datetime import datetime, timezone
import os # For path joining
from typing import Dict, Any
# Added import for leaderboard printing
import unicodedata

# Load environment variables early
from dotenv import load_dotenv
load_dotenv()

from utils.logging_setup import setup_logging, get_verbosity
from utils.file_io import load_json_file, update_run_data, save_json_file # save_json_file needed for reset
from core.benchmark import run_eq_bench3 # Import the main benchmark runner
import utils.constants as C # Import constants for default file paths


def signal_handler(signum, frame):
    """Handles graceful shutdown on signals like Ctrl+C."""
    print(f"\n[INFO] Signal {signum} received. Shutting down gracefully...")
    logging.info(f"Shutdown signal {signum} received.")
    # Perform any necessary cleanup here if needed
    sys.exit(1)

def print_summary_box(run_key: str, local_runs_file: str, run_elo: bool, run_rubric: bool):
    """
    Prints a formatted summary box of the benchmark run.
    Reads data ONLY from the local runs file.
    """
    try:
        # Load only local runs data for the summary box
        runs = load_json_file(local_runs_file)
        run_data = runs.get(run_key)
        if not run_data:
            print(f"\nError: Could not find run data for key {run_key} in local runs file {local_runs_file}")
            logging.warning(f"Summary box generation failed: Run key {run_key} not found in {local_runs_file}")
            return

        # Use model_name if available, fallback to test_model (legacy), then api_model_id
        model_name = run_data.get("model_name", run_data.get("test_model", "N/A"))
        api_model_id = run_data.get("api_model_id", "N/A")
        judge_model = run_data.get("judge_model", "N/A") # Judge model used for ELO and Rubric
        start_time_str = run_data.get("start_time")
        end_time_str = run_data.get("end_time")
        run_status = run_data.get("status", "Unknown")

        duration_str = "N/A"
        if start_time_str and end_time_str:
            try:
                start_time = datetime.fromisoformat(start_time_str.replace("Z", "+00:00"))
                end_time = datetime.fromisoformat(end_time_str.replace("Z", "+00:00"))
                if start_time.tzinfo is None: start_time = start_time.replace(tzinfo=timezone.utc)
                if end_time.tzinfo is None: end_time = end_time.replace(tzinfo=timezone.utc)
                duration = end_time - start_time
                total_seconds = duration.total_seconds()
                hours, remainder = divmod(total_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                duration_str = f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"
            except ValueError as e:
                duration_str = "Error parsing time"
                logging.error(f"Error parsing run duration times: {start_time_str}, {end_time_str} - {e}")

        results = run_data.get("results", {})

        # --- Rubric Score (Calculate 0-100) ---
        rubric_score_0_20 = results.get("average_rubric_score", "N/A") # This is the 0-20 score
        rubric_error = results.get("rubric_error")
        rubric_score_100_str = "N/A" # Initialize the display string

        if not run_rubric:
            rubric_score_100_str = "Skipped"
        elif rubric_error:
            rubric_score_100_str = f"Error ({rubric_error[:20]}...)"
        elif isinstance(rubric_score_0_20, (int, float)):
            # Scale the 0-20 score to 0-100
            rubric_score_0_100 = rubric_score_0_20 * 5.0
            rubric_score_100_str = f"{rubric_score_0_100:.2f}" # Format the 0-100 score
        else:
            # Handle cases where score might be "N/A" or other non-numeric string
             rubric_score_100_str = str(rubric_score_0_20)


        # --- ELO Score ---
        elo_raw = results.get("elo_raw", "N/A")
        elo_norm = results.get("elo_normalized", "N/A")
        elo_error = results.get("elo_error")
        elo_raw_str = "N/A"
        elo_norm_str = "N/A"

        if not run_elo:
            elo_raw_str = "Skipped"
            elo_norm_str = "Skipped"
        elif elo_error:
             elo_raw_str = f"Error ({elo_error[:20]}...)"
             elo_norm_str = f"Error ({elo_error[:20]}...)"
        else:
            elo_raw_str = f"{elo_raw:.2f}" if isinstance(elo_raw, (int, float)) else str(elo_raw)
            elo_norm_str = f"{elo_norm:.2f}" if isinstance(elo_norm, (int, float)) else str(elo_norm)

        # --- PAL Fitness Score (Calculate 0-100) ---
        pals_fitness_0_20 = results.get("pals_fitness_score")
        pals_fitness_error = results.get("pals_fitness_error")
        has_pals_data = pals_fitness_0_20 is not None and pals_fitness_0_20 != "Skipped"
        pals_fitness_100_str = "N/A"

        if pals_fitness_error:
            pals_fitness_100_str = f"Error ({pals_fitness_error[:20]}...)"
        elif isinstance(pals_fitness_0_20, (int, float)):
            pals_fitness_100_str = f"{pals_fitness_0_20 * 5.0:.2f}"
        elif pals_fitness_0_20 is not None:
            pals_fitness_100_str = str(pals_fitness_0_20)

        # --- Adversarial Pass Rate ---
        adversarial_pass_rate = results.get("adversarial_pass_rate")

        import unicodedata

        # ──────────  helper: printable width  ──────────
        def cell_width(s: str) -> int:
            """Return the on‑screen width of s in monospaced fonts."""
            w = 0
            for ch in s:
                # ‘F’=Full, ‘W’=Wide → 2 columns; everything else → 1
                w += 2 if unicodedata.east_asian_width(ch) in ("F", "W") else 1
            return w

        def crop_to_width(s: str, max_w: int, ellipsis="…") -> str:
            """Trim string so its visual width ≤ max_w (add ellipsis if trimmed)."""
            if cell_width(s) <= max_w:
                return s + " " * (max_w - cell_width(s))
            keep_w = max_w - cell_width(ellipsis)
            out = ""
            for ch in s:
                ch_w = 2 if unicodedata.east_asian_width(ch) in ("F", "W") else 1
                if cell_width(out) + ch_w > keep_w:
                    break
                out += ch
            return out + ellipsis

        # ──────────  box parameters  ──────────
        BOX_W      = 80          # total width including borders
        PAD        = 1           # spaces inside each cell
        LINE       = "─"
        TOP        = "┌" + LINE * (BOX_W - 2) + "┐"
        BOTTOM     = "└" + LINE * (BOX_W - 2) + "┘"
        ROW_SEP    = "├" + LINE * (BOX_W - 2) + "┤"
        TITLE_SEP  = "╞" + LINE * (BOX_W - 2) + "╡"

        # ──────────  collect rows in sections  ──────────
        # Each section is (title_or_None, [(label, value), ...])
        # A section title of None means no header row before it.
        info_rows = [
            ("Run Key:",               run_key),
            ("Model Name:",            model_name),
            ("API Model ID:",          api_model_id),
        ]
        if run_elo or run_rubric:
            lbl_bits = []
            if run_rubric: lbl_bits.append("Rubric")
            if run_elo:   lbl_bits.append("ELO")
            info_rows.append((f"Judge ({'/'.join(lbl_bits)}):", judge_model))
        info_rows.extend([
            ("Status:",                run_status),
            ("Duration:",              duration_str),
        ])

        scoring_rows = [("Rubric Score (0‑100):",  rubric_score_100_str)]
        if has_pals_data:
            scoring_rows.append(("PAL Fitness (0‑100):", pals_fitness_100_str))
            if adversarial_pass_rate:
                scoring_rows.append(("Adversarial Pass Rate:", adversarial_pass_rate))

        elo_rows = [
            ("ELO Raw:",               elo_raw_str),
            ("ELO (Normalised):",      elo_norm_str),
        ]

        sections = [
            (None, info_rows),
            ("PAL-Bench Results" if has_pals_data else None, scoring_rows),
            ("ELO Analysis Results", elo_rows),
        ]

        # Flatten for column width calculation
        rows = [row for _, section_rows in sections for row in section_rows]

        # ──────────  calculate column widths  ──────────
        max_label = max(cell_width(lbl) for lbl, _ in rows)
        # cap label col so value column is at least 15‑char wide
        # constant characters per row:
        #   • 3 border glyphs  │ │ │
        #   • 4 padding spaces (PAD on each side of each cell)
        CONST_CHARS = 3 + 4*PAD          # = 7 when PAD == 1

        label_col = min(max(cell_width(lbl) for lbl, _ in rows),
                        BOX_W - CONST_CHARS - 15)     # leave ≥15 for value col
        value_col = BOX_W - CONST_CHARS - label_col   # <-- corrected here

        def make_row(lbl: str, val: str) -> str:
            lbl_fmt = crop_to_width(lbl,  label_col)
            val_fmt = crop_to_width(val,  value_col)
            return (f"│{' '*PAD}{lbl_fmt}{' '*PAD}│"
                    f"{' '*PAD}{val_fmt}{' '*PAD}│")

        # ──────────  render  ──────────
        print("\n" + TOP)
        print(make_row("", "EQBench3 Results Summary".center(value_col)))
        print(TITLE_SEP)
        for section_title, section_rows in sections:
            if section_title is not None:
                print(ROW_SEP)
                print(make_row("", section_title.center(value_col)))
            print(ROW_SEP)
            for (lbl, val) in section_rows:
                print(make_row(lbl, str(val)))
        print(BOTTOM)


    except Exception as e:
        print(f"\nError generating summary box: {e}")
        logging.error(f"Error generating summary box for run {run_key}", exc_info=True)


def print_leaderboard_summary(elo_data: Dict[str, Any], highlight_model: str):
    """Prints a formatted leaderboard summary, sorted by ELO Norm."""
    if not elo_data:
        print("\n[INFO] No ELO data available to display leaderboard.")
        return

    # --- Prepare data ---
    leaderboard_entries = []
    for model, data in elo_data.items():
        if model == "__metadata__" or not isinstance(data, dict):
            continue
        # Use .get with defaults for robustness
        elo_norm = data.get("elo_norm", 0.0) # Default to 0 for sorting if missing
        elo_raw = data.get("elo", "N/A")
        sigma = data.get("sigma", "N/A")
        ci_low_norm = data.get("ci_low_norm", "N/A")
        ci_high_norm = data.get("ci_high_norm", "N/A")

        # Format CI string
        ci_str = "N/A"
        if ci_low_norm != "N/A" and ci_high_norm != "N/A":
            try:
                # Use norm CI for display
                ci_str = f"{ci_low_norm:.0f} - {ci_high_norm:.0f}"
            except (TypeError, ValueError):
                ci_str = "[Err]" # Handle non-numeric CI values

        leaderboard_entries.append({
            "name": model,
            "elo_norm": elo_norm if isinstance(elo_norm, (int, float)) else 0.0, # Ensure numeric for sort
            "elo_norm_disp": f"{elo_norm:.0f}" if isinstance(elo_norm, (int, float)) else str(elo_norm),
            "elo_raw_disp": f"{elo_raw:.0f}" if isinstance(elo_raw, (int, float)) else str(elo_raw),
            "ci_norm_disp": ci_str,
            "sigma_disp": f"{sigma:.1f}" if isinstance(sigma, (int, float)) else str(sigma),
        })

    # Sort by ELO Norm descending
    leaderboard_entries.sort(key=lambda x: x["elo_norm"], reverse=True)

    # --- Formatting Helpers (from print_summary_box) ---
    def cell_width(s: str) -> int:
        w = 0
        for ch in s: w += 2 if unicodedata.east_asian_width(ch) in ("F", "W") else 1
        return w

    def crop_to_width(s: str, max_w: int, ellipsis="…") -> str:
        s = str(s) # Ensure string conversion
        if cell_width(s) <= max_w: return s + " " * (max_w - cell_width(s))
        keep_w = max_w - cell_width(ellipsis)
        out = ""
        current_w = 0
        for ch in s:
            ch_w = 2 if unicodedata.east_asian_width(ch) in ("F", "W") else 1
            if current_w + ch_w > keep_w: break
            out += ch
            current_w += ch_w
        return out + ellipsis + " " * (max_w - cell_width(out + ellipsis))


    # --- Table Parameters ---
    COL_PAD = 1
    RANK_W = 4
    MODEL_W = 35 # Adjust as needed
    ELO_NORM_W = 8
    ELO_RAW_W = 8
    CI_W = 12 # Width for "[XXXX - YYYY]"
    SIGMA_W = 7

    cols = [RANK_W, MODEL_W, ELO_NORM_W, ELO_RAW_W, CI_W, SIGMA_W]
    LINE = "─"

    # --- Corrected Separator and Box Width Calculation ---
    # Calculate the width of each line segment including padding
    segments = [LINE * (w + 2 * COL_PAD) for w in cols]
    # Join segments with the correct column separator (┼)
    ROW_SEP_INNER = "┼".join(segments)
    # Create the full row separator line
    ROW_SEP = f"├{ROW_SEP_INNER}┤"
    # Calculate the total box width based on the correctly calculated separator
    BOX_W = len(ROW_SEP)

    # --- Recalculate other lines based on correct BOX_W ---
    TOP = "┌" + LINE * (BOX_W - 2) + "┐"
    BOTTOM = "└" + LINE * (BOX_W - 2) + "┘"
    TITLE_SEP = "╞" + LINE * (BOX_W - 2) + "╡"

    # --- Header Row ---
    headers = ["Rank", "Model Name", "ELO Norm", "ELO Raw", "95% CI Norm", "Sigma"]
    header_cells = [
        crop_to_width(h, w).center(w) # Center header text within its column width
        for h, w in zip(headers, cols)
    ]
    # Construct the header row string with padding and column separators
    header_parts = []
    for cell_content in header_cells:
        header_parts.append(f"{' ' * COL_PAD}{cell_content}{' ' * COL_PAD}")
    header_row = f"│{'│'.join(header_parts)}│" # Join padded cells with │

    # --- Print Table ---
    print("\n" + TOP)
    print(f"│{'EQBench3 Elo Results'.center(BOX_W - 2)}│") # Center title within the box
    print(TITLE_SEP)
    print(header_row)
    print(ROW_SEP) # Print the correctly calculated row separator directly

    for rank, entry in enumerate(leaderboard_entries, 1):
        is_highlighted = entry["name"] == highlight_model
        prefix = ">" if is_highlighted else " "
        rank_str = f"{prefix}{rank}"

        cells = [
            crop_to_width(rank_str, RANK_W),
            crop_to_width(entry["name"], MODEL_W),
            crop_to_width(entry["elo_norm_disp"], ELO_NORM_W).rjust(ELO_NORM_W),
            crop_to_width(entry["elo_raw_disp"], ELO_RAW_W).rjust(ELO_RAW_W),
            crop_to_width(entry["ci_norm_disp"], CI_W).center(CI_W),
            crop_to_width(entry["sigma_disp"], SIGMA_W).rjust(SIGMA_W),
        ]
        row_str = f"│{' ' * COL_PAD}" + f"{' ' * COL_PAD}│{' ' * COL_PAD}".join(cells) + f"{' ' * COL_PAD}│"
        print(row_str)

    print(BOTTOM)

def print_rubric_summary(runs_data: Dict[str, Any], highlight_model: str):
    """Prints a formatted leaderboard summary based on Rubric Scores."""
    if not runs_data:
        print("\n[INFO] No run data available to display Rubric leaderboard.")
        return

    # --- Prepare data ---
    rubric_entries = []
    any_has_pals = False
    for run_key, run_data in runs_data.items():
        if not isinstance(run_data, dict):
            continue

        model_name = run_data.get("model_name", run_data.get("test_model", "Unknown"))
        results = run_data.get("results", {})
        rubric_score_0_20 = results.get("average_rubric_score") # 0-20 scale
        rubric_error = results.get("rubric_error")

        score_100 = 0.0 # Default for sorting if missing/error
        score_disp = "N/A"

        if rubric_error:
            score_disp = "Error"
        elif rubric_score_0_20 == "Skipped":
             score_disp = "Skipped"
        elif isinstance(rubric_score_0_20, (int, float)):
            score_100 = rubric_score_0_20 * 5.0
            score_disp = f"{score_100:.1f}" # Display with 1 decimal place
        elif rubric_score_0_20 is not None: # Handle other non-numeric strings like "N/A"
             score_disp = str(rubric_score_0_20)

        # PAL Fitness Score
        pals_0_20 = results.get("pals_fitness_score")
        pals_100 = None
        pals_disp = "—"
        if isinstance(pals_0_20, (int, float)):
            pals_100 = pals_0_20 * 5.0
            pals_disp = f"{pals_100:.1f}"
            any_has_pals = True

        # Only include entries that have a valid score attempt (not skipped and has results)
        if "results" in run_data and rubric_score_0_20 != "Skipped":
            rubric_entries.append({
                "name": model_name,
                "score_100": score_100,
                "score_disp": score_disp,
                "pals_100": pals_100,
                "pals_disp": pals_disp,
            })

    # Sort by Rubric Score (0-100) descending
    rubric_entries.sort(key=lambda x: x["score_100"], reverse=True)

    # --- Formatting Helpers (copied from print_leaderboard_summary) ---
    def cell_width(s: str) -> int:
        w = 0
        for ch in s: w += 2 if unicodedata.east_asian_width(ch) in ("F", "W") else 1
        return w

    def crop_to_width(s: str, max_w: int, ellipsis="…") -> str:
        s = str(s) # Ensure string conversion
        if cell_width(s) <= max_w: return s + " " * (max_w - cell_width(s))
        keep_w = max_w - cell_width(ellipsis)
        out = ""
        current_w = 0
        for ch in s:
            ch_w = 2 if unicodedata.east_asian_width(ch) in ("F", "W") else 1
            if current_w + ch_w > keep_w: break
            out += ch
            current_w += ch_w
        return out + ellipsis + " " * (max_w - cell_width(out + ellipsis))

    # --- Table Parameters ---
    COL_PAD = 1
    RANK_W = 4
    MODEL_W = 40 if any_has_pals else 50  # Narrower when PAL column is present
    SCORE_W = 15 # Width for "XXX.X / 100"
    PALS_W = 17  # Width for PAL Fitness (0-100) column

    if any_has_pals:
        cols = [RANK_W, MODEL_W, SCORE_W, PALS_W]
        headers = ["Rank", "Model Name", "Rubric (0-100)", "PAL Fitness (0-100)"]
    else:
        cols = [RANK_W, MODEL_W, SCORE_W]
        headers = ["Rank", "Model Name", "Rubric (0-100)"]

    LINE = "─"

    # --- Separator and Box Width Calculation ---
    segments = [LINE * (w + 2 * COL_PAD) for w in cols]
    ROW_SEP_INNER = "┼".join(segments)
    ROW_SEP = f"├{ROW_SEP_INNER}┤"
    BOX_W = len(ROW_SEP)

    # --- Recalculate other lines based on correct BOX_W ---
    TOP = "┌" + LINE * (BOX_W - 2) + "┐"
    BOTTOM = "└" + LINE * (BOX_W - 2) + "┘"
    TITLE_SEP = "╞" + LINE * (BOX_W - 2) + "╡"

    # --- Header Row ---
    header_cells = [
        crop_to_width(h, w).center(w)
        for h, w in zip(headers, cols)
    ]
    header_parts = [f"{' ' * COL_PAD}{cell_content}{' ' * COL_PAD}" for cell_content in header_cells]
    header_row = f"│{'│'.join(header_parts)}│"

    # --- Print Table ---
    print("\n" + TOP)
    print(f"│{'EQBench3 Rubric Score Summary'.center(BOX_W - 2)}│")
    print(TITLE_SEP)
    print(header_row)
    print(ROW_SEP)

    for rank, entry in enumerate(rubric_entries, 1):
        is_highlighted = entry["name"] == highlight_model
        prefix = ">" if is_highlighted else " "
        rank_str = f"{prefix}{rank}"

        cells = [
            crop_to_width(rank_str, RANK_W),
            crop_to_width(entry["name"], MODEL_W),
            crop_to_width(entry["score_disp"], SCORE_W).rjust(SCORE_W),
        ]
        if any_has_pals:
            cells.append(crop_to_width(entry["pals_disp"], PALS_W).rjust(PALS_W))
        row_parts = [f"{' ' * COL_PAD}{cell_content}{' ' * COL_PAD}" for cell_content in cells]
        row_str = f"│{'│'.join(row_parts)}│"
        print(row_str)

    print(BOTTOM)

def print_adversarial_summary(adversarial_results: Dict[str, Any]):
    """Prints a pass/fail breakdown for adversarial PAL scenarios."""
    if not adversarial_results:
        return

    import unicodedata

    def cell_width(s: str) -> int:
        w = 0
        for ch in s: w += 2 if unicodedata.east_asian_width(ch) in ("F", "W") else 1
        return w

    def crop_to_width(s: str, max_w: int, ellipsis="…") -> str:
        s = str(s)
        if cell_width(s) <= max_w: return s + " " * (max_w - cell_width(s))
        keep_w = max_w - cell_width(ellipsis)
        out, current_w = "", 0
        for ch in s:
            ch_w = 2 if unicodedata.east_asian_width(ch) in ("F", "W") else 1
            if current_w + ch_w > keep_w: break
            out += ch
            current_w += ch_w
        return out + ellipsis + " " * (max_w - cell_width(out + ellipsis))

    COL_PAD = 1
    ID_W = 5
    RESULT_W = 6
    DOMAIN_W = 22
    CONDITION_W = 42
    cols = [ID_W, RESULT_W, DOMAIN_W, CONDITION_W]
    LINE = "─"

    segments = [LINE * (w + 2 * COL_PAD) for w in cols]
    ROW_SEP_INNER = "┼".join(segments)
    ROW_SEP = f"├{ROW_SEP_INNER}┤"
    BOX_W = len(ROW_SEP)
    TOP = "┌" + LINE * (BOX_W - 2) + "┐"
    BOTTOM = "└" + LINE * (BOX_W - 2) + "┘"
    TITLE_SEP = "╞" + LINE * (BOX_W - 2) + "╡"

    total = len(adversarial_results)
    passed = sum(1 for r in adversarial_results.values() if r["passed"])
    title = f"Adversarial Scenarios: {passed}/{total} Passed"

    headers = ["ID", "Result", "Domain", "Pass Condition"]
    header_cells = [crop_to_width(h, w).center(w) for h, w in zip(headers, cols)]
    header_parts = [f"{' ' * COL_PAD}{c}{' ' * COL_PAD}" for c in header_cells]
    header_row = f"│{'│'.join(header_parts)}│"

    print("\n" + TOP)
    print(f"│{title.center(BOX_W - 2)}│")
    print(TITLE_SEP)
    print(header_row)
    print(ROW_SEP)

    for sid in sorted(adversarial_results.keys(), key=int):
        r = adversarial_results[sid]
        result_str = "PASS" if r["passed"] else "FAIL"
        domain_str = r.get("subdomain", r.get("domain", ""))
        condition_str = r.get("pass_condition", "") or ""

        cells = [
            crop_to_width(sid, ID_W),
            crop_to_width(result_str, RESULT_W),
            crop_to_width(domain_str, DOMAIN_W),
            crop_to_width(condition_str, CONDITION_W),
        ]
        row_parts = [f"{' ' * COL_PAD}{c}{' ' * COL_PAD}" for c in cells]
        print(f"│{'│'.join(row_parts)}│")

    print(BOTTOM)


def _reset_model_data(model_name: str, local_runs_file: str, local_elo_file: str):
    """
    Remove all entries for the logical `model_name` from the LOCAL files:
      • local_runs_file (main run data)
      • local_elo_file (ELO results and pairwise comparisons)
    Does NOT touch leaderboard files.
    """
    # --- purge local runs file ---
    runs = load_json_file(local_runs_file) or {}
    to_delete = [k for k,v in runs.items()
                 if isinstance(v, dict) and v.get("model_name", v.get("test_model")) == model_name] # Check model_name first, fallback to test_model
    deleted_count = 0
    for k in to_delete:
        if k in runs:
            del runs[k]
            deleted_count += 1
    if deleted_count > 0:
        save_json_file(runs, local_runs_file)
        logging.info(f"[RESET] Removed {deleted_count} run(s) for '{model_name}' from local runs file: {local_runs_file}")

    # --- purge local ELO file ---
    if not os.path.exists(local_elo_file):
        logging.info(f"[RESET] Local ELO file not found, skipping purge: {local_elo_file}")
        return

    elo = load_json_file(local_elo_file) or {}
    elo_changed = False
    # Check if the logical model name exists as a top-level key
    if model_name in elo:
        del elo[model_name]
        elo_changed = True
        logging.info(f"[RESET] Removed top-level ELO entry for '{model_name}' from {local_elo_file}")

    meta = elo.setdefault("__metadata__", {})
    comps = meta.get("global_pairwise_comparisons", [])
    initial_comp_count = len(comps)
    # Filter comparisons based on logical model names stored in the pair dict
    comps_filtered = [
        c for c in comps
        if model_name not in (
            c.get("pair",{}).get("test_model"), # These should hold logical names
            c.get("pair",{}).get("neighbor_model")
        )
    ]
    if len(comps_filtered) < initial_comp_count:
        meta["global_pairwise_comparisons"] = comps_filtered
        elo_changed = True
        logging.info(f"[RESET] Pruned {initial_comp_count - len(comps_filtered)} comparisons involving '{model_name}' from {local_elo_file}")

    if elo_changed:
        save_json_file(elo, local_elo_file)
        logging.info(f"[RESET] Saved updated local ELO file: {local_elo_file}")
    else:
        logging.info(f"[RESET] No data found for '{model_name}' in local ELO file: {local_elo_file}")


def main():
    parser = argparse.ArgumentParser(description="Run EQBench3 Scenario Benchmark.")
    # --- Model Identifiers ---
    parser.add_argument("--test-model", required=True, help="Identifier for the model sent to the API (e.g., 'openai/gpt-4o'). This is the API Model ID.")
    parser.add_argument("--model-name", help="Logical identifier for the model (e.g., 'gpt-4o-june-2024') used for tracking and leaderboards. Defaults to the value of --test-model if not provided.")
    parser.add_argument("--judge-model", help="Identifier for the judge model used for ELO pairwise comparisons and/or Rubric scoring.")
    # --- File Paths ---
    parser.add_argument("--runs-file", default=C.DEFAULT_LOCAL_RUNS_FILE, help=f"File to store local run data (default: {C.DEFAULT_LOCAL_RUNS_FILE}).")
    parser.add_argument("--elo-results-file", default=C.DEFAULT_LOCAL_ELO_FILE, help=f"File to store local ELO results and comparisons (default: {C.DEFAULT_LOCAL_ELO_FILE}).")
    parser.add_argument("--leaderboard-runs-file", default=C.CANONICAL_LEADERBOARD_RUNS_FILE, help=f"Path to the canonical leaderboard runs file (read-only, default: {C.CANONICAL_LEADERBOARD_RUNS_FILE}).")
    parser.add_argument("--leaderboard-elo-file", default=C.CANONICAL_LEADERBOARD_ELO_FILE, help=f"Path to the canonical leaderboard ELO file (read-only, default: {C.CANONICAL_LEADERBOARD_ELO_FILE}).")
    # --- Run Control ---
    parser.add_argument("--run-id", help="Optional: Resume or specify a run ID prefix for the local run.")
    parser.add_argument("--threads", type=int, default=4, help="Number of parallel threads for API calls.")
    parser.add_argument("--verbosity", choices=['DEBUG','INFO','WARNING','ERROR','CRITICAL'], default="INFO", help="Logging verbosity level.")
    parser.add_argument("--save-interval", type=int, default=2, help="How often (in tasks) to save partial progress to local files.")
    parser.add_argument("--iterations", type=int, default=1, help="Number of times to run each scenario (for assessing variance).")
    # --- Feature Flags ---
    parser.add_argument(
        "--ignore-canonical",
        action="store_true",
        default=False,
        help="If set, do not load or use default canonical leaderboard files. Runs will be based on local files only."
    )
    parser.add_argument("--no-elo", action="store_true", default=False, help="Disable the ELO analysis step.")
    parser.add_argument("--no-rubric", action="store_true", default=False, help="Disable the Rubric scoring step.")
    parser.add_argument("--redo-rubric-judging", action="store_true", default=False,
                        help="If set, tasks in the local runs file that have completed rubric scoring will be reset so the rubric step is re-run.")
    parser.add_argument(
        "--reset-model",
        action="store_true",
        default=False,
        help="Delete all existing run data and ELO comparisons for the logical model name from the LOCAL files before running.",
    )
    # --- PAL Companion Scenarios ---
    pals_group = parser.add_mutually_exclusive_group()
    pals_group.add_argument("--pals", action="store_true", default=False,
                            help="Run PAL companion scenarios (501-532) only.")
    pals_group.add_argument("--include-pals", action="store_true", default=False,
                            help="Run PAL companion scenarios alongside stock EQ-Bench scenarios.")
    parser.add_argument("--pal-persona", metavar="PATH",
                        help="Path to PAL persona file (Tavus JSON or plain text system prompt). Required with --pals or --include-pals.")
    parser.add_argument("--pal-context", metavar="PATH",
                        help="(Optional) Path to per-session conversational context file to append to the persona system prompt.")
    # --- Removed file path arguments (now handled via constants) ---
    # parser.add_argument("--scenario-prompts-file", ...)
    # parser.add_argument("--debrief-prompt-file", ...)
    # parser.add_argument("--pairwise-prompt-file", ...)
    # parser.add_argument("--rubric-criteria-file", ...)
    # parser.add_argument("--rubric-prompt-file", ...)

    args = parser.parse_args()

    # Validate PAL arguments
    if (args.pals or args.include_pals) and not args.pal_persona:
        parser.error("--pal-persona is required when using --pals or --include-pals.")
    if args.pal_persona and not (args.pals or args.include_pals):
        parser.error("--pal-persona requires either --pals or --include-pals.")
    if args.pal_context and not args.pal_persona:
        parser.error("--pal-context requires --pal-persona.")

    # Determine the logical model name and API model ID
    api_model_id = args.test_model
    logical_model_name = args.model_name if args.model_name else api_model_id

    # Load PAL persona if specified
    pal_persona_config = None
    if args.pal_persona:
        from core.pal_persona import load_pal_persona
        try:
            pal_persona_config = load_pal_persona(args.pal_persona, context_path=args.pal_context)
            logging.info(f"Loaded PAL persona from {args.pal_persona}")
            if pal_persona_config.model:
                logging.info(f"Persona specifies model: {pal_persona_config.model} (using --test-model={api_model_id})")
        except FileNotFoundError as e:
            parser.error(str(e))

    # Setup logging first
    setup_logging(get_verbosity(args.verbosity))

    actual_leaderboard_runs_file = args.leaderboard_runs_file
    actual_leaderboard_elo_file = args.leaderboard_elo_file

    if args.ignore_canonical:
        logging.info("--ignore-canonical flag is set. Canonical leaderboard files will not be loaded or used.")
        actual_leaderboard_runs_file = None # load_json_file will return {} for this
        actual_leaderboard_elo_file = None  # load_json_file will return {} for this
    else:
        # Optional: Check existence and warn if not found, though load_json_file handles it
        if not os.path.exists(args.leaderboard_runs_file):
            logging.warning(f"Canonical leaderboard runs file not found: {args.leaderboard_runs_file}. Will proceed as if empty. Use --ignore-canonical to run purely locally and suppress this warning.")
        if not os.path.exists(args.leaderboard_elo_file):
            logging.warning(f"Canonical leaderboard ELO file not found: {args.leaderboard_elo_file}. Will proceed as if empty. Use --ignore-canonical to run purely locally and suppress this warning.")

    logging.info("--- EQBench3 Run Start ---")
    logging.info(f"Logical Model Name: {logical_model_name}")
    logging.info(f"API Model ID: {api_model_id}")
    logging.info(f"Local Runs File: {args.runs_file}")
    logging.info(f"Local ELO File: {args.elo_results_file}")
    logging.info(f"Leaderboard Runs File (effective): {actual_leaderboard_runs_file if actual_leaderboard_runs_file else 'Ignored'}")
    logging.info(f"Leaderboard ELO File (effective): {actual_leaderboard_elo_file if actual_leaderboard_elo_file else 'Ignored'}")
    logging.debug(f"Full Arguments: {args}")

    if args.reset_model:
        # Reset using the logical model name and LOCAL file paths
        _reset_model_data(logical_model_name, args.runs_file, args.elo_results_file)

    # Validate arguments
    run_elo_flag = not args.no_elo
    run_rubric_flag = not args.no_rubric

    if (run_elo_flag or run_rubric_flag) and not args.judge_model:
        parser.error("--judge-model is required unless both --no-elo and --no-rubric are specified.")
        sys.exit(1)

    # Hook signals for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    run_key = None
    try:
        # Call run_eq_bench3 with logical name, API ID, and all file paths
        run_key = run_eq_bench3(
            model_name=logical_model_name,
            api_model_id=api_model_id,
            judge_model=args.judge_model if (run_elo_flag or run_rubric_flag) else None,
            # File Paths
            local_runs_file=args.runs_file,
            local_elo_file=args.elo_results_file,
            leaderboard_runs_file=actual_leaderboard_runs_file,
            leaderboard_elo_file=actual_leaderboard_elo_file,
            # Run Control
            num_threads=args.threads,
            run_id=args.run_id,
            save_interval=args.save_interval,
            iterations=args.iterations,
            # Feature Flags
            run_elo=run_elo_flag,
            run_rubric=run_rubric_flag,
            redo_judging=args.redo_rubric_judging,
            truncate_for_rubric=False, # Hardcoded for now, could be arg
            # PAL
            run_pals_only=args.pals,
            include_pals=args.include_pals,
            pal_persona_config=pal_persona_config,
        )

        logging.info(f"EQBench3 run completed. Run key: {run_key}")
        print(f"\nEQBench3 benchmark completed. Run key: {run_key}")

    except Exception as e:
        logging.critical(f"An unhandled error occurred during the benchmark run: {e}", exc_info=True)
        print(f"\nFATAL ERROR during benchmark run: {e}")
        if run_key and args.runs_file:
            try:
                # Update status in the LOCAL runs file
                update_run_data(args.runs_file, run_key, {
                    "status": "error",
                    "error": f"Unhandled exception: {str(e)}",
                    "end_time": datetime.now(timezone.utc).isoformat()
                })
                logging.info(f"Marked run {run_key} as errored in {args.runs_file}")
            except Exception as update_e:
                logging.error(f"Could not update run status to error for {run_key}: {update_e}")
        sys.exit(1)

    # Print Summary Box if run completed (even with errors), using LOCAL runs file
    if run_key:        
        # Print Rubric Leaderboard Summary if Rubric scoring was run
        if run_rubric_flag and run_key:
            try:
                logging.info("Loading merged run data for Rubric leaderboard display...")
                # Load final data from both sources, respecting --ignore-canonical
                final_leaderboard_runs = {}
                if not args.ignore_canonical:
                    final_leaderboard_runs = load_json_file(actual_leaderboard_runs_file)
                else:
                    logging.info("Rubric summary: Not loading canonical runs due to --ignore-canonical.")
                final_local_runs = load_json_file(args.runs_file)
                final_merged_runs = {**final_leaderboard_runs, **final_local_runs}

                if final_merged_runs:
                    print_rubric_summary(final_merged_runs, logical_model_name)
                else:
                    logging.warning("Could not load merged run data for Rubric leaderboard display.")
            except Exception as e:
                logging.error(f"Failed to load or print Rubric leaderboard summary: {e}", exc_info=True)
        elif not run_rubric_flag:
            logging.info("Skipping Rubric leaderboard display because Rubric scoring was disabled.")

        # Load run data once for adversarial summary and ELO error check
        final_run_data = load_json_file(args.runs_file).get(run_key, {})

        # Print Adversarial Summary if PAL data is present
        if run_rubric_flag and (args.pals or args.include_pals):
            try:
                adv_results = final_run_data.get("results", {}).get("adversarial_results", {})
                if adv_results:
                    print_adversarial_summary(adv_results)
            except Exception as e:
                logging.error(f"Failed to print adversarial summary: {e}", exc_info=True)

        # Print Leaderboard Summary if ELO was run successfully
        if run_elo_flag:
            elo_step_error = final_run_data.get("results", {}).get("elo_error")

            if not elo_step_error:
                try:
                    logging.info(f"Loading final ELO data from {args.elo_results_file} for leaderboard display.")
                    # Load the local ELO file which now contains the full snapshot
                    final_local_elo_data = load_json_file(args.elo_results_file)
                    if final_local_elo_data:
                        print_leaderboard_summary(final_local_elo_data, logical_model_name)
                    else:
                        logging.warning(f"Could not load local ELO data from {args.elo_results_file} for leaderboard display.")
                except Exception as e:
                    logging.error(f"Failed to load or print leaderboard summary: {e}", exc_info=True)
            else:
                logging.warning(f"Skipping leaderboard display because ELO analysis reported an error: {elo_step_error}")
        else:
            logging.info("Skipping leaderboard display because ELO analysis was disabled.")
            
        print_summary_box(run_key, args.runs_file, run_elo_flag, run_rubric_flag)


if __name__ == "__main__":
    main()