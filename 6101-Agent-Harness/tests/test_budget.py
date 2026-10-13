import sys
sys.path.insert(0, r"E:\6101\6101-agent-harness")

from src.budget import BudgetResetElement


def test_reset_sets_k():
    el = BudgetResetElement(initial_k=7)
    _, _, _, _, extra = el.query(
        query="", runtime=None, messages=[], extra_args={"k_remaining": 1}
    )
    assert extra["k_remaining"] == 7


def test_reset_passthrough_messages():
    el = BudgetResetElement(initial_k=3)
    msgs = [{"role": "user", "content": "hi"}]
    _, _, _, out, _ = el.query(
        query="", runtime=None, messages=msgs, extra_args={}
    )
    assert out == msgs


def test_reset_passthrough_query():
    el = BudgetResetElement(initial_k=3)
    q, _, _, _, _ = el.query(
        query="send money", runtime=None, messages=[], extra_args={}
    )
    assert q == "send money"