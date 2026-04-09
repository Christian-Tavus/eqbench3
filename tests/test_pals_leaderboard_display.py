"""Tests for PAL ELO leaderboard display."""
from io import StringIO
from unittest.mock import patch

from eqbench3 import print_pals_leaderboard_summary


def test_pals_leaderboard_shows_rankings():
    """PAL ELO leaderboard should show ranked models."""
    elo_data = {
        "persona-v1": {
            "elo": 1250.0,
            "elo_norm": 1350.0,
            "sigma": 90.0,
            "ci_low_norm": 1200.0,
            "ci_high_norm": 1500.0,
        },
        "persona-v2": {
            "elo": 1150.0,
            "elo_norm": 1250.0,
            "sigma": 95.0,
            "ci_low_norm": 1100.0,
            "ci_high_norm": 1400.0,
        },
        "__metadata__": {"global_pairwise_comparisons": []},
    }

    with patch("sys.stdout", new_callable=StringIO) as mock_out:
        print_pals_leaderboard_summary(elo_data, "persona-v1")
        output = mock_out.getvalue()

    assert "PAL" in output, f"PAL title not found in output:\n{output}"
    assert "persona-v1" in output
    assert "persona-v2" in output
    assert "1350" in output  # elo_norm for persona-v1


def test_pals_leaderboard_empty_data():
    """Empty ELO data should print info message, not crash."""
    with patch("sys.stdout", new_callable=StringIO) as mock_out:
        print_pals_leaderboard_summary({}, "test-model")
        output = mock_out.getvalue()

    assert "No" in output or "no" in output  # Some "no data" message
