import yaml
from typing import Dict, Any


def load_tool_risk_metadata(path: str) -> Dict[str, Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    defaults = data.get("defaults", {})
    out = {}
    for tool_name, meta in data.get("tools", {}).items():
        merged = {**defaults, **(meta or {})}
        out[tool_name] = merged
    # unknown tools fall back to defaults
    out.setdefault("__default__", defaults)
    return out


def risk_for(tool_risk_metadata: Dict[str, Dict[str, Any]], tool_name: str) -> Dict[str, Any]:
    return tool_risk_metadata.get(tool_name) or tool_risk_metadata.get("__default__", {})