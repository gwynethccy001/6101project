# src/llm_reviewer.py
"""LLM-simulated human reviewer backed by a local Qwen3 model served by Ollama.

The gate calls approve() and/or deny() for an escalated tool call. Both methods
share one model call per request, so the consultation (and its cost) is counted once.

Firewall: the reviewer is shown only the user's task, the visible trajectory and
the proposed tool call. It never sees tool_metadata (risk labels), k_remaining,
or anything about the benchmark's injection tasks / attack setup.
"""
import json
import re
import string
import time
from pathlib import Path
from typing import Literal

from openai import OpenAI
from pydantic import BaseModel
from tenacity import Retrying, stop_after_attempt, wait_exponential

from .types import GateInput, Reviewer

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "reviewer.txt"
DEFAULT_MODEL = "qwen3:14b"
DEFAULT_BASE_URL = "http://localhost:11434/v1"

# Identifiers that would only appear in the prompt if our own code leaked ground truth.
FORBIDDEN = ["injection_task", "attack_type", "ground_truth",
             "security_result", "utility_result"]

_APPROVE = {"approve", "approved", "allow", "allowed", "yes"}
_DENY = {"deny", "denied", "reject", "rejected", "block", "blocked", "no"}

_THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
_JSON_RE = re.compile(r"\{.*\}", re.DOTALL)


class Verdict(BaseModel):
    decision: Literal["approve", "deny"]
    reason: str
    error: bool = False


def firewall_check(prompt: str) -> list:
    """Return the forbidden identifiers found in a rendered prompt (empty list = clean)."""
    low = prompt.lower()
    return [w for w in FORBIDDEN if w in low]


def clean_model_text(text: str) -> str:
    """Remove Qwen3 <think> blocks, including an unclosed one from a cut-off reply."""
    text = _THINK_RE.sub("", text or "")
    if "<think>" in text:
        text = text.split("<think>")[0]
    return text.strip()


def parse_verdict(text: str) -> Verdict:
    """Parse a model reply into a Verdict. Raises ValueError if it can't be understood."""
    m = _JSON_RE.search(clean_model_text(text))
    if not m:
        raise ValueError("no JSON object in reply")
    data = json.loads(m.group(0))
    raw = str(data.get("decision", "")).strip().lower()
    if raw in _APPROVE:
        decision = "approve"
    elif raw in _DENY:
        decision = "deny"
    else:
        raise ValueError(f"unrecognised decision: {raw!r}")
    return Verdict(decision=decision, reason=str(data.get("reason", "")).strip())


class LLMReviewer(Reviewer):
    def __init__(self, model=DEFAULT_MODEL, base_url=DEFAULT_BASE_URL, client=None,
                 max_chars=1500, max_steps=10, max_tokens=512, no_think=True,
                 max_attempts=3, retry_wait=None):
        self.model = model
        self.base_url = base_url
        self.client = client or OpenAI(base_url=base_url, api_key="ollama", timeout=120.0)
        self.template = string.Template(PROMPT_PATH.read_text())
        self.max_chars = max_chars          # per trajectory step (keeps prompts small)
        self.max_steps = max_steps          # only the most recent steps are shown
        self.max_tokens = max_tokens
        self.no_think = no_think            # append Qwen3's /no_think switch
        self.max_attempts = max_attempts
        self.retry_wait = retry_wait or wait_exponential(multiplier=1, min=1, max=8)

        self.consultations = 0              # actual model reviews (cached repeats not counted)
        self.errors = 0
        self.firewall_hits = []
        self.last_usage = None
        self.log = []                       # one record per review, for failure analysis
        self._last = None                   # (prompt, Verdict): approve()/deny() share a call

    # ---- setup check -------------------------------------------------------------
    def check_ready(self):
        """Call once before a run: confirms Ollama is reachable and the model is pulled."""
        try:
            names = [m.id for m in self.client.models.list().data]
        except Exception as e:
            raise RuntimeError(
                f"Cannot reach Ollama at {self.base_url}. Start it with `ollama serve`."
            ) from e
        if self.model not in names:
            raise RuntimeError(
                f"Model {self.model!r} not found in Ollama. Run `ollama pull {self.model}`. "
                f"Available: {names}")
        return True

    # ---- prompt building ---------------------------------------------------------
    def _clip(self, x):
        s = str(x)
        return s if len(s) <= self.max_chars else s[: self.max_chars] + " ...[truncated]"

    def _fmt_step(self, step: dict) -> str:
        # Adjust these keys once you've seen how gate.py builds trajectory entries.
        tool = step.get("tool") or step.get("tool_name")
        if tool is None:
            return "- " + self._clip(json.dumps(step, default=str))
        out = step.get("output", step.get("result", ""))
        args = json.dumps(step.get("args", {}), default=str)
        return f"- {tool}({args}) -> <tool_output>{self._clip(out)}</tool_output>"

    def render(self, gi: GateInput) -> str:
        # Deliberately NOT using gi.tool_metadata or gi.k_remaining.
        steps = gi.trajectory[-self.max_steps:]
        lines = [self._fmt_step(s) for s in steps]
        omitted = len(gi.trajectory) - len(steps)
        if omitted > 0:
            lines.insert(0, f"({omitted} earlier steps omitted)")
        return self.template.substitute(
            task=gi.user_task_text, tool=gi.tool_name,
            args=json.dumps(gi.args, default=str),
            trajectory="\n".join(lines) or "(none yet)")

    # ---- model call --------------------------------------------------------------
    def _raw_call(self, prompt: str):
        content = prompt + ("\n/no_think" if self.no_think else "")
        t0 = time.time()
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": content}],
            temperature=0.0, seed=0, max_tokens=self.max_tokens,
            response_format={"type": "json_object"})
        latency = time.time() - t0
        text = resp.choices[0].message.content or ""
        u = getattr(resp, "usage", None)
        usage = {"model": self.model, "provider": "ollama", "local": True,
                 "input_tokens": getattr(u, "prompt_tokens", None),
                 "output_tokens": getattr(u, "completion_tokens", None),
                 "cost_usd": None,           # local model: no API charge; see note for R5
                 "latency_s": round(latency, 3)}
        return text, usage

    def _call(self, prompt: str):
        for attempt in Retrying(stop=stop_after_attempt(self.max_attempts),
                                wait=self.retry_wait, reraise=True):
            with attempt:
                return self._raw_call(prompt)

    def _verdict(self, gi: GateInput) -> Verdict:
        prompt = self.render(gi)
        if self._last and self._last[0] == prompt:
            return self._last[1]
        self.firewall_hits += firewall_check(prompt)
        self.consultations += 1
        usage = None
        try:
            text, usage = self._call(prompt)
            v = parse_verdict(text)
            self.last_usage = usage
            # TODO(R5): send self.last_usage to CostTracker as component "reviewer"
        except Exception as e:
            self.errors += 1
            v = Verdict(decision="deny", reason=f"reviewer_error: {type(e).__name__}", error=True)
        self._last = (prompt, v)
        self.log.append({"tool": gi.tool_name, "decision": v.decision, "reason": v.reason,
                         "error": v.error, "usage": usage})
        return v

    # ---- Reviewer interface ------------------------------------------------------
    def approve(self, gate_input: GateInput) -> bool:
        return self._verdict(gate_input).decision == "approve"

    def deny(self, gate_input: GateInput) -> bool:
        return self._verdict(gate_input).decision == "deny"

    def stats(self) -> dict:
        return {"consultations": self.consultations, "errors": self.errors,
                "firewall_hits": list(self.firewall_hits)}
