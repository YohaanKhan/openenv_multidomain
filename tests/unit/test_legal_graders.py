from domains.legal.graders.code_grader import LegalCodeGrader


def _extract_step():
    return {
        "step_idx": 1,
        "tool_name": "extract_clause",
        "tool_args": {"contract_id": "NDA-001", "clause_type": "termination"},
        "result": "NDA-001-TERM | termination | is_standard=True",
        "reward": 0.05,
        "thought": "",
    }


def _add_note_step():
    return {
        "step_idx": 2,
        "tool_name": "add_memo_note",
        "tool_args": {"contract_id": "NDA-001", "section": "termination"},
        "result": "Note added to memo under 'termination'.",
        "reward": 0.05,
        "thought": "",
    }


def _finalize_step():
    return {
        "step_idx": 3,
        "tool_name": "finalize_memo",
        "tool_args": {"contract_id": "NDA-001", "summary": "Reviewed."},
        "result": "Memo finalized for contract NDA-001.",
        "reward": 0.4,
        "thought": "",
    }


def _perfect_traj():
    return [_extract_step(), _add_note_step(), _finalize_step()]


def _partial_traj():
    return [_extract_step()]


def test_grade_perfect_trajectory():
    grader = LegalCodeGrader()
    result = grader.grade(_perfect_traj(), session=None)
    assert result["score"] >= 0.95
    assert result["success"] is True


def test_grade_empty_trajectory():
    grader = LegalCodeGrader()
    result = grader.grade([], session=None)
    assert result["score"] == 0.0
    assert result["success"] is False


def test_grade_partial_trajectory():
    grader = LegalCodeGrader()
    result = grader.grade(_partial_traj(), session=None)
    assert 0.0 < result["score"] < 1.0
    assert result["success"] is False


def test_grader_deterministic():
    grader = LegalCodeGrader()
    traj = _partial_traj()
    score1 = grader.grade(traj, session=None)["score"]
    score2 = grader.grade(traj, session=None)["score"]
    assert score1 == score2


def test_grade_score_in_range():
    grader = LegalCodeGrader()
    for traj in [[], _partial_traj(), _perfect_traj()]:
        result = grader.grade(traj, session=None)
        assert 0.0 <= result["score"] <= 1.0
        assert isinstance(result["success"], bool)
        assert isinstance(result["feedback"], str)


def test_grade_without_session():
    grader = LegalCodeGrader()
    result = grader.grade(_perfect_traj(), session=None)
    assert "score" in result
