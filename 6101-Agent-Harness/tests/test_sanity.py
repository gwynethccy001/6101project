# tests/test_sanity.py
import sys
sys.path.insert(0, r"E:\6101\6101-agent-harness")

from src.types import Decision, GateOutput, Policy, GateInput


class FullApprovePolicy(Policy):
    def decide(self, gate_input: GateInput) -> GateOutput:
        return GateOutput(decision=Decision.AUTO_APPROVE)


class FullDenyPolicy(Policy):
    def decide(self, gate_input: GateInput) -> GateOutput:
        return GateOutput(decision=Decision.AUTO_DENY)


class FullEscalatePolicy(Policy):
    def decide(self, gate_input: GateInput) -> GateOutput:
        return GateOutput(decision=Decision.ESCALATE)


def _make_input(k_remaining=5):
    return GateInput(
        tool_name="send_money",
        args={"amount": 100},
        tool_metadata={"risk": "high"},
        trajectory=[],
        user_task_text="send money",
        k_remaining=k_remaining,
    )


def test_full_approve():
    policy = FullApprovePolicy()
    output = policy.decide(_make_input())
    assert output.decision == Decision.AUTO_APPROVE


def test_full_deny():
    policy = FullDenyPolicy()
    output = policy.decide(_make_input())
    assert output.decision == Decision.AUTO_DENY


def test_full_escalate():
    policy = FullEscalatePolicy()
    output = policy.decide(_make_input())
    assert output.decision == Decision.ESCALATE