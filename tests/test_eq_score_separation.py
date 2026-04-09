"""Tests that PAL scenarios are excluded from the standard EQ Score calculation."""
import json
import statistics
from unittest.mock import patch, mock_open
from core.benchmark import calculate_final_rubric_score
from utils import constants as C


def _make_run_data(scenario_tasks_iter1: dict) -> dict:
    """Helper to build minimal run_data with one iteration."""
    return {
        "run_key": "test_separation",
        "scenario_tasks": {"1": scenario_tasks_iter1},
    }


def test_standard_eq_score_excludes_pal_scenarios():
    """PAL scenario scores must NOT appear in the standard EQ score."""
    standard_task = {
        "status": "rubric_scored",
        "rubric_scores": {
            "demonstrated_empathy": 16.0,
            "pragmatic_ei": 14.0,
            "depth_of_insight": 12.0,
            "social_dexterity": 15.0,
            "emotional_reasoning": 13.0,
            "message_tailoring": 14.0,
            "theory_of_mind": 15.0,
            "subtext_identification": 11.0,
            "intellectual_grounding": 14.0,
            "correctness": 16.0,
        },
    }
    pal_task = {
        "status": "rubric_scored",
        "rubric_scores": {
            "demonstrated_empathy": 5.0,
            "pragmatic_ei": 5.0,
            "depth_of_insight": 5.0,
            "social_dexterity": 5.0,
            "emotional_reasoning": 5.0,
            "message_tailoring": 5.0,
            "theory_of_mind": 5.0,
            "subtext_identification": 5.0,
            "intellectual_grounding": 5.0,
            "correctness": 5.0,
        },
    }
    tasks = {"1": standard_task, "501": pal_task}
    run_data = _make_run_data(tasks)

    mock_analysis_criteria = "analytical_reasoning\ndata_interpretation\n"
    with patch("builtins.open", mock_open(read_data=mock_analysis_criteria)):
        score, err = calculate_final_rubric_score(run_data)

    assert err is None
    assert score is not None
    assert score > 13.0, f"Score {score} is too low — PAL scenario may be leaking in"


def test_pals_only_run_returns_none_for_standard_eq():
    """When only PAL scenarios are present, standard EQ score should be None."""
    pal_task = {
        "status": "rubric_scored",
        "rubric_scores": {"demonstrated_empathy": 15.0, "persona_fidelity": 16.0},
    }
    tasks = {"501": pal_task, "510": pal_task}
    run_data = _make_run_data(tasks)

    mock_analysis_criteria = "analytical_reasoning\n"
    with patch("builtins.open", mock_open(read_data=mock_analysis_criteria)):
        score, err = calculate_final_rubric_score(run_data)

    assert score is None
    assert err is not None
