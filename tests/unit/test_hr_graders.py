from domains.hr.graders.code_grader import HRCodeGrader


def _lookup_step():
    return {
        "step_idx": 1,
        "tool_name": "lookup_policy",
        "tool_args": {"topic": "annual_leave"},
        "result": "Matching policies: P-1 | Annual Leave Policy",
        "reward": 0.05,
        "thought": "",
    }


def _get_employee_step():
    return {
        "step_idx": 2,
        "tool_name": "get_employee_record",
        "tool_args": {"employee_id": "E-303"},
        "result": "Employee E-303 | Leave remaining: 10",
        "reward": 0.05,
        "thought": "",
    }


def _benefits_step():
    return {
        "step_idx": 3,
        "tool_name": "get_benefits_summary",
        "tool_args": {"employee_id": "E-303"},
        "result": "Benefits summary: health | $500",
        "reward": 0.05,
        "thought": "",
    }


def _file_leave_step(ref="LR-2024-AB12"):
    return {
        "step_idx": 4,
        "tool_name": "file_leave_request",
        "tool_args": {"employee_id": "E-303", "leave_type": "annual"},
        "result": f"Leave request filed. Reference number: {ref}. Status: pending.",
        "reward": 0.25,
        "thought": "",
    }


def _close_step(ref="LR-2024-AB12", success=True):
    message = (
        f"Request {ref} closed." if success else f"No request found with reference '{ref}'."
    )
    return {
        "step_idx": 5,
        "tool_name": "close_hr_request",
        "tool_args": {"request_ref": ref, "resolution": "Approved"},
        "result": message,
        "reward": 0.4 if success else -0.05,
        "thought": "",
    }


def _perfect_traj():
    return [_lookup_step(), _get_employee_step(), _benefits_step(), _file_leave_step(), _close_step()]


def _partial_traj():
    return [_lookup_step()]


def test_grade_perfect_trajectory():
    grader = HRCodeGrader()
    result = grader.grade(_perfect_traj(), session=None)
    assert result["score"] >= 0.95
    assert result["success"] is True


def test_grade_empty_trajectory():
    grader = HRCodeGrader()
    result = grader.grade([], session=None)
    assert result["score"] == 0.0
    assert result["success"] is False


def test_grade_partial_trajectory():
    grader = HRCodeGrader()
    result = grader.grade(_partial_traj(), session=None)
    assert 0.0 < result["score"] < 1.0
    assert result["success"] is False


def test_grader_deterministic():
    grader = HRCodeGrader()
    traj = _partial_traj()
    score1 = grader.grade(traj, session=None)["score"]
    score2 = grader.grade(traj, session=None)["score"]
    assert score1 == score2


def test_grade_score_in_range():
    grader = HRCodeGrader()
    for traj in [[], _partial_traj(), _perfect_traj()]:
        result = grader.grade(traj, session=None)
        assert 0.0 <= result["score"] <= 1.0
        assert isinstance(result["success"], bool)
        assert isinstance(result["feedback"], str)


def test_grade_without_session():
    grader = HRCodeGrader()
    result = grader.grade(_perfect_traj(), session=None)
    assert "score" in result


def test_hr_hard_grader_requires_matching_ref_number():
    grader = HRCodeGrader()
    traj_correct_ref = [_file_leave_step(), _close_step(success=True)]
    traj_wrong_ref = [_file_leave_step(), _close_step(ref="LR-2024-FAKE", success=False)]

    score_correct = grader.grade(traj_correct_ref, session=None)["score"]
    score_wrong = grader.grade(traj_wrong_ref, session=None)["score"]
    assert score_correct > score_wrong
