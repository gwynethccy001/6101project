
from src.metrics import calculate_metrics


def main():
    episodes = [
        {
            "task_id": "task_001",
            "task_completed": True,
            "unauthorized_tool_call": False,
        },
        {
            "task_id": "task_002",
            "task_completed": True,
            "unauthorized_tool_call": True,
        },
        {
            "task_id": "task_003",
            "task_completed": False,
            "unauthorized_tool_call": False,
        },
        {
            "task_id": "task_004",
            "task_completed": True,
            "unauthorized_tool_call": None,
        },
    ]

    gates = [
        {
            "task_id": "task_001",
            "decision": "ESCALATE",
            "reviewer_consulted": True,
        },
        {
            "task_id": "task_001",
            "decision": "AUTO_APPROVE",
            "reviewer_consulted": False,
        },
        {
            "task_id": "task_002",
            "decision": "ESCALATE",
            "reviewer_consulted": True,
        },
    ]

    costs = [
        {"component": "agent", "cost_usd": 0.10},
        {"component": "reviewer", "cost_usd": 0.02},
        {"component": "policy", "cost_usd": None},
    ]

    result = calculate_metrics(episodes, gates, costs)

    assert result["total_episodes"] == 4
    assert result["episodes_with_known_safety_label"] == 3
    assert result["episodes_with_unknown_safety_label"] == 1
    assert result["safe_completed_episodes"] == 1
    assert abs(result["TCR_at_k"] - 1 / 3) < 1e-9

    assert result["human_interventions_on_successful_tasks"] == 2
    assert result["HITL_load_per_successful_task"] == 1.0

    assert abs(result["known_cost_total_usd"] - 0.12) < 1e-9
    assert result["unknown_cost_calls"] == 1
    assert result["cost_by_component"]["policy"]["unknown_cost_calls"] == 1

    print("PASS: TCR@k calculation")
    print("PASS: Unknown safety labels are tracked")
    print("PASS: HITL load counts reviewer consultations")
    print("PASS: Known and unknown costs are separated")


if __name__ == "__main__":
    main()
