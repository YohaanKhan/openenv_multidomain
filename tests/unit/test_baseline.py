from __future__ import annotations

import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from baseline import run_baseline_all


class RunBaselineAllTests(unittest.TestCase):
    def test_requires_openai_api_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaisesRegex(EnvironmentError, "OPENAI_API_KEY"):
                run_baseline_all("saas")

    def test_returns_task_scores(self) -> None:
        fake_tasks = [
            {"id": "saas_easy", "difficulty": "easy"},
            {"id": "saas_medium", "difficulty": "medium"},
        ]
        fake_domain = SimpleNamespace(get_tasks=lambda: fake_tasks)

        class FakeEnv:
            def sync(self) -> "FakeEnv":
                return self

            def __enter__(self) -> "FakeEnv":
                return self

            def __exit__(self, exc_type, exc, tb) -> None:
                return None

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            with patch("baseline.OpenAI") as mock_openai, patch(
                "baseline.DomainRegistry.require", return_value=lambda: fake_domain
            ), patch("baseline.MultiDomainEnv", return_value=FakeEnv()), patch(
                "baseline.run_episode", side_effect=[1.0, 0.75]
            ):
                mock_openai.return_value = object()

                scores = run_baseline_all("saas")

        self.assertEqual(scores, {"saas_easy": 1.0, "saas_medium": 0.75})


if __name__ == "__main__":
    unittest.main()
