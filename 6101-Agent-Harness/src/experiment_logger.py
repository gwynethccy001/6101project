
"""Append-only JSONL logging for R5 experiments."""
"""ExperimentLogger:统一管理实验日志。
log_gate_decision()：记录一次工具调用的决策。
log_episode_result()：记录一次任务运行的最终结果。
_append_jsonl()：每次追加一行 JSON,不覆盖已有记录。
timestamp,自动记录 UTC 时间。
**extra,允许后续增加其他字段，例如 injection_id、latency_seconds、error,而不必重写整个接口。"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class ExperimentLogger:
    """Write experiment events to JSONL files without overwriting old records."""

    def __init__(self, output_dir: str | Path, run_id: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.run_id = run_id
        self.gate_log_path = self.output_dir / "gate_decisions.jsonl"
        self.episode_log_path = self.output_dir / "episode_results.jsonl"

    def _append_jsonl(self, path: Path, record: dict[str, Any]) -> None:
        """Append exactly one JSON record as one line."""
        record = {
            **record,
            "run_id": self.run_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }

        with path.open("a", encoding="utf-8") as file:
            file.write(
                json.dumps(record, ensure_ascii=False, default=str) + "\n"
            )

    def log_gate_decision(
        self,
        *,
        policy: str,
        k: int,
        task_id: str,
        tool_name: str,
        decision: str,
        approved: bool,
        k_remaining: int,
        rationale: str | None = None,
        **extra: Any,
    ) -> None:
        """Record one tool-call decision."""
        record = {
            "event_type": "gate_decision",
            "policy": policy,
            "k": k,
            "task_id": task_id,
            "tool_name": tool_name,
            "decision": decision,
            "approved": approved,
            "k_remaining": k_remaining,
            "rationale": rationale,
            **extra,
        }
        self._append_jsonl(self.gate_log_path, record)

    def log_episode_result(
        self,
        *,
        policy: str,
        k: int,
        task_id: str,
        status: str,
        task_completed: bool,
        unauthorized_tool_call: bool | None,
        **extra: Any,
    ) -> None:
        """Record one task episode's final result."""
        record = {
            "event_type": "episode_result",
            "policy": policy,
            "k": k,
            "task_id": task_id,
            "status": status,
            "task_completed": task_completed,
            "unauthorized_tool_call": unauthorized_tool_call,
            **extra,
        }
        self._append_jsonl(self.episode_log_path, record)
