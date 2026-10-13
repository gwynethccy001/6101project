# src/budget.py
from agentdojo.agent_pipeline import BasePipelineElement
from agentdojo.functions_runtime import FunctionsRuntime
from agentdojo.types import ChatMessage
from typing import Sequence


class BudgetResetElement(BasePipelineElement):
    """每个任务开始时重置预算"""
    
    def __init__(self, initial_k: int):
        self.initial_k = initial_k
    
    def query(
        self,
        query: str,
        runtime: FunctionsRuntime,
        env = None,
        messages: Sequence[ChatMessage] = [],
        extra_args: dict = {},
    ) -> tuple[str, FunctionsRuntime, None, Sequence[ChatMessage], dict]:
        extra_args["k_remaining"] = self.initial_k
        return query, runtime, env, messages, extra_args