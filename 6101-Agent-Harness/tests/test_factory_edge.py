# tests/test_factory_edge.py
import sys
sys.path.insert(0, r"E:\6101\6101-agent-harness")

from unittest.mock import MagicMock
from src.pipeline import build_pipeline


def test_build_pipeline_with_k_zero():
    md = {}
    policy = MagicMock()
    reviewer = MagicMock()
    client = MagicMock()

    pipeline = build_pipeline(
        model="qwen3:14b",
        policy=policy,
        k=0,
        reviewer=reviewer,
        tool_risk_metadata=md,
        client=client,
    )

    assert pipeline is not None
    assert len(pipeline.elements) == 6


def test_build_pipeline_with_empty_system_prompt():
    md = {}
    policy = MagicMock()
    reviewer = MagicMock()
    client = MagicMock()

    pipeline = build_pipeline(
        model="qwen3:14b",
        policy=policy,
        k=5,
        reviewer=reviewer,
        tool_risk_metadata=md,
        client=client,
    )

    assert pipeline is not None