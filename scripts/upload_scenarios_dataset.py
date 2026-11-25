"""Upload the 32 PAL scenarios as a Braintrust dataset in the PalBench project.

Rows are keyed by stable ids (pal-scenario-<id>) so re-runs upsert instead of
duplicating. Zero model spend: this only parses local data files and uploads.

Usage:
  python scripts/upload_scenarios_dataset.py [--project PalBench] [--dataset pal-scenarios] [--dry-run]
"""
import argparse
import json
import os
import re
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROMPTS_FILE = os.path.join(REPO_ROOT, "data", "pals_scenario_prompts.txt")
META_FILE = os.path.join(REPO_ROOT, "data", "pals_scenario_metadata.json")

_HEADER_RE = re.compile(r"^########\s+(\d+)\s*\|", re.MULTILINE)
_PROMPT_SPLIT_RE = re.compile(r"^#######\s+Prompt\d+\s*$", re.MULTILINE)


def parse_pals_prompts(text):
    """{scenario_id: [canned user turns]} from pals_scenario_prompts.txt."""
    prompts_by_id = {}
    chunks = _HEADER_RE.split(text)
    # chunks: [preamble, id1, body1, id2, body2, ...]
    for scenario_id, body in zip(chunks[1::2], chunks[2::2]):
        turns = [t.strip() for t in _PROMPT_SPLIT_RE.split(body) if t.strip()]
        # first fragment is the remainder of the header line (subdomain etc.)
        prompts_by_id[scenario_id] = turns[1:] if len(turns) > 1 else turns
    return prompts_by_id


def build_dataset_rows(prompts_by_id, meta_by_id):
    rows = []
    for scenario_id, prompts in sorted(prompts_by_id.items(), key=lambda kv: kv[0]):
        meta = meta_by_id.get(scenario_id, {})
        pass_condition = meta.get("pass_condition")
        rows.append(
            {
                "id": f"pal-scenario-{scenario_id}",
                "input": {"scenario_id": scenario_id, "prompts": prompts},
                "expected": {"pass_condition": pass_condition} if pass_condition else None,
                "metadata": {
                    "domain": meta.get("domain"),
                    "subdomain": meta.get("subdomain"),
                    "adversarial": bool(meta.get("adversarial")),
                    "guardrail_surface": meta.get("guardrail_surface") or [],
                    "eval_dimensions": meta.get("eval_dimensions") or [],
                },
            }
        )
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", default="PalBench")
    parser.add_argument("--dataset", default="pal-scenarios")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
        prompts_by_id = parse_pals_prompts(f.read())
    with open(META_FILE, "r", encoding="utf-8") as f:
        meta_by_id = json.load(f)

    rows = build_dataset_rows(prompts_by_id, meta_by_id)
    adversarial = sum(1 for r in rows if r["metadata"]["adversarial"])
    print(f"{len(rows)} scenarios parsed ({adversarial} adversarial)")

    if args.dry_run:
        for r in rows[:3]:
            print(json.dumps(r, indent=2)[:400])
        return

    import braintrust

    dataset = braintrust.init_dataset(project=args.project, name=args.dataset)
    for row in rows:
        dataset.insert(
            input=row["input"],
            expected=row["expected"],
            metadata=row["metadata"],
            id=row["id"],
        )
    print(dataset.summarize())
    dataset.flush()


if __name__ == "__main__":
    main()
