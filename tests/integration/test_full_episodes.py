"""Integration coverage for full-episode behavior across all domains."""

from __future__ import annotations

import os

import pytest

os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import domains  # noqa: F401 register domains
from models import EnvAction
from server.domain_registry import DomainRegistry


@pytest.fixture(params=["saas", "hr", "legal"])
def env(request):
    """Run every test against each registered domain implementation."""
    os.environ["DOMAIN"] = request.param
    from server.environment import MultiDomainEnvironment

    e = MultiDomainEnvironment()
    yield e
    e._tx.rollback_episode()


def test_reset_returns_valid_observation(env):
    obs = env.reset()
    assert obs.done is False
    assert obs.reward == 0.0
    assert obs.content
    assert "task_id" in obs.info
    assert "trace_id" in obs.info
    assert obs.info["step_count"] == 0


def test_reset_gives_clean_state_each_time(env):
    env.reset()
    env.step(EnvAction(tool_name="nonexistent"))
    assert env._state.step_count == 1
    env.reset()
    assert env._state.step_count == 0
    assert env._trajectory == []


def test_invalid_tool_penalty(env):
    env.reset()
    obs = env.step(EnvAction(tool_name="this_tool_does_not_exist"))
    assert obs.reward == -0.05
    assert obs.done is False
    assert "not a valid tool" in obs.content


def test_bad_args_penalty(env):
    env.reset()
    tool_name = next(iter(env._tools))
    obs = env.step(EnvAction(tool_name=tool_name, tool_args={}))
    assert obs.reward in (-0.10, 0.0, 0.05)
    assert obs.done is False


def test_step_limit_terminates_episode(env):
    env.reset()
    env._task["max_steps"] = 3
    obs = None
    for _ in range(3):
        obs = env.step(EnvAction(tool_name="nonexistent"))
    assert obs.info.get("step_limit_hit") is True
    assert obs.done is True


def test_grader_score_present_on_terminal_step(env):
    env.reset()
    env._task["max_steps"] = 1
    obs = env.step(EnvAction(tool_name="nonexistent"))
    assert obs.done is True
    assert obs.info.get("grader_score") is not None
    assert 0.0 <= obs.info["grader_score"] <= 1.0


def test_grader_score_absent_mid_episode(env):
    env.reset()
    env._task["max_steps"] = 5
    obs = env.step(EnvAction(tool_name="nonexistent"))
    if not obs.done:
        assert obs.info.get("grader_score") is None


def test_state_property_returns_correct_type(env):
    env.reset()
    from openenv.core.env_server.types import State

    assert isinstance(env.state, State)
    assert env.state.step_count == 0
    env.step(EnvAction(tool_name="nonexistent"))
    assert env.state.step_count == 1


def test_trajectory_recorded_per_step(env):
    env.reset()
    assert len(env._trajectory) == 0
    env.step(EnvAction(tool_name="nonexistent", thought="testing"))
    assert len(env._trajectory) == 1
    step = env._trajectory[0]
    for key in ("step_idx", "tool_name", "tool_args", "thought", "result", "reward"):
        assert key in step


def test_saas_easy_full_episode():
    """Drive the SaaS easy task through a realistic search + close flow."""
    os.environ["DOMAIN"] = "saas"
    from server.environment import MultiDomainEnvironment

    env = MultiDomainEnvironment()
    env.reset()
    for task in env._domain.get_tasks():
        if task["difficulty"] == "easy":
            env._task = task
            env._tx.rollback_episode()
            env._tx.begin_episode()
            env._domain.seed_episode(task["id"], env._tx.get_session())
            break

    step1 = env.step(
        EnvAction(
            tool_name="search_tickets",
            tool_args={"query": "renewal", "customer_id": "C-1042", "status": "open"},
            thought="Finding the active renewal-charge ticket for the right customer",
        )
    )
    assert step1.done is False
    assert step1.reward >= 0.0
    assert "T-5001" in step1.content

    step2 = env.step(
        EnvAction(
            tool_name="close_ticket",
            tool_args={
                "ticket_id": "T-5001",
                "resolution": "Reviewed annual renewal and closed after confirming corrected billing.",
            },
            thought="Closing the verified billing ticket",
        )
    )
    assert step2.done is True
    assert step2.info["grader_score"] is not None
    assert step2.info["grader_score"] >= 0.7
