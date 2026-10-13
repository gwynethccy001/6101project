# tests/test_gate_result.py
import sys
sys.path.insert(0, r"E:\6101\6101-agent-harness")

from src.gate import GateElement
from src.types import Decision, GateInput, GateOutput, Policy, Reviewer


class ApproveAllPolicy(Policy):
    def decide(self, gate_input: GateInput) -> GateOutput:
        return GateOutput(decision=Decision.AUTO_APPROVE, rationale="test")


class ApproveReviewer(Reviewer):
    def approve(self, gate_input: GateInput) -> bool:
        return True
    def deny(self, gate_input: GateInput) -> bool:
        return False


def test_gate_records_results():
    policy = ApproveAllPolicy()
    reviewer = ApproveReviewer()
    gate = GateElement(policy=policy, reviewer=reviewer, k=5, tool_risk_metadata={})

    messages = [
        {
            "role": "assistant",
            "content": "",
            "tool_calls": [
                {"id": "call_1", "function": "get_balance", "args": {}},
                {"id": "call_2", "function": "send_money", "args": {}},
            ],
        }
    ]
    extra_args = {"k_remaining": 5, "user_task": "test task"}

    gate.query("test", None, None, messages, extra_args)

    assert len(gate.gate_results) == 2
    assert gate.gate_results[0].tool_name == "get_balance"
    assert gate.gate_results[0].approved is True
    assert gate.gate_results[1].tool_name == "send_money"
    assert gate.gate_results[1].approved is True