# tests/test_risk_policy.py
import sys
sys.path.insert(0, r"E:\6101\6101-agent-harness")

from src.types import Decision, GateInput
from src.risk_based_policy import RiskBasedPolicy
from src.tool_risk import load_tool_risk_metadata

md = load_tool_risk_metadata("src/tool_risk_metadata.yaml")
policy = RiskBasedPolicy(md)


def make_input(tool_name):
    return GateInput(
        tool_name=tool_name,
        args={},
        tool_metadata=md.get(tool_name, {}),
        trajectory=[],
        user_task_text="",
        k_remaining=5,
    )


def test_low_risk_auto_approve():
    out = policy.decide(make_input("get_balance"))
    assert out.decision == Decision.AUTO_APPROVE


def test_high_risk_escalate():
    out = policy.decide(make_input("send_money"))
    assert out.decision == Decision.ESCALATE


def test_unknown_tool_defaults_to_escalate():
    out = policy.decide(make_input("unknown_tool"))
    assert out.decision == Decision.ESCALATE