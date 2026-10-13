# src/gate.py
from typing import Sequence, Dict, Any, List
from agentdojo.agent_pipeline import BasePipelineElement
from agentdojo.types import ChatToolResultMessage
from agentdojo.agent_pipeline.tool_execution import text_content_block_from_string
from agentdojo.functions_runtime import FunctionsRuntime
from agentdojo.types import ChatMessage
from .types import Decision, GateInput, GateOutput, Policy, Reviewer, GateResult
from .tool_risk import risk_for


class GateElement(BasePipelineElement):
    """
    Tool approval gate: runs before ToolsExecutor, checks each tool_call.

    Decision flow:
    1. Policy decides AUTO_APPROVE / AUTO_DENY / ESCALATE
    2. On ESCALATE, if k_remaining > 0, consult Reviewer
    3. If k_remaining == 0, ESCALATE degrades to AUTO_DENY
    4. Each ESCALATE consumes 1 budget
    """

    def __init__(
        self,
        policy: Policy,
        reviewer: Reviewer,
        k: int,
        tool_risk_metadata: Dict[str, Dict[str, Any]],
    ):
        self.policy = policy
        self.reviewer = reviewer
        self.k_remaining = k
        self.tool_risk_metadata = tool_risk_metadata
        self.gate_results: List[GateResult] = []

    def query(
        self,
        query: str,
        runtime: FunctionsRuntime,
        env=None,
        messages: Sequence[ChatMessage] = [],
        extra_args: dict = {},
    ) -> tuple[str, FunctionsRuntime, None, Sequence[ChatMessage], dict]:
        # Read k_remaining from extra_args (set by BudgetResetElement)
        self.k_remaining = extra_args.get("k_remaining", self.k_remaining)

        # Pass through if no tool calls
        if len(messages) == 0:
            return query, runtime, env, messages, extra_args
        if messages[-1]["role"] != "assistant":
            return query, runtime, env, messages, extra_args
        if messages[-1]["tool_calls"] is None or len(messages[-1]["tool_calls"]) == 0:
            return query, runtime, env, messages, extra_args

        # Approve/block each tool call
        approved_calls = []
        blocked_messages = []

        for tool_call in messages[-1]["tool_calls"]:
            meta = risk_for(self.tool_risk_metadata, tool_call["function"])
            gate_input = GateInput(
                tool_name=tool_call["function"],
                args=tool_call["args"],
                tool_metadata=meta,
                trajectory=messages,
                user_task_text=extra_args.get("user_task", ""),
                k_remaining=self.k_remaining,
            )

            gate_output = self.policy.decide(gate_input)
            approved = False
            rationale = gate_output.rationale

            if gate_output.decision == Decision.AUTO_APPROVE:
                approved_calls.append(tool_call)
                approved = True

            elif gate_output.decision == Decision.ESCALATE:
                if self.k_remaining > 0:
                    self.k_remaining -= 1
                    if self.reviewer.approve(gate_input):
                        approved_calls.append(tool_call)
                        approved = True
                        rationale = "Reviewer approved"
                    else:
                        blocked_messages.append(
                            self._build_blocked_message(tool_call, "Reviewer denied")
                        )
                        rationale = "Reviewer denied"
                else:
                    blocked_messages.append(
                        self._build_blocked_message(tool_call, "Budget exhausted")
                    )
                    rationale = "Budget exhausted"

            else:  # AUTO_DENY
                blocked_messages.append(
                    self._build_blocked_message(tool_call, "Policy denied")
                )
                rationale = gate_output.rationale or "Policy denied"

            # Record gate result
            self.gate_results.append(
                GateResult(
                    tool_name=tool_call["function"],
                    decision=gate_output.decision,
                    approved=approved,
                    k_remaining=self.k_remaining,
                    rationale=rationale,
                )
            )

        # Modify last message's tool_calls to only approved ones
        if len(messages) > 0 and messages[-1]["role"] == "assistant":
            messages[-1]["tool_calls"] = approved_calls

        # Append blocked messages to messages
        messages = list(messages) + blocked_messages

        # Update k_remaining in extra_args for downstream elements
        extra_args["k_remaining"] = self.k_remaining

        return query, runtime, env, messages, extra_args

    def _build_blocked_message(self, tool_call, reason: str) -> ChatToolResultMessage:
        """Build a ChatToolResultMessage that blocks the tool call."""
        return ChatToolResultMessage(
            role="tool",
            tool_call_id=tool_call["id"],
            content=text_content_block_from_string(f"Blocked by gate: {reason}"),
            error=f"Blocked by gate: {reason}",
        )