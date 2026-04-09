"""Tests for PAL ELO integration — constants and scenario filtering."""
import os
from utils import constants as C
from core import elo_config


def test_pals_pairwise_prompt_constant_exists():
    """PALS_PAIRWISE_PROMPT_FILE constant must be defined."""
    assert hasattr(C, "PALS_PAIRWISE_PROMPT_FILE")
    assert "pairwise_prompt_eqbench3_pals.txt" in C.PALS_PAIRWISE_PROMPT_FILE


def test_pals_elo_file_constant_exists():
    """DEFAULT_LOCAL_PALS_ELO_FILE constant must be defined."""
    assert hasattr(C, "DEFAULT_LOCAL_PALS_ELO_FILE")
    assert "pals" in C.DEFAULT_LOCAL_PALS_ELO_FILE.lower()


def test_pals_pairwise_prompt_file_exists():
    """The PAL pairwise prompt template file must exist on disk."""
    assert os.path.exists(C.PALS_PAIRWISE_PROMPT_FILE), (
        f"Missing: {C.PALS_PAIRWISE_PROMPT_FILE}"
    )


def test_pals_scenario_notes_global_exists():
    """elo_config must have a pals_scenario_notes dict."""
    assert hasattr(elo_config, "pals_scenario_notes")
    assert isinstance(elo_config.pals_scenario_notes, dict)
