from benchmarks.run_saas_ollama import (
    EpisodeStats,
    _aggregate_summaries,
    _coerce_action_dict,
    _comparison_delta,
    _summarize_runs,
)


def test_coerce_action_dict_parses_json_object():
    payload = _coerce_action_dict(
        '{"tool_name":"search_tickets","tool_args":{"query":"billing"},"thought":"check open tickets"}'
    )
    assert payload["tool_name"] == "search_tickets"
    assert payload["tool_args"]["query"] == "billing"
    assert payload["thought"] == "check open tickets"


def test_coerce_action_dict_extracts_wrapped_json():
    payload = _coerce_action_dict(
        'Here is the action:\n{"tool_name":"close_ticket","tool_args":{"ticket_id":"T-1"},"thought":""}'
    )
    assert payload["tool_name"] == "close_ticket"
    assert payload["tool_args"]["ticket_id"] == "T-1"


def test_summarize_runs_computes_aggregate_metrics():
    summary = _summarize_runs(
        "codellama",
        [
            EpisodeStats("saas_easy", 1.0, turns=2, invalid_actions=0, total_actions=2),
            EpisodeStats("saas_medium", 0.5, turns=4, invalid_actions=1, total_actions=4),
        ],
    )

    assert summary["model"] == "codellama"
    assert summary["task_scores"] == {"saas_easy": 1.0, "saas_medium": 0.5}
    assert summary["average_score"] == 0.75
    assert summary["success_rate"] == 0.5
    assert summary["average_turns"] == 3.0
    assert summary["invalid_action_rate"] == 0.1667


def test_aggregate_summaries_computes_means():
    aggregate = _aggregate_summaries(
        "codellama",
        [
            {
                "task_scores": {"saas_easy": 1.0, "saas_medium": 0.5},
                "average_score": 0.75,
                "success_rate": 0.5,
                "average_turns": 3.0,
                "invalid_action_rate": 0.1,
            },
            {
                "task_scores": {"saas_easy": 0.5, "saas_medium": 0.25},
                "average_score": 0.375,
                "success_rate": 0.0,
                "average_turns": 5.0,
                "invalid_action_rate": 0.3,
            },
        ],
    )

    assert aggregate["runs"] == 2
    assert aggregate["mean_average_score"] == 0.5625
    assert aggregate["mean_success_rate"] == 0.25
    assert aggregate["mean_average_turns"] == 4.0
    assert aggregate["mean_invalid_action_rate"] == 0.2
    assert aggregate["task_score_means"] == {"saas_easy": 0.75, "saas_medium": 0.375}


def test_comparison_delta_reports_metric_differences():
    delta = _comparison_delta(
        {
            "mean_average_score": 0.4,
            "mean_success_rate": 0.2,
            "mean_average_turns": 8.0,
            "mean_invalid_action_rate": 0.3,
        },
        {
            "mean_average_score": 0.7,
            "mean_success_rate": 0.6,
            "mean_average_turns": 6.0,
            "mean_invalid_action_rate": 0.1,
        },
    )

    assert delta == {
        "mean_average_score": 0.3,
        "mean_success_rate": 0.4,
        "mean_average_turns": -2.0,
        "mean_invalid_action_rate": -0.2,
    }
