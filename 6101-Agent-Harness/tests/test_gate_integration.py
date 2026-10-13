# tests/test_gate_integration.py
import sys
sys.path.insert(0, r"E:\6101\6101-agent-harness")

from src.gate import GateElement
from src.types import Decision, GateInput, GateOutput, Policy, Reviewer


class MockPolicy(Policy):
    def __init__(self, decision_map):
        self.decision_map = decision_map

    def decide(self, gate_input: GateInput) -> GateOutput:
        decision = self.decision_map.get(gate_input.tool_name, Decision.AUTO_DENY)
        return GateOutput(decision=decision, rationale="mock")


class MockReviewer(Reviewer):
    def __init__(self, approve_all=True):
        self.approve_all = approve_all

    def approve(self, gate_input: GateInput) -> bool:
        return self.approve_all

    def deny(self, gate_input: GateInput) -> bool:
        return not self.approve_all


def test_gate_with_mock_policy_approve():
    policy = MockPolicy({"get_balance": Decision.AUTO_APPROVE})
    reviewer = MockReviewer()
    gate = GateElement(policy=policy, reviewer=reviewer, k=5, tool_risk_metadata={})

    messages = [{
        "role": "assistant",
        "content": "",
        "tool_calls": [{"id": "1", "function": "get_balance", "args": {}}],
    }]
    extra_args = {"k_remaining": 5, "user_task": "test"}

    query, runtime, env, out_messages, out_extra = gate.query("test", None, None, messages, extra_args)

    assert len(out_messages[-1]["tool_calls"]) == 1
    assert out_messages[-1]["tool_calls"][0]["function"] == "get_balance"


def test_gate_with_mock_policy_deny():
    policy = MockPolicy({"send_money": Decision.AUTO_DENY})
    reviewer = MockReviewer()
    gate = GateElement(policy=policy, reviewer=reviewer, k=5, tool_risk_metadata={})

    messages = [{
        "role": "assistant",
        "content": "",
        "tool_calls": [{"id": "1", "function": "send_money", "args": {}}],
    }]
    extra_args = {"k_remaining": 5, "user_task": "test"}

    query, runtime, env, out_messages, out_extra = gate.query("test", None, None, messages, extra_args)

    # AUTO_DENY: tool_calls replaced by a tool message with error field
    assert "tool_calls" not in out_messages[-1]
    assert out_messages[-1]["role"] == "tool"
    assert "Blocked by gate" in out_messages[-1]["error"]