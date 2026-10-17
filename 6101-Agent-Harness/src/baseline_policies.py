# src/baseline_policies.py
from .types import Decision, GateInput, GateOutput, Policy


class FullApprovePolicy(Policy):
    """Baseline: approve every tool call, never consult the reviewer."""

    def decide(self, gate_input: GateInput) -> GateOutput:
        return GateOutput(
            decision=Decision.AUTO_APPROVE,
            rationale=f"Full-approve baseline: {gate_input.tool_name}",
        )


class FullEscalatePolicy(Policy):
    """Baseline: escalate every tool call to the reviewer.
    When the budget is exhausted, the gate (not this class) turns ESCALATE into a deny."""

    def decide(self, gate_input: GateInput) -> GateOutput:
        return GateOutput(
            decision=Decision.ESCALATE,
            rationale=f"Full-escalate baseline: {gate_input.tool_name}",
        )


POLICIES = {
    "full_approve": FullApprovePolicy,
    "full_escalate": FullEscalatePolicy,
}
