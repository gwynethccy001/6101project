
import json
import tempfile
from pathlib import Path

from src.cost_tracker import CostTracker


def main():
    with tempfile.TemporaryDirectory() as temp_dir:
        tracker = CostTracker(temp_dir, run_id="cost_test_001")

        tracker.record_call(
            component="agent",
            model="test-model",
            provider="test-provider",
            input_tokens=100,
            output_tokens=40,
            cost_usd=0.02,
        )

        tracker.record_call(
            component="reviewer",
            model="local-model",
            provider="local",
            input_tokens=50,
            output_tokens=20,
            cost_usd=None,
            usage_source="provider_reported",
        )

        log_path = Path(temp_dir) / "cost_calls.jsonl"
        records = [
            json.loads(line)
            for line in log_path.read_text(encoding="utf-8").splitlines()
        ]

        assert len(records) == 2
        assert records[0]["total_tokens"] == 140
        assert records[0]["cost_usd"] == 0.02
        assert records[1]["cost_usd"] is None

        summary = tracker.get_summary()

        assert summary["agent"]["calls"] == 1
        assert summary["agent"]["input_tokens"] == 100
        assert summary["agent"]["known_cost_usd"] == 0.02

        assert summary["reviewer"]["calls"] == 1
        assert summary["reviewer"]["unknown_cost_calls"] == 1

        print("PASS: Model calls are recorded")
        print("PASS: Token totals are calculated")
        print("PASS: Known costs are summed")
        print("PASS: Unknown costs remain distinguishable")


if __name__ == "__main__":
    main()
