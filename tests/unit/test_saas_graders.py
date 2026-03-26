from domains.saas.graders.code_grader import SaaSCodeGrader


def _search_step():
    return {
        "step_idx": 1,
        "tool_name": "search_tickets",
        "tool_args": {"query": "billing", "customer_id": "C-1042"},
        "result": "Found tickets:\nT-5001: Incorrect annual renewal charge | status=open",
        "reward": 0.05,
        "thought": "",
    }


def _close_step():
    return {
        "step_idx": 2,
        "tool_name": "close_ticket",
        "tool_args": {"ticket_id": "T-5001", "resolution": "Resolved billing renewal discrepancy"},
        "result": "Ticket T-5001 closed for customer C-1042. Resolution: Resolved billing renewal discrepancy",
        "reward": 0.4,
        "thought": "",
    }


def _perfect_traj():
    return [_search_step(), _close_step()]


def _partial_traj():
    return [_search_step()]


def _medium_perfect_traj():
    return [
        {
            "step_idx": 1,
            "tool_name": "get_account",
            "tool_args": {"customer_id": "C-2077"},
            "result": "Customer Bob Chen (C-2077)",
            "reward": 0.05,
            "thought": "",
        },
        {
            "step_idx": 2,
            "tool_name": "get_transactions",
            "tool_args": {"customer_id": "C-2077"},
            "result": "Transactions:\nTX-9002: $49.00 USD | duplicate",
            "reward": 0.05,
            "thought": "",
        },
        {
            "step_idx": 3,
            "tool_name": "issue_refund",
            "tool_args": {
                "customer_id": "C-2077",
                "transaction_id": "TX-9002",
                "amount": 49.0,
                "reason": "Duplicate November subscription charge",
            },
            "result": "Refund issued for $49.00 on transaction TX-9002 for customer C-2077.",
            "reward": 0.2,
            "thought": "",
        },
        {
            "step_idx": 4,
            "tool_name": "send_email",
            "tool_args": {
                "customer_id": "C-2077",
                "subject": "Refund processed",
                "body": "We reversed the duplicate November charge.",
            },
            "result": "Email sent to customer C-2077",
            "reward": 0.1,
            "thought": "",
        },
        {
            "step_idx": 5,
            "tool_name": "close_ticket",
            "tool_args": {"ticket_id": "T-5002", "resolution": "Duplicate charge refunded"},
            "result": "Ticket T-5002 closed for customer C-2077. Resolution: Duplicate charge refunded",
            "reward": 0.4,
            "thought": "",
        },
    ]


def _medium_wrong_refund_traj():
    traj = _medium_perfect_traj()
    traj[2] = {
        **traj[2],
        "tool_args": {
            "customer_id": "C-2077",
            "transaction_id": "TX-9001",
            "amount": 49.0,
            "reason": "Refunded the wrong charge",
        },
        "result": "Refund issued for $49.00 on transaction TX-9001 for customer C-2077.",
    }
    return traj


def test_grade_perfect_trajectory():
    grader = SaaSCodeGrader()
    result = grader.grade(_perfect_traj(), session=None)
    assert result["score"] >= 0.99
    assert result["success"] is True


def test_grade_empty_trajectory():
    grader = SaaSCodeGrader()
    result = grader.grade([], session=None)
    assert result["score"] == 0.0
    assert result["success"] is False


def test_grade_partial_trajectory():
    grader = SaaSCodeGrader()
    result = grader.grade(_partial_traj(), session=None)
    assert 0.0 < result["score"] < 1.0
    assert result["success"] is False


def test_grader_deterministic():
    grader = SaaSCodeGrader()
    traj = _partial_traj()
    score1 = grader.grade(traj, session=None)["score"]
    score2 = grader.grade(traj, session=None)["score"]
    assert score1 == score2


def test_grade_score_in_range():
    grader = SaaSCodeGrader()
    for traj in [[], _partial_traj(), _perfect_traj()]:
        result = grader.grade(traj, session=None)
        assert 0.0 <= result["score"] <= 1.0
        assert isinstance(result["success"], bool)
        assert isinstance(result["feedback"], str)


def test_grade_without_session():
    grader = SaaSCodeGrader()
    result = grader.grade(_perfect_traj(), session=None)
    assert "score" in result


def test_grade_medium_correct_refund_scores_higher_than_wrong_refund():
    grader = SaaSCodeGrader()
    correct = grader.grade(_medium_perfect_traj(), session=None)["score"]
    wrong = grader.grade(_medium_wrong_refund_traj(), session=None)["score"]
    assert correct > wrong
