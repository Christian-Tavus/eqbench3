#!/usr/bin/env python3
"""Validate merged PALs-Bench data files.

Checks:
  - pals_scenario_prompts.txt: 32 scenarios (501-532), each with >= 3 turns
  - pals_scenario_notes.txt: 32 entries (501-532), each non-empty
  - pals_scenario_metadata.json: 32 entries with required fields and correct types
"""

import json
import os
import re
import sys

# Add project root to path so we can import from core/
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from core.benchmark import parse_scenario_prompts

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
EXPECTED_IDS = {str(i) for i in range(501, 533)}  # 501-532 inclusive = 32 scenarios
REQUIRED_METADATA_FIELDS = {
    "domain": str,
    "subdomain": str,
    "guardrail_surface": list,
    "eval_dimensions": list,
    "pass_condition": (str, type(None)),
    "adversarial": bool,
}

errors = []


def check(condition: bool, msg: str):
    if not condition:
        errors.append(msg)
        print(f"  FAIL: {msg}")
    else:
        print(f"  OK:   {msg}")


def validate_prompts():
    print("\n=== Validating pals_scenario_prompts.txt ===")
    prompts_file = os.path.join(DATA_DIR, "pals_scenario_prompts.txt")
    check(os.path.exists(prompts_file), f"File exists: {prompts_file}")
    if not os.path.exists(prompts_file):
        return

    scenarios = parse_scenario_prompts(prompts_file)
    check(len(scenarios) == 32, f"Scenario count: {len(scenarios)} (expected 32)")
    check(set(scenarios.keys()) == EXPECTED_IDS,
          f"Scenario IDs match 501-532: missing={EXPECTED_IDS - set(scenarios.keys())}, extra={set(scenarios.keys()) - EXPECTED_IDS}")

    for sid in sorted(scenarios.keys(), key=int):
        turns = len(scenarios[sid])
        check(turns >= 3, f"Scenario {sid}: {turns} turns (>= 3 required)")


def validate_notes():
    print("\n=== Validating pals_scenario_notes.txt ===")
    notes_file = os.path.join(DATA_DIR, "pals_scenario_notes.txt")
    check(os.path.exists(notes_file), f"File exists: {notes_file}")
    if not os.path.exists(notes_file):
        return

    with open(notes_file, "r", encoding="utf-8") as f:
        content = f.read()

    # Parse notes: split on "# NNN" headers
    note_ids = set()
    sections = re.split(r"^# (\d+)\s*$", content, flags=re.MULTILINE)
    # sections[0] is text before first header (should be empty/whitespace)
    # then alternating: id, text, id, text, ...
    for i in range(1, len(sections), 2):
        sid = sections[i].strip()
        note_text = sections[i + 1].strip() if i + 1 < len(sections) else ""
        note_ids.add(sid)
        check(len(note_text) >= 50, f"Note {sid}: {len(note_text)} chars (>= 50 required)")

    check(note_ids == EXPECTED_IDS,
          f"Note IDs match 501-532: missing={EXPECTED_IDS - note_ids}, extra={note_ids - EXPECTED_IDS}")


def validate_metadata():
    print("\n=== Validating pals_scenario_metadata.json ===")
    meta_file = os.path.join(DATA_DIR, "pals_scenario_metadata.json")
    check(os.path.exists(meta_file), f"File exists: {meta_file}")
    if not os.path.exists(meta_file):
        return

    with open(meta_file, "r", encoding="utf-8") as f:
        metadata = json.load(f)

    check(len(metadata) == 32, f"Metadata entry count: {len(metadata)} (expected 32)")
    check(set(metadata.keys()) == EXPECTED_IDS,
          f"Metadata IDs match 501-532: missing={EXPECTED_IDS - set(metadata.keys())}, extra={set(metadata.keys()) - EXPECTED_IDS}")

    for sid in sorted(metadata.keys(), key=int):
        entry = metadata[sid]
        for field, expected_type in REQUIRED_METADATA_FIELDS.items():
            check(field in entry, f"Metadata {sid}: has field '{field}'")
            if field in entry:
                if isinstance(expected_type, tuple):
                    check(isinstance(entry[field], expected_type),
                          f"Metadata {sid}.{field}: type {type(entry[field]).__name__} in {[t.__name__ for t in expected_type]}")
                else:
                    check(isinstance(entry[field], expected_type),
                          f"Metadata {sid}.{field}: type {type(entry[field]).__name__} == {expected_type.__name__}")

    # Check adversarial scenarios have pass_condition
    for sid in sorted(metadata.keys(), key=int):
        entry = metadata[sid]
        if entry.get("adversarial"):
            check(entry.get("pass_condition") is not None,
                  f"Metadata {sid}: adversarial=true has non-null pass_condition")


