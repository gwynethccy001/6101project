# src/types.py
from enum import Enum
from pydantic import BaseModel
from typing import Any, Optional, List, Dict


class Decision(str, Enum):
    AUTO_APPROVE = "AUTO_APPROVE"
    AUTO_DENY = "AUTO_DENY"
    ESCALATE = "ESCALATE"


class GateInput(BaseModel):
    tool_name: str
    args: Dict[str, Any]
    tool_metadata: Dict[str, Any]
    trajectory: List[Dict[str, Any]]
    user_task_text: str
    k_remaining: int


class GateOutput(BaseModel):
    decision: Decision
    risk_score: Optional[float] = None
    rationale: Optional[str] = None


class GateResult(BaseModel):
    """Result of processing a single tool call through the gate."""
    tool_name: str
    decision: Decision
    approved: bool
    k_remaining: int
    rationale: Optional[str] = None


class Policy:
    """Policy interface: decides whether a tool call is approved, denied, or escalated."""
    def decide(self, gate_input: GateInput) -> GateOutput:
        raise NotImplementedError


class Reviewer:
    """Reviewer interface: approves or denies escalated tool calls."""
    def approve(self, gate_input: GateInput) -> bool:
        raise NotImplementedError
    
    def deny(self, gate_input: GateInput) -> bool:
        raise NotImplementedError