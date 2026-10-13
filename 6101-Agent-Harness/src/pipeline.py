# src/pipeline.py
from openai import OpenAI
from agentdojo.agent_pipeline import (
    AgentPipeline,
    SystemMessage,
    InitQuery,
    ToolsExecutor,
    LocalLLM,
)

from .budget import BudgetResetElement
from .gate import GateElement


def build_pipeline(model, policy, k, reviewer, tool_risk_metadata, system_prompt="", client=None):
    """
    组装完整 pipeline:
    SystemMessage → InitQuery → BudgetReset → LLM → Gate → ToolsExecutor

    Args:
        model: 模型名，如 "qwen3:14b"
        policy: Policy 实例
        k: 预算
        reviewer: Reviewer 实例
        tool_risk_metadata: 工具风险元数据 dict
        system_prompt: 系统提示词
        client: OpenAI 客户端（Ollama 用 OpenAI(base_url="http://localhost:11434/v1")）
    """
    if client is None:
        client = OpenAI(base_url="http://localhost:11434/v1", api_key="ollama")

    llm = LocalLLM(client=client, model=model)

    elements = [
        SystemMessage(system_message=system_prompt),
        InitQuery(),
        BudgetResetElement(initial_k=k),
        llm,
        GateElement(
            policy=policy,
            reviewer=reviewer,
            k=k,
            tool_risk_metadata=tool_risk_metadata,
        ),
        ToolsExecutor(),
    ]
    return AgentPipeline(elements=elements)