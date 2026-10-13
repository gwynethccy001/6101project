
"""Track model token usage and reported API costs for R5."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


VALID_COMPONENTS = {"agent", "policy", "reviewer"}


class CostTracker:
    """Append model-call usage records and calculate cost summaries."""

    def __init__(self, output_dir: str | Path, run_id: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.run_id = run_id
        self.log_path = self.output_dir / "cost_calls.jsonl"

    def record_call(
        self,
        *,
        component: str,
        model: str,
        provider: str,
        input_tokens: int | None = None,
        output_tokens: int | None = None,
        cost_usd: float | None = None,
        usage_source: str = "provider_reported",
        status: str = "success",
        request_id: str | None = None,
        **extra: Any,
    ) -> None:
        """Append one model-call record.

        Never estimate token usage or USD cost when the data is unavailable.
        """
        if component not in VALID_COMPONENTS:
            raise ValueError(
                f"component must be one of {sorted(VALID_COMPONENTS)}"
            )

        for name, value in (
            ("input_tokens", input_tokens),
            ("output_tokens", output_tokens),
        ):
            if value is not None:
                if isinstance(value, bool) or not isinstance(value, int):
                    raise TypeError(f"{name} must be an integer or None")
                if value < 0:
                    raise ValueError(f"{name} cannot be negative")

        if cost_usd is not None:
            if cost_usd < 0:
                raise ValueError("cost_usd cannot be negative")

        record = {
            "run_id": self.run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "component": component,
            "model": model,
            "provider": provider,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": (
                input_tokens + output_tokens
                if input_tokens is not None and output_tokens is not None
                else None
            ),
            "cost_usd": cost_usd,
            "usage_source": usage_source,
            "status": status,
            "request_id": request_id,
            **extra,
        }

        with self.log_path.open("a", encoding="utf-8") as file:
            file.write(
                json.dumps(record, ensure_ascii=False, default=str) + "\n"
            )

    def get_summary(self) -> dict[str, Any]:
        """Summarize recorded calls without treating unknown costs as zero."""
        totals = {
            component: {
                "calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "known_cost_usd": 0.0,
                "unknown_cost_calls": 0,
            }
            for component in sorted(VALID_COMPONENTS)
        }

        if not self.log_path.exists():
            return totals

        with self.log_path.open("r", encoding="utf-8") as file:
            for line in file:
                if not line.strip():
                    continue

                record = json.loads(line)
                component = record["component"]
                item = totals[component]
                item["calls"] += 1

                if record["input_tokens"] is not None:
                    item["input_tokens"] += record["input_tokens"]

                if record["output_tokens"] is not None:
                    item["output_tokens"] += record["output_tokens"]

                if record["cost_usd"] is None:
                    item["unknown_cost_calls"] += 1
                else:
                    item["known_cost_usd"] += record["cost_usd"]

        return totals
