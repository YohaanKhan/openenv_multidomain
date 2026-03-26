from benchmarks.run_saas_transformers import _render_prompt, _resolve_model_label


class _FakeTokenizer:
    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=False):
        assert tokenize is False
        assert add_generation_prompt is True
        return "CHAT_TEMPLATE_PROMPT"


def test_resolve_model_label_prefers_adapter_name():
    assert (
        _resolve_model_label(
            "Qwen/Qwen2.5-1.5B-Instruct",
            "artifacts/checkpoints/qwen25_saas_sft_smoke",
        )
        == "qwen25_saas_sft_smoke"
    )


def test_resolve_model_label_uses_model_when_no_adapter():
    assert _resolve_model_label("Qwen/Qwen2.5-1.5B-Instruct", None) == "Qwen/Qwen2.5-1.5B-Instruct"


def test_render_prompt_uses_chat_template_when_available():
    prompt = _render_prompt(
        _FakeTokenizer(),
        [
            {"role": "system", "content": "Return JSON."},
            {"role": "user", "content": "Do the task."},
        ],
    )
    assert prompt == "CHAT_TEMPLATE_PROMPT"


def test_render_prompt_has_string_fallback():
    prompt = _render_prompt(
        object(),
        [
            {"role": "system", "content": "Return JSON."},
            {"role": "user", "content": "Do the task."},
        ],
    )
    assert "SYSTEM:\nReturn JSON." in prompt
    assert "USER:\nDo the task." in prompt
    assert prompt.endswith("ASSISTANT:")
