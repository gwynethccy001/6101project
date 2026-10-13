# tests/test_pipeline.py
import sys
sys.path.insert(0, r"E:\6101\6101-agent-harness")

from unittest.mock import MagicMock
from src.pipeline import build_pipeline
from src.risk_based_policy import RiskBasedPolicy
from src.tool_risk import load_tool_risk_metadata


class MockReviewer:
    def approve(self, gate_input):
        return True
    def deny(self, gate_input):
        return False


def test_build_pipeline_returns_agent_pipeline():
    md = load_tool_risk_metadata("src/tool_risk_metadata.yaml")
    policy = RiskBasedPolicy(md)
    reviewer = MockReviewer()
    mock_client = MagicMock()
    pipeline = build_pipeline(
        model="qwen3:14b",
        policy=policy,
        k=5,
        reviewer=reviewer,
        tool_risk_metadata=md,
        system_prompt="You are a banking assistant.",
        client=mock_client,
    )
    assert pipeline is not None
    assert len(pipeline.elements) == 6


def test_build_pipeline_element_order():
    md = load_tool_risk_metadata("src/tool_risk_metadata.yaml")
    policy = RiskBasedPolicy(md)
    reviewer = MockReviewer()
    mock_client = MagicMock()
    pipeline = build_pipeline(
        model="qwen3:14b",
        policy=policy,
        k=5,
        reviewer=reviewer,
        tool_risk_metadata=md,
        client=mock_client,
    )
    names = [type(e).__name__ for e in pipeline.elements]
    assert names == [
        "SystemMessage",
        "InitQuery",
        "BudgetResetElement",
        "LocalLLM",
        "GateElement",
        "ToolsExecutor",
    ]