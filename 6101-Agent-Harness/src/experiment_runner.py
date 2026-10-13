
"""R5 experiment planner for AgentDojo.

This first version only creates an experiment manifest.
It does NOT call a model or execute benchmark tasks.
"""

import csv
from pathlib import Path
from typing import Any

from agentdojo.task_suite.load_suites import get_suite


def build_experiment_plan(
    benchmark_version: str = "v1.2.2",
    suite_name: str = "banking",
    policies: list[str] | None = None,
    k_values: list[int] | None = None,
) -> list[dict[str, Any]]:
    """Create one planned row per user task, injection task, policy, and k."""

    if policies is None:
        policies = ["full_approve", "full_escalate", "risk_based"]

    if k_values is None:
        k_values = [0, 1, 3, 5]

    if not policies:
        raise ValueError("policies must not be empty")

    if not k_values or any(k < 0 for k in k_values):
        raise ValueError("k_values must contain non-negative integers")

    suite = get_suite(benchmark_version, suite_name)
    plan = []

    for user_task_id in suite.user_tasks:
        for injection_task_id in suite.injection_tasks:
            for policy_name in policies:
                for k in k_values:
                    plan.append(
                        {
                            "benchmark_version": benchmark_version,
                            "suite": suite_name,
                            "user_task_id": user_task_id,
                            "injection_task_id": injection_task_id,
                            "policy": policy_name,
                            "k": k,
                            "status": "pending",
                            "error": "",
                        }
                    )

    return plan


def save_plan_csv(
    plan: list[dict[str, Any]],
    output_path: str | Path = "runs/r5_experiment_plan.csv",
) -> Path:
    """Save the plan as a CSV manifest."""

    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    if not plan:
        raise ValueError("Cannot save an empty experiment plan")

    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(file, fieldnames=list(plan[0].keys()))
        writer.writeheader()
        writer.writerows(plan)

    return path


if __name__ == "__main__":
    experiment_plan = build_experiment_plan()
    output_file = save_plan_csv(experiment_plan)

    print(f"Planned experiment rows: {len(experiment_plan)}")
    print(f"Saved manifest to: {output_file.resolve()}")
    print("\nFirst 3 rows:")
    for row in experiment_plan[:3]:
        print(row)
