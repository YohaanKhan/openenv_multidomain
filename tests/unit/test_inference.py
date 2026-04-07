from __future__ import annotations

import unittest
import os
from io import StringIO
from types import SimpleNamespace
from unittest.mock import Mock, patch

from inference import run_all_tasks, run_episode


class RunEpisodeTests(unittest.TestCase):
    def test_falls_back_when_json_mode_request_fails(self) -> None:
        initial = SimpleNamespace(
            observation=SimpleNamespace(content="start", info={"task_id": "saas_easy", "grader_score": None}),
            done=False,
        )
        terminal = SimpleNamespace(
            observation=SimpleNamespace(content="done", info={"grader_score": 0.8}),
            reward=0.8,
            done=True,
        )
        env = SimpleNamespace(
            reset=Mock(return_value=initial),
            step=Mock(return_value=terminal),
        )

        text_response = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"tool_name":"done","tool_args":{},"thought":"finish"}'))]
        )
        create = Mock(side_effect=[RuntimeError("json mode unsupported"), text_response])
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))

        stdout = StringIO()
        with patch("sys.stdout", stdout):
            score, steps, rewards, success = run_episode(
                env, client, {"id": "saas_easy", "difficulty": "easy"}, "saas"
            )

        self.assertEqual(score, 0.8)
        self.assertEqual(steps, 1)
        self.assertEqual(rewards, [0.8])
        self.assertTrue(success)
        self.assertEqual(create.call_count, 2)
        self.assertEqual(env.step.call_count, 1)
        self.assertIn("[STEP] step=1", stdout.getvalue())
        self.assertIn("reward=0.80", stdout.getvalue())
        self.assertIn("done=true", stdout.getvalue())
        self.assertIn("error=null", stdout.getvalue())
        self.assertIn('"tool_name": "done"', stdout.getvalue())

    def test_returns_zero_when_llm_request_keeps_failing(self) -> None:
        initial = SimpleNamespace(
            observation=SimpleNamespace(content="start", info={"task_id": "saas_easy", "grader_score": None}),
            done=False,
        )
        env = SimpleNamespace(
            reset=Mock(return_value=initial),
            step=Mock(),
        )
        create = Mock(side_effect=RuntimeError("network down"))
        client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))

        score, steps, rewards, success = run_episode(
            env, client, {"id": "saas_easy", "difficulty": "easy"}, "saas"
        )

        self.assertEqual(score, 0.0)
        self.assertEqual(steps, 1)
        self.assertEqual(rewards, [])
        self.assertFalse(success)
        env.step.assert_not_called()


class RunAllTasksTests(unittest.TestCase):
    def test_records_zero_if_a_task_raises(self) -> None:
        fake_tasks = [
            {"id": "saas_easy", "difficulty": "easy"},
            {"id": "saas_medium", "difficulty": "medium"},
        ]
        fake_domain = SimpleNamespace(get_tasks=lambda: fake_tasks)

        class FakeEnv:
            def sync(self) -> "FakeEnv":
                return self

            def close(self) -> None:
                return None

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}), patch(
            "inference.OPENAI_API_KEY", "test-key"
        ), patch("inference.OpenAI", return_value=object()), patch(
            "inference.DomainRegistry.require", return_value=lambda: fake_domain
        ), patch("inference.MultiDomainEnv", return_value=FakeEnv()), patch(
            "inference.run_episode", side_effect=[(0.9, 2, [0.4, 0.5], True), RuntimeError("boom")]
        ):
            scores = run_all_tasks("saas")

        self.assertEqual(scores, {"saas_easy": 0.9, "saas_medium": 0.0})

    def test_retries_task_after_environment_failure(self) -> None:
        fake_tasks = [{"id": "saas_easy", "difficulty": "easy"}]
        fake_domain = SimpleNamespace(get_tasks=lambda: fake_tasks)

        class FakeEnv:
            def sync(self) -> "FakeEnv":
                return self

            def close(self) -> None:
                return None

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}), patch(
            "inference.OPENAI_API_KEY", "test-key"
        ), patch("inference.ENV_RETRY_ATTEMPTS", 3), patch(
            "inference.ENV_RETRY_BACKOFF_S", 0
        ), patch("inference.time.sleep"), patch(
            "inference.OpenAI", return_value=object()
        ), patch(
            "inference.DomainRegistry.require", return_value=lambda: fake_domain
        ), patch(
            "inference.MultiDomainEnv", return_value=FakeEnv()
        ), patch(
            "inference.run_episode", side_effect=[RuntimeError("ws closed"), (0.6, 3, [0.2, 0.2, 0.2], True)]
        ) as run_episode:
            scores = run_all_tasks("saas")

        self.assertEqual(scores, {"saas_easy": 0.6})
        self.assertEqual(run_episode.call_count, 2)

    def test_prints_structured_output_blocks(self) -> None:
        fake_tasks = [{"id": "saas_easy", "difficulty": "easy"}]
        fake_domain = SimpleNamespace(get_tasks=lambda: fake_tasks)

        class FakeEnv:
            def sync(self) -> "FakeEnv":
                return self

            def close(self) -> None:
                return None

        stdout = StringIO()
        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}), patch(
            "inference.OPENAI_API_KEY", "test-key"
        ), patch("inference.OpenAI", return_value=object()), patch(
            "inference.DomainRegistry.require", return_value=lambda: fake_domain
        ), patch("inference.MultiDomainEnv", return_value=FakeEnv()), patch(
            "inference.run_episode", return_value=(0.75, 2, [0.25, 0.5], True)
        ), patch("sys.stdout", stdout):
            scores = run_all_tasks("saas")

        output = stdout.getvalue()
        self.assertEqual(scores, {"saas_easy": 0.75})
        self.assertIn("[START] task=saas_easy env=saas model=", output)
        self.assertIn("[END] success=true steps=2 score=0.75 rewards=0.25,0.50", output)


if __name__ == "__main__":
    unittest.main()
