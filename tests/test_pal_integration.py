#!/usr/bin/env python3
"""Integration tests for PAL scenario pipeline wiring."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.conversation import ScenarioTask


def test_scenario_task_has_system_messages_field():
    """ScenarioTask accepts and stores system_messages."""
    task = ScenarioTask(
        scenario_id="501",
        prompts=["Hello"],
        debrief_prompt="Debrief now.",
        iteration_index=1,
        test_model="test-model",
        master_prompt_template="{scenario_prompt}",
        system_messages=[{"role": "system", "content": "You are Sage."}],
    )
    assert task.system_messages == [{"role": "system", "content": "You are Sage."}]


def test_scenario_task_has_scenario_notes_field():
    """ScenarioTask accepts and stores scenario_notes."""
    task = ScenarioTask(
        scenario_id="501",
        prompts=["Hello"],
        debrief_prompt="Debrief now.",
        iteration_index=1,
        test_model="test-model",
        scenario_notes="This scenario tests empathy.",
    )
    assert task.scenario_notes == "This scenario tests empathy."


def test_scenario_task_defaults_none():
    """system_messages and scenario_notes default to None."""
    task = ScenarioTask(
        scenario_id="501",
        prompts=["Hello"],
        debrief_prompt="Debrief now.",
        iteration_index=1,
        test_model="test-model",
    )
    assert task.system_messages is None
    assert task.scenario_notes is None


def test_scenario_task_roundtrip_serialization():
    """system_messages and scenario_notes survive to_dict/from_dict."""
    task = ScenarioTask(
        scenario_id="501",
        prompts=["Hello"],
        debrief_prompt="Debrief now.",
        iteration_index=1,
        test_model="test-model",
        system_messages=[{"role": "system", "content": "You are Sage."}],
        scenario_notes="This scenario tests empathy.",
    )
    data = task.to_dict()
    restored = ScenarioTask.from_dict(data)
    assert restored.system_messages == [{"role": "system", "content": "You are Sage."}]
    assert restored.scenario_notes == "This scenario tests empathy."


def test_scenario_task_roundtrip_none_fields():
    """None system_messages and scenario_notes survive to_dict/from_dict."""
    task = ScenarioTask(
        scenario_id="1",
        prompts=["Hello"],
        debrief_prompt="Debrief now.",
        iteration_index=1,
        test_model="test-model",
    )
    data = task.to_dict()
    restored = ScenarioTask.from_dict(data)
    assert restored.system_messages is None
    assert restored.scenario_notes is None


def test_prepare_rubric_prompt_includes_scenario_notes():
    """PAL rubric prompt formatting includes scenario_notes."""
    task = ScenarioTask(
        scenario_id="501",
        prompts=["Hi there"],
        debrief_prompt="Debrief.",
        iteration_index=1,
        test_model="test-model",
        scenario_notes="This scenario tests empathy under pressure.",
    )
    # Simulate a completed conversation
    task.conversation_history = [
        {"role": "user", "content": "Hi there"},
        {"role": "assistant", "content": "Hey! How are you doing today?"},
    ]
    task.parsed_responses = [{"raw": "Hey! How are you doing today?"}]
    task.debrief_response = "I handled the conversation well."

    # Use a template that includes {scenario_notes}
    template = "Transcript:\n{transcript}\nDebrief:\n{debrief}\nNotes:\n{scenario_notes}\nFormat:\n{output_format}"
    result = task.prepare_rubric_prompt_text(template, '{"score": "0-20"}', False)

    assert result is not None
    assert "This scenario tests empathy under pressure." in result


if __name__ == "__main__":
    test_scenario_task_has_system_messages_field()
    test_scenario_task_has_scenario_notes_field()
    test_scenario_task_defaults_none()
    test_scenario_task_roundtrip_serialization()
    test_scenario_task_roundtrip_none_fields()
    test_prepare_rubric_prompt_includes_scenario_notes()
    print("All tests passed!")
