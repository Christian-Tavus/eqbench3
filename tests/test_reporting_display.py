"""Tests for PAL-specific display output in eqbench3.py."""
import json
import os
import tempfile
from unittest.mock import patch
from io import StringIO

from eqbench3 import print_summary_box, print_rubric_summary


def _write_runs_file(runs_data: dict) -> str:
    """Write runs data to a temp file and return the path."""
    fd, path = tempfile.mkstemp(suffix=".json")
    with os.fdopen(fd, "w") as f:
        json.dump(runs_data, f)
    return path


def test_summary_box_shows_pals_fitness_score():
    """PAL Fitness Score should appear in the summary box when present."""
    runs = {
        "test_run": {
            "model_name": "test-model",
            "api_model_id": "test-model-api",
            "judge_model": "judge-model",
            "status": "completed",
            "start_time": "2026-04-09T10:00:00+00:00",
            "end_time": "2026-04-09T10:30:00+00:00",
            "results": {
                "average_rubric_score": 14.5,
                "pals_fitness_score": 16.2,
                "adversarial_pass_rate": "12/16",
            },
        }
    }
    path = _write_runs_file(runs)
    try:
        with patch("sys.stdout", new_callable=StringIO) as mock_out:
            print_summary_box("test_run", path, run_elo=False, run_rubric=True)
            output = mock_out.getvalue()

        assert "PAL Fitness" in output, f"PAL Fitness Score not found in output:\n{output}"
        assert "81.00" in output, f"Scaled PAL fitness (16.2*5=81.0) not found:\n{output}"
        assert "12/16" in output, f"Adversarial pass rate not found:\n{output}"
    finally:
        os.unlink(path)


def test_summary_box_omits_pals_when_not_present():
    """When no PAL data exists, PAL rows should not appear."""
    runs = {
        "test_run": {
            "model_name": "test-model",
            "api_model_id": "test-model-api",
            "status": "completed",
            "start_time": "2026-04-09T10:00:00+00:00",
            "end_time": "2026-04-09T10:30:00+00:00",
            "results": {
                "average_rubric_score": 14.5,
            },
        }
    }
    path = _write_runs_file(runs)
    try:
        with patch("sys.stdout", new_callable=StringIO) as mock_out:
            print_summary_box("test_run", path, run_elo=False, run_rubric=True)
            output = mock_out.getvalue()

        assert "PAL Fitness" not in output, f"PAL rows should be absent:\n{output}"
        assert "Adversarial" not in output, f"Adversarial row should be absent:\n{output}"
    finally:
        os.unlink(path)


def test_rubric_summary_shows_pals_fitness_column():
    """When any run has PAL data, show a PAL Fitness column."""
    runs = {
        "run_a": {
            "model_name": "model-a",
            "results": {
                "average_rubric_score": 14.0,
                "pals_fitness_score": 16.0,
            },
        },
        "run_b": {
            "model_name": "model-b",
            "results": {
                "average_rubric_score": 12.0,
            },
        },
    }

    with patch("sys.stdout", new_callable=StringIO) as mock_out:
        print_rubric_summary(runs, "model-a")
        output = mock_out.getvalue()

    assert "PAL Fitness" in output, f"PAL Fitness column header not found:\n{output}"
    assert "80.0" in output, f"model-a PAL score (16*5=80) not found:\n{output}"


def test_rubric_summary_no_pals_column_when_absent():
    """When no runs have PAL data, don't show the PAL column."""
    runs = {
        "run_a": {
            "model_name": "model-a",
            "results": {"average_rubric_score": 14.0},
        },
    }

    with patch("sys.stdout", new_callable=StringIO) as mock_out:
        print_rubric_summary(runs, "model-a")
        output = mock_out.getvalue()

    assert "PAL Fitness" not in output, f"PAL column should be absent:\n{output}"
