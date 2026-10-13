
import json
import tempfile
from pathlib import Path

from src.experiment_logger import ExperimentLogger


def main():
    with tempfile.TemporaryDirectory() as temp_dir:
        logger = ExperimentLogger(temp_dir, run_id="r5_test_001")

        logger.log_gate_decision(
            policy="risk_based",
            k=3,
            task_id="task_001",
            tool_name="read_file",
            decision="ESCALATE",
            approved=True,
            k_remaining=2,
            rationale="Reviewer approved",
        )

        logger.log_episode_result(
            policy="risk_based",
            k=3,
            task_id="task_001",
            status="success",
            task_completed=True,
            unauthorized_tool_call=False,
            total_cost_usd=None,
        )

        gate_path = Path(temp_dir) / "gate_decisions.jsonl"
        episode_path = Path(temp_dir) / "episode_results.jsonl"

        gate_records = [
            json.loads(line)
            for line in gate_path.read_text(encoding="utf-8").splitlines()
        ]
        episode_records = [
            json.loads(line)
            for line in episode_path.read_text(encoding="utf-8").splitlines()
        ]

        assert len(gate_records) == 1
        assert gate_records[0]["decision"] == "ESCALATE"
        assert gate_records[0]["run_id"] == "r5_test_001"

        assert len(episode_records) == 1
        assert episode_records[0]["task_completed"] is True
        assert episode_records[0]["total_cost_usd"] is None

        print("PASS: Gate decision logging")
        print("PASS: Episode result logging")
        print("PASS: JSONL records are valid JSON")
        print("PASS: Unknown cost is stored as null")


if __name__ == "__main__":
    main()
