#!/usr/bin/env python3
"""Merge batched PALs-Bench data files into canonical single files.

Produces:
  data/pals_scenario_prompts.txt
  data/pals_scenario_notes.txt
  data/pals_scenario_metadata.json
"""

import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


def merge_text_files(sources: list[str], output: str):
    """Concatenate text files with a blank line between each."""
    merged = []
    for src in sources:
        path = os.path.join(DATA_DIR, src)
        with open(path, "r", encoding="utf-8") as f:
            content = f.read().rstrip("\n")
        merged.append(content)

    out_path = os.path.join(DATA_DIR, output)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(merged) + "\n")
    print(f"Created {out_path} ({len(merged)} sources merged)")


def merge_metadata_files(sources: list[str], output: str):
    """Merge JSON metadata files into a single dict, sorted by ID."""
    combined = {}
    for src in sources:
        path = os.path.join(DATA_DIR, src)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Check for duplicate keys
        overlap = set(combined.keys()) & set(data.keys())
        if overlap:
            raise ValueError(f"Duplicate IDs across files: {overlap}")
        combined.update(data)

    # Sort by numeric ID
    sorted_combined = dict(sorted(combined.items(), key=lambda x: int(x[0])))

    out_path = os.path.join(DATA_DIR, output)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(sorted_combined, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Created {out_path} ({len(sorted_combined)} entries)")


if __name__ == "__main__":
    print("Merging prompt files...")
    merge_text_files(
        ["scenarios_501-508_prompts.txt",
         "scenarios_509-517_prompts.txt",
         "adversarial_scenario_prompts.txt"],
        "pals_scenario_prompts.txt",
    )

    print("Merging notes files...")
    merge_text_files(
        ["scenarios_501-508_notes.txt",
         "scenarios_509-517_notes.txt",
         "adversarial_scenario_notes.txt"],
        "pals_scenario_notes.txt",
    )

    print("Merging metadata files...")
    merge_metadata_files(
        ["scenarios_501-508_metadata.json",
         "scenarios_509-517_metadata.json",
         "adversarial_scenario_metadata.json"],
        "pals_scenario_metadata.json",
    )

    print("\nDone. Run 'python tests/validate_pals_data.py' to verify.")
