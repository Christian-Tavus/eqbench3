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


from unittest.mock import patch, MagicMock
from core.pairwise_judging import do_pairwise_judge


def test_pairwise_judge_uses_pals_notes_for_pal_scenario():
    """do_pairwise_judge should use pals_scenario_notes for PAL scenario IDs."""
    from core import elo_config

    # Set up notes
    elo_config.scenario_notes["501"] = "standard note"
    elo_config.pals_scenario_notes["501"] = "PAL-specific note for 501"

    template = (
        "{conversation_history_A}\n{debrief_A}\n"
        "{conversation_history_B}\n{debrief_B}\n"
        "{scenario_notes}\n{scenario_description}"
    )

    mock_api = MagicMock()
    mock_api.generate.return_value = '{"chain_of_thought_reasoning": "test", "persona_fidelity": "A0493+"}'

    result = do_pairwise_judge(
        scenario_id="501",
        scenario_desc="Test PAL scenario",
        history_A=[{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hello!"}],
        debrief_A="Debrief A",
        history_B=[{"role": "user", "content": "Hi"}, {"role": "assistant", "content": "Hey!"}],
        debrief_B="Debrief B",
        pairwise_prompt_template=template,
        judge_model="test-judge",
        api_clients={"judge": mock_api},
    )

    # Verify the judge was called with PAL-specific notes
    call_args = mock_api.generate.call_args
    prompt_sent = call_args[1]["messages"][0]["content"] if "messages" in call_args[1] else call_args[0][0]
    assert "PAL-specific note for 501" in str(call_args)

    # Clean up
    elo_config.scenario_notes.pop("501", None)
    elo_config.pals_scenario_notes.pop("501", None)
