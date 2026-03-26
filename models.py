# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""Domain-agnostic Action and Observation per the OpenEnv spec."""

from openenv.core.env_server.types import Action, Observation
from pydantic import Field


class EnvAction(Action):
    """Universal action type. Pick a tool name and pass its args."""

    tool_name: str = Field(..., description="Name of the tool to invoke")
    tool_args: dict = Field(default_factory=dict, description="Arguments validated against tool schema")
    thought: str = Field(default="", description="Agent reasoning, logged but not executed")


class EnvObservation(Observation):
    """Universal observation type. content is always human-readable text."""

    content: str = Field(..., description="Tool result, error message, or initial task description")
    done: bool = Field(..., description="True on terminal step")
    reward: float = Field(..., description="Step reward. Negative for errors, positive for correct actions.")
    info: dict = Field(default_factory=dict, description="Metadata. Contains step_count, task_id, trace_id. On terminal step: grader_score.")
