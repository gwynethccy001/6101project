from src.baseline_policies import FullApprovePolicy, FullEscalatePolicy
from src.types import Decision, GateInput

def make_input(tool="send_money", k=3):
    return GateInput(tool_name=tool, args={}, tool_metadata={},
                     trajectory=[], user_task_text="test task", k_remaining=k)

def test_full_approve_always_approves():
    for tool in ["send_money", "get_balance", "anything_else"]:
        assert FullApprovePolicy().decide(make_input(tool)).decision == Decision.AUTO_APPROVE

def test_full_escalate_always_escalates():
    for tool in ["send_money", "get_balance"]:
        assert FullEscalatePolicy().decide(make_input(tool)).decision == Decision.ESCALATE
