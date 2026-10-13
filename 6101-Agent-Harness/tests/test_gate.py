# tests/test_gate.py
import sys
sys.path.insert(0, r"E:\6101\6101-agent-harness")

from src.types import Decision, GateOutput, GateInput, Policy, Reviewer
from src.gate import GateElement


# --- Mock Policy ---

class ApproveAllPolicy(Policy):
    def decide(self, gate_input):
        return GateOutput(decision=Decision.AUTO_APPROVE)


class DenyAllPolicy(Policy):
    def decide(self, gate_input):
        return GateOutput(decision=Decision.AUTO_DENY)


class EscalateAllPolicy(Policy):
    def decide(self, gate_input):
        return GateOutput(decision=Decision.ESCALATE)


# --- Mock Reviewer ---

class ApproveReviewer(Reviewer):
    def approve(self, gate_input):
        return True
    def deny(self, gate_input):
        return False


class DenyReviewer(Reviewer):
    def approve(self, gate_input):
        return False
    def deny(self, gate_input):
        return True


# --- 构造 mock tool call ---

def make_tool_call(name="send_money", args=None, id="call_1"):
    return {
        "id": id,
        "function": name,
        "args": args or {"amount": 100},
    }

def make_messages_with_tool_call(tool_calls):
    return [
        {"role": "user", "content": "send money"},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": tool_calls,
        },
    ]


# --- 测试 ---

def test_auto_approve_passes_tool_call():
    gate = GateElement(
        policy=ApproveAllPolicy(),
        reviewer=DenyReviewer(),
        k=5,
        tool_risk_metadata={},
    )
    tool_call = make_tool_call()
    messages = make_messages_with_tool_call([tool_call])
    
    _, _, _, new_messages, extra_args = gate.query(
        query="",
        runtime=None,
        env=None,
        messages=messages,
        extra_args={"k_remaining": 5},
    )
    
    # 最后一条 assistant 消息的 tool_calls 应该保留
    assert len(new_messages[-1]["tool_calls"]) == 1
    assert new_messages[-1]["tool_calls"][0]["function"] == "send_money"


def test_auto_deny_blocks_tool_call():
    gate = GateElement(
        policy=DenyAllPolicy(),
        reviewer=DenyReviewer(),
        k=5,
        tool_risk_metadata={},
    )
    tool_call = make_tool_call()
    messages = make_messages_with_tool_call([tool_call])
    
    _, _, _, new_messages, extra_args = gate.query(
        query="",
        runtime=None,
        env=None,
        messages=messages,
        extra_args={"k_remaining": 5},
    )
    
    # tool_calls 应该被清空
    assert len(new_messages) == len(messages) + 1
    assert new_messages[-1]["role"] == "tool"
    assert "Blocked" in new_messages[-1]["error"]
    # assistant 消息的 tool_calls 被清空
    assert len(new_messages[-2]["tool_calls"]) == 0


def test_escalate_with_approval_passes():
    gate = GateElement(
        policy=EscalateAllPolicy(),
        reviewer=ApproveReviewer(),
        k=5,
        tool_risk_metadata={},
    )
    tool_call = make_tool_call()
    messages = make_messages_with_tool_call([tool_call])
    
    _, _, _, new_messages, extra_args = gate.query(
        query="",
        runtime=None,
        env=None,
        messages=messages,
        extra_args={"k_remaining": 5},
    )
    
    assert len(new_messages[-1]["tool_calls"]) == 1
    assert extra_args["k_remaining"] == 4  # 消耗了 1


def test_escalate_with_denial_blocks():
    gate = GateElement(
        policy=EscalateAllPolicy(),
        reviewer=DenyReviewer(),
        k=5,
        tool_risk_metadata={},
    )
    tool_call = make_tool_call()
    messages = make_messages_with_tool_call([tool_call])
    
    _, _, _, new_messages, extra_args = gate.query(
        query="",
        runtime=None,
        env=None,
        messages=messages,
        extra_args={"k_remaining": 5},
    )
    
    assert new_messages[-1]["role"] == "tool"
    assert "Blocked" in new_messages[-1]["error"]
    assert len(new_messages[-2]["tool_calls"]) == 0
    assert extra_args["k_remaining"] == 4


def test_escalate_with_k_zero_auto_deny():
    gate = GateElement(
        policy=EscalateAllPolicy(),
        reviewer=ApproveReviewer(),  # 即使 reviewer 同意，k=0 也拒绝
        k=0,
        tool_risk_metadata={},
    )
    tool_call = make_tool_call()
    messages = make_messages_with_tool_call([tool_call])
    
    _, _, _, new_messages, extra_args = gate.query(
        query="",
        runtime=None,
        env=None,
        messages=messages,
        extra_args={"k_remaining": 0},
    )
    
    assert new_messages[-1]["role"] == "tool"
    assert "Budget exhausted" in new_messages[-1]["error"]
    assert len(new_messages[-2]["tool_calls"]) == 0


def test_multiple_tool_calls_each_processed():
    gate = GateElement(
        policy=EscalateAllPolicy(),
        reviewer=ApproveReviewer(),
        k=5,
        tool_risk_metadata={},
    )
    tool_calls = [
        make_tool_call(name="send_money", id="call_1"),
        make_tool_call(name="get_balance", id="call_2"),
    ]
    messages = make_messages_with_tool_call(tool_calls)
    
    _, _, _, new_messages, extra_args = gate.query(
        query="",
        runtime=None,
        env=None,
        messages=messages,
        extra_args={"k_remaining": 5},
    )
    
    # 两个都通过
    assert len(new_messages[-1]["tool_calls"]) == 2
    assert extra_args["k_remaining"] == 3  # 消耗了 2