# tests/test_agentdojo_sanity.py
import sys
sys.path.insert(0, r"E:\6101\6101-agent-harness")

from agentdojo.agent_pipeline import AgentPipeline
from src.pipeline import build_pipeline
from src.risk_based_policy import RiskBasedPolicy
from src.tool_risk import load_tool_risk_metadata


def test_agentdojo_pipeline_constructs():
    md = load_tool_risk_metadata("src/tool_risk_metadata.yaml")
    policy = RiskBasedPolicy(md)

    class MockReviewer:
        def approve(self, gate_input):
            return True
        def deny(self, gate_input):
            return False

    pipeline = build_pipeline(
        model="qwen3:14b",
        policy=policy,
        k=5,
        reviewer=MockReviewer(),
        tool_risk_metadata=md,
    )

    assert isinstance(pipeline, AgentPipeline)