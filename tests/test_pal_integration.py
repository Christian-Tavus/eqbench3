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


if __name__ == "__main__":
    test_scenario_task_has_system_messages_field()
    test_scenario_task_has_scenario_notes_field()
    test_scenario_task_defaults_none()
    test_scenario_task_roundtrip_serialization()
    test_scenario_task_roundtrip_none_fields()
    print("All tests passed!")
