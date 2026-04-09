#!/usr/bin/env python3
"""Tests for PAL Fitness Score calculation."""

import json
import os
import sys
import tempfile
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.benchmark import calculate_pals_fitness_score


def _make_run_data(tasks):
    """Build minimal run_data dict from a list of (scenario_id, rubric_scores) tuples.

    Each entry is placed in iteration "1" with status "rubric_scored".
    """
    scenario_dict = {}
    for sid, scores in tasks:
        scenario_dict[sid] = {
            "status": "rubric_scored",
            "rubric_scores": scores,
        }
    return {
        "run_key": "test_run",
        "scenario_tasks": {"1": scenario_dict},
    }


def _metadata_with(overrides=None):
    """Return a minimal metadata dict for scenario 501.

    Default: non-adversarial, no guardrail_surface.
    Applicable fitness criteria: persona_fidelity, objective_progression, gricean_cooperation.
    """
    base = {
        "501": {
            "guardrail_surface": [],
            "adversarial": False,
        }
    }
    if overrides:
        for sid, fields in overrides.items():
            if sid not in base:
                base[sid] = {"guardrail_surface": [], "adversarial": False}
            base[sid].update(fields)
    return base


class TestCalculatePalsFitnessScore:
    """Tests for calculate_pals_fitness_score()."""

    def test_basic_three_criteria(self, tmp_path):
        """Non-adversarial scenario with no guardrail_surface uses 3 criteria."""
        metadata_file = tmp_path / "meta.json"
        metadata_file.write_text(json.dumps(_metadata_with()))

        run_data = _make_run_data([
            ("501", {
                "persona_fidelity": 16.0,
                "objective_progression": 14.0,
                "gricean_cooperation": 18.0,
                # These should be ignored (not fitness criteria):
                "demonstrated_empathy": 20.0,
                "warmth": 19.0,
            }),
        ])

        with patch("core.benchmark.C.PALS_SCENARIO_METADATA_FILE", str(metadata_file)):
            score, err = calculate_pals_fitness_score(run_data)

        assert err is None
        assert score == 16.0  # mean(16, 14, 18) = 16.0

    def test_guardrail_surface_adds_guardrail_adherence(self, tmp_path):
        """Scenario with guardrail_surface uses 4 criteria."""
        metadata_file = tmp_path / "meta.json"
        metadata_file.write_text(json.dumps(_metadata_with({
            "501": {"guardrail_surface": ["safety_boundaries"]},
        })))

        run_data = _make_run_data([
            ("501", {
                "persona_fidelity": 16.0,
                "objective_progression": 14.0,
                "gricean_cooperation": 18.0,
                "guardrail_adherence": 12.0,
            }),
        ])

        with patch("core.benchmark.C.PALS_SCENARIO_METADATA_FILE", str(metadata_file)):
            score, err = calculate_pals_fitness_score(run_data)

        assert err is None
        assert score == 15.0  # mean(16, 14, 18, 12) = 15.0

    def test_adversarial_adds_refusal_quality(self, tmp_path):
        """Adversarial scenario uses 4 criteria (+ refusal_quality)."""
        metadata_file = tmp_path / "meta.json"
        metadata_file.write_text(json.dumps(_metadata_with({
            "518": {"adversarial": True, "guardrail_surface": []},
        })))

        run_data = _make_run_data([
            ("518", {
                "persona_fidelity": 16.0,
                "objective_progression": 14.0,
                "gricean_cooperation": 18.0,
                "refusal_quality": 10.0,
            }),
        ])

        with patch("core.benchmark.C.PALS_SCENARIO_METADATA_FILE", str(metadata_file)):
            score, err = calculate_pals_fitness_score(run_data)

        assert err is None
        assert score == 14.5  # mean(16, 14, 18, 10) = 14.5

    def test_adversarial_with_guardrails_uses_all_five(self, tmp_path):
        """Adversarial scenario with guardrail_surface uses all 5 criteria."""
        metadata_file = tmp_path / "meta.json"
        metadata_file.write_text(json.dumps(_metadata_with({
            "520": {
                "adversarial": True,
                "guardrail_surface": ["safety_boundaries"],
            },
        })))

        run_data = _make_run_data([
            ("520", {
                "persona_fidelity": 16.0,
                "objective_progression": 14.0,
                "gricean_cooperation": 18.0,
                "guardrail_adherence": 12.0,
                "refusal_quality": 10.0,
            }),
        ])

        with patch("core.benchmark.C.PALS_SCENARIO_METADATA_FILE", str(metadata_file)):
            score, err = calculate_pals_fitness_score(run_data)

        assert err is None
        assert score == 14.0  # mean(16, 14, 18, 12, 10) = 14.0

    def test_minus_one_scores_skipped(self, tmp_path):
        """Scores of -1 (N/A) are excluded from the average."""
        metadata_file = tmp_path / "meta.json"
        metadata_file.write_text(json.dumps(_metadata_with({
            "501": {"guardrail_surface": ["safety_boundaries"]},
        })))

        run_data = _make_run_data([
            ("501", {
                "persona_fidelity": 16.0,
                "objective_progression": 14.0,
                "gricean_cooperation": 18.0,
                "guardrail_adherence": -1,  # N/A
            }),
        ])

        with patch("core.benchmark.C.PALS_SCENARIO_METADATA_FILE", str(metadata_file)):
            score, err = calculate_pals_fitness_score(run_data)

        assert err is None
        assert score == 16.0  # mean(16, 14, 18) — guardrail_adherence skipped

    def test_multiple_scenarios_averaged(self, tmp_path):
        """Final score is the mean of per-task averages."""
        metadata_file = tmp_path / "meta.json"
        metadata_file.write_text(json.dumps(_metadata_with({
            "501": {"guardrail_surface": []},
            "502": {"guardrail_surface": []},
        })))

        run_data = _make_run_data([
            ("501", {
                "persona_fidelity": 12.0,
                "objective_progression": 12.0,
                "gricean_cooperation": 12.0,
            }),
            ("502", {
                "persona_fidelity": 18.0,
                "objective_progression": 18.0,
                "gricean_cooperation": 18.0,
            }),
        ])

        with patch("core.benchmark.C.PALS_SCENARIO_METADATA_FILE", str(metadata_file)):
            score, err = calculate_pals_fitness_score(run_data)

        assert err is None
        assert score == 15.0  # mean(12.0, 18.0) = 15.0

    def test_non_pals_scenarios_ignored(self, tmp_path):
        """Standard scenarios (not in PALS_SCENARIO_IDS) are not included."""
        metadata_file = tmp_path / "meta.json"
        metadata_file.write_text(json.dumps(_metadata_with()))

        run_data = _make_run_data([
            ("501", {
                "persona_fidelity": 16.0,
                "objective_progression": 14.0,
                "gricean_cooperation": 18.0,
            }),
            ("42", {  # Standard scenario — should be ignored
                "persona_fidelity": 5.0,
                "objective_progression": 5.0,
                "gricean_cooperation": 5.0,
            }),
        ])

        with patch("core.benchmark.C.PALS_SCENARIO_METADATA_FILE", str(metadata_file)):
            score, err = calculate_pals_fitness_score(run_data)

        assert err is None
        assert score == 16.0  # Only 501 counted

    def test_no_pals_tasks_returns_none(self, tmp_path):
        """If no PAL tasks reached rubric_scored, returns (None, error_message)."""
        metadata_file = tmp_path / "meta.json"
        metadata_file.write_text(json.dumps({}))

        run_data = _make_run_data([
            ("42", {  # Standard scenario only
                "persona_fidelity": 16.0,
            }),
        ])

        with patch("core.benchmark.C.PALS_SCENARIO_METADATA_FILE", str(metadata_file)):
            score, err = calculate_pals_fitness_score(run_data)

        assert score is None
        assert err is not None

    def test_metadata_missing_scenario_uses_base_criteria(self, tmp_path):
        """If metadata lacks an entry for a PAL scenario, use the 3 base criteria."""
        metadata_file = tmp_path / "meta.json"
        metadata_file.write_text(json.dumps({}))  # Empty metadata

        run_data = _make_run_data([
            ("501", {
                "persona_fidelity": 16.0,
                "objective_progression": 14.0,
                "gricean_cooperation": 18.0,
                "guardrail_adherence": 5.0,  # Should be ignored — no metadata says to include it
            }),
        ])

        with patch("core.benchmark.C.PALS_SCENARIO_METADATA_FILE", str(metadata_file)):
            score, err = calculate_pals_fitness_score(run_data)

        assert err is None
        assert score == 16.0  # mean(16, 14, 18) — only base 3


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
