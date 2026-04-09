#!/usr/bin/env python3
"""Tests for PAL persona loading."""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.pal_persona import PalPersonaConfig, load_pal_persona


def test_load_plain_text_persona():
    """A plain text file is treated as a raw system prompt."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
        f.write("You are a friendly companion named Sage.")
        f.flush()
        path = f.name

    try:
        config = load_pal_persona(path)
        assert config.system_prompt == "You are a friendly companion named Sage."
        assert config.greeting is None
        assert config.model is None
        assert config.context is None
        # persona_name derived from filename (temp file name stem)
        assert config.persona_name is not None
        assert config.persona_id is None
    finally:
        os.unlink(path)


def test_load_full_persona_json():
    """A Tavus persona JSON extracts system_prompt, greeting, and model."""
    persona = {
        "persona_id": "p_abc123",
        "persona_name": "Sage",
        "system_prompt": "You are Sage, a warm companion.",
        "greeting": "Hey there! How's your day going?",
        "layers": {
            "llm": {"model": "tavus-gemini-2.5-flash"},
            "tts": {"voice": "alloy"},
        },
        "context": "User prefers morning check-ins.",
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(persona, f)
        f.flush()
        path = f.name

    try:
        config = load_pal_persona(path)
        assert config.system_prompt == "You are Sage, a warm companion."
        assert config.greeting == "Hey there! How's your day going?"
        assert config.model == "tavus-gemini-2.5-flash"
        assert config.context == "User prefers morning check-ins."
        assert config.persona_name == "Sage"
        assert config.persona_id == "p_abc123"
        # display_name should combine persona name with model
        assert config.display_name("gpt-4o") == "Sage (gpt-4o)"
    finally:
        os.unlink(path)


def test_load_minimal_persona_json():
    """A JSON with only system_prompt works; optional fields default to None."""
    persona = {"system_prompt": "You are a coach."}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(persona, f)
        f.flush()
        path = f.name

    try:
        config = load_pal_persona(path)
        assert config.system_prompt == "You are a coach."
        assert config.greeting is None
        assert config.model is None
        assert config.context is None
        # No persona_name in JSON → derived from filename
        assert config.persona_name is not None
        assert config.persona_id is None
    finally:
        os.unlink(path)


def test_load_json_without_system_prompt_falls_back_to_raw():
    """A JSON file without 'system_prompt' key is treated as plain text."""
    data = {"name": "not a persona", "description": "just some json"}
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(data, f)
        f.flush()
        path = f.name

    try:
        config = load_pal_persona(path)
        # Falls back to raw text of the entire file
        assert "not a persona" in config.system_prompt
        assert config.greeting is None
        assert config.model is None
    finally:
        os.unlink(path)


def test_load_persona_with_context_file(tmp_path):
    """Context from a separate file is loaded and attached."""
    persona_file = tmp_path / "persona.txt"
    persona_file.write_text("You are Sage.", encoding="utf-8")

    context_file = tmp_path / "context.txt"
    context_file.write_text("User is feeling anxious today.", encoding="utf-8")

    config = load_pal_persona(str(persona_file), context_path=str(context_file))
    assert config.system_prompt == "You are Sage."
    assert config.context == "User is feeling anxious today."


def test_pal_persona_config_build_system_prompt_no_context():
    """build_system_prompt returns system_prompt unchanged when no context."""
    config = PalPersonaConfig(system_prompt="You are Sage.")
    assert config.build_system_prompt() == "You are Sage."


def test_pal_persona_config_build_system_prompt_with_context():
    """build_system_prompt appends context to system_prompt."""
    config = PalPersonaConfig(
        system_prompt="You are Sage.",
        context="User likes hiking.",
    )
    result = config.build_system_prompt()
    assert result.startswith("You are Sage.")
    assert "User likes hiking." in result


def test_file_not_found_raises():
    """Loading a nonexistent file raises FileNotFoundError."""
    import pytest
    with pytest.raises(FileNotFoundError):
        load_pal_persona("/nonexistent/path/persona.txt")


if __name__ == "__main__":
    test_load_plain_text_persona()
    test_load_full_persona_json()
    test_load_minimal_persona_json()
    test_load_json_without_system_prompt_falls_back_to_raw()
    test_pal_persona_config_build_system_prompt_no_context()
    test_pal_persona_config_build_system_prompt_with_context()
    print("All tests passed!")
