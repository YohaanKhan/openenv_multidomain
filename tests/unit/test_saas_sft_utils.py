import json

from benchmarks.saas_sft_utils import (
    EXPERT_EPISODES,
    SFT_SYSTEM_INSTRUCTION,
    dataset_task_order,
    format_chat_example,
    make_target_json,
)


def test_dataset_task_order_matches_expert_tasks():
    assert dataset_task_order() == sorted(EXPERT_EPISODES.keys())


def test_format_chat_example_appends_assistant_prompt():
    prompt = format_chat_example(
        [
            {"role": "system", "content": SFT_SYSTEM_INSTRUCTION},
            {"role": "user", "content": "Task details"},
        ]
    )
    assert "SYSTEM:" in prompt
    assert "USER:" in prompt
    assert prompt.endswith("ASSISTANT:")


def test_make_target_json_uses_expected_action_shape():
    target = make_target_json(EXPERT_EPISODES["saas_easy"][0])
    payload = json.loads(target)
    assert set(payload.keys()) == {"tool_name", "tool_args", "thought"}
    assert payload["tool_name"] == "search_tickets"
    assert payload["tool_args"]["customer_id"] == "C-1042"