def validate_rubric_files():
    print("\n=== Validating rubric and debrief files ===")

    # --- rubric_scoring_criteria_pals.txt ---
    criteria_file = os.path.join(DATA_DIR, "rubric_scoring_criteria_pals.txt")
    check(os.path.exists(criteria_file), f"File exists: {criteria_file}")
    if not os.path.exists(criteria_file):
        return

    with open(criteria_file, "r", encoding="utf-8") as f:
        criteria_lines = [line.strip() for line in f if line.strip()]
    check(len(criteria_lines) == 23,
          f"Criteria line count: {len(criteria_lines)} (expected 23)")

    pal_criteria = {
        "persona_fidelity", "guardrail_adherence", "objective_progression",
        "refusal_quality", "gricean_cooperation",
    }
    for crit in sorted(pal_criteria):
        check(crit in criteria_lines, f"PAL criterion present: {crit}")

    # --- rubric_scoring_prompt_pals.txt ---
    prompt_file = os.path.join(DATA_DIR, "rubric_scoring_prompt_pals.txt")
    check(os.path.exists(prompt_file), f"File exists: {prompt_file}")
    if os.path.exists(prompt_file):
        with open(prompt_file, "r", encoding="utf-8") as f:
            prompt_content = f.read()
        required_placeholders = ["{transcript}", "{debrief}", "{scenario_notes}", "{output_format}"]
        for ph in required_placeholders:
            check(ph in prompt_content, f"Rubric prompt contains placeholder: {ph}")

    # --- debrief_prompt_pals.txt ---
    debrief_file = os.path.join(DATA_DIR, "debrief_prompt_pals.txt")
    check(os.path.exists(debrief_file), f"File exists: {debrief_file}")
    if os.path.exists(debrief_file):
        with open(debrief_file, "r", encoding="utf-8") as f:
            debrief_content = f.read()
        check(len(debrief_content) >= 100,
              f"Debrief prompt length: {len(debrief_content)} chars (>= 100 required)")


def validate_constants():
    print("\n=== Validating utils.constants ===")
    from utils import constants as C

    # PALS_SCENARIO_IDS count
    check(len(C.PALS_SCENARIO_IDS) == 32,
          f"PALS_SCENARIO_IDS count: {len(C.PALS_SCENARIO_IDS)} (expected 32)")

    # PALS_ADVERSARIAL_SCENARIO_IDS count
    check(len(C.PALS_ADVERSARIAL_SCENARIO_IDS) == 16,
          f"PALS_ADVERSARIAL_SCENARIO_IDS count: {len(C.PALS_ADVERSARIAL_SCENARIO_IDS)} (expected 16)")

    # Adversarial is subset of all PALs
    check(C.PALS_ADVERSARIAL_SCENARIO_IDS.issubset(C.PALS_SCENARIO_IDS),
          "PALS_ADVERSARIAL_SCENARIO_IDS is a subset of PALS_SCENARIO_IDS")

    # No overlap with other scenario sets
    other_ids = C.NO_RP_SCENARIO_IDS | C.MESSAGE_DRAFTING_SCENARIO_IDS | C.ANALYSIS_SCENARIO_IDS
    overlap = C.PALS_SCENARIO_IDS & other_ids
    check(len(overlap) == 0,
          f"No overlap with NO_RP | MESSAGE_DRAFTING | ANALYSIS: overlap={overlap}")

    # Required file-path attributes
    required_attrs = [
        "PALS_SCENARIO_PROMPTS_FILE",
        "PALS_SCENARIO_NOTES_FILE",
        "PALS_SCENARIO_METADATA_FILE",
        "PALS_RUBRIC_CRITERIA_FILE",
        "PALS_RUBRIC_PROMPT_FILE",
        "PALS_DEBRIEF_PROMPT_FILE",
        "PALS_MASTER_PROMPT_FILE",
    ]
    for attr in required_attrs:
        check(hasattr(C, attr), f"constants.{attr} exists")


if __name__ == "__main__":
    validate_prompts()
    validate_notes()
    validate_metadata()
    validate_rubric_files()
    validate_constants()

    print(f"\n{'='*50}")
    if errors:
        print(f"FAILED: {len(errors)} error(s)")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print("ALL CHECKS PASSED")
        sys.exit(0)
