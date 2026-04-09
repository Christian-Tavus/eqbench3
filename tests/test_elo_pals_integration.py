"""Tests for PAL ELO integration — constants and scenario filtering."""
import os
from utils import constants as C
from core import elo_config
from core.elo_helpers import _data_has_all_expected_responses


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


def test_pal_scenario_passes_response_check_with_raw_content():
    """PAL scenarios (NO_RP style) should pass with raw content >= 100 chars."""
    task = {
        "conversation_history": [
            {"role": "user", "content": "Hi there"},
            {"role": "assistant", "content": "A" * 150},
        ],
        "debrief_response": "This was a good conversation about emotions.",
    }
    assert _data_has_all_expected_responses(task, "501") is True


def test_pal_scenario_fails_response_check_with_short_content():
    """PAL scenarios should fail with raw content < 100 chars (strict mode)."""
    task = {
        "conversation_history": [
            {"role": "user", "content": "Hi"},
            {"role": "assistant", "content": "Short"},
        ],
        "debrief_response": "Debrief.",
    }
    # With ALLOW_INCOMPLETE_RESPONSES=True (default), short content fails baseline
    assert _data_has_all_expected_responses(task, "501") is False
