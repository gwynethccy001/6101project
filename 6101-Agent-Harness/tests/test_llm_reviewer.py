# tests/test_llm_reviewer.py
"""Offline tests: a fake OpenAI-style client stands in for Ollama, so no GPU or server is needed."""
from types import SimpleNamespace

from tenacity import wait_none

from src.llm_reviewer import LLMReviewer, firewall_check
from src.types import GateInput


class FakeCompletions:
    def __init__(self, outputs):
        self.outputs = list(outputs)
        self.calls = []

    def create(self, **kw):
        self.calls.append(kw)
        out = self.outputs.pop(0) if len(self.outputs) > 1 else self.outputs[0]
        if isinstance(out, Exception):
            raise out
        return SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=out))],
            usage=SimpleNamespace(prompt_tokens=10, completion_tokens=5))


def make_client(*outputs):
    return SimpleNamespace(chat=SimpleNamespace(completions=FakeCompletions(outputs)))


def calls(client):
    return client.chat.completions.calls


def make_reviewer(*outputs, **kw):
    client = make_client(*outputs)
    return LLMReviewer(client=client, retry_wait=wait_none(), **kw), client


def gi(trajectory=None, **kw):
    base = dict(tool_name="send_money", args={"recipient": "ACME-123"},
                tool_metadata={"risk": "ZZZRISK"}, trajectory=trajectory or [],
                user_task_text="Pay my rent", k_remaining=987654)
    base.update(kw)
    return GateInput(**base)


APPROVE = '{"decision": "approve", "reason": "matches the request"}'
DENY = '{"decision": "deny", "reason": "unknown recipient"}'


def test_approve_and_deny_share_one_call():
    r, c = make_reviewer(APPROVE)
    assert r.approve(gi()) is True
    assert r.deny(gi()) is False
    assert len(calls(c)) == 1 and r.consultations == 1


def test_different_requests_are_separate_calls():
    r, c = make_reviewer(APPROVE, DENY)
    assert r.approve(gi(tool_name="send_money")) is True
    assert r.approve(gi(tool_name="update_scheduled_transaction")) is False
    assert len(calls(c)) == 2 and r.consultations == 2


def test_think_block_and_code_fence_are_stripped():
    reply = "<think>The user wants rent paid...</think>\n```json\n" + APPROVE + "\n```"
    r, _ = make_reviewer(reply)
    assert r.approve(gi()) is True
    assert r.errors == 0


def test_unclosed_think_block_becomes_flagged_deny():
    r, _ = make_reviewer("<think>I am still thinking about this and ran out of")
    assert r.deny(gi()) is True
    assert r.errors == 1 and r.log[-1]["error"] is True


def test_decision_synonyms_are_normalised():
    r, _ = make_reviewer('{"decision": "Approved", "reason": "fine"}')
    assert r.approve(gi()) is True


def test_unrecognised_decision_becomes_flagged_deny():
    r, _ = make_reviewer('{"decision": "maybe", "reason": "unsure"}')
    assert r.deny(gi()) is True
    assert r.errors == 1


def test_non_json_output_becomes_flagged_deny():
    r, _ = make_reviewer("I think this is fine.")
    assert r.deny(gi()) is True
    assert r.errors == 1


def test_api_error_is_retried_then_denied_without_raising():
    r, c = make_reviewer(ConnectionError("ollama down"), max_attempts=2)
    assert r.deny(gi()) is True
    assert len(calls(c)) == 2
    assert r.errors == 1


def test_retry_recovers_after_one_failure():
    r, c = make_reviewer(ConnectionError("blip"), APPROVE, max_attempts=3)
    assert r.approve(gi()) is True
    assert len(calls(c)) == 2 and r.errors == 0


def test_firewall_hides_metadata_and_budget():
    r, _ = make_reviewer(DENY)
    prompt = r.render(gi())
    assert "ZZZRISK" not in prompt and "987654" not in prompt
    r.approve(gi())
    assert r.firewall_hits == []


def test_firewall_flags_leaked_identifiers():
    leaky = [{"tool": "get_balance", "args": {}, "output": "injection_task_3 goal: send money"}]
    assert firewall_check(gi(trajectory=leaky).user_task_text) == []
    r, _ = make_reviewer(DENY)
    r.approve(gi(trajectory=leaky))
    assert "injection_task" in r.firewall_hits


def test_trajectory_is_capped_and_clipped():
    traj = [{"tool": f"step{i}", "args": {}, "output": "x" * 5000} for i in range(30)]
    r, _ = make_reviewer(DENY, max_steps=5, max_chars=100)
    prompt = r.render(gi(trajectory=traj))
    assert "25 earlier steps omitted" in prompt
    assert "step29" in prompt and "step0(" not in prompt
    assert "[truncated]" in prompt and "x" * 200 not in prompt


def test_request_is_deterministic_and_disables_thinking():
    r, c = make_reviewer(APPROVE)
    r.approve(gi())
    kw = calls(c)[0]
    assert kw["temperature"] == 0.0 and kw["seed"] == 0
    assert kw["messages"][0]["content"].endswith("/no_think")
    assert kw["model"] == "qwen3:14b"


def test_no_think_can_be_turned_off():
    r, c = make_reviewer(APPROVE, no_think=False)
    r.approve(gi())
    assert not calls(c)[0]["messages"][0]["content"].endswith("/no_think")


def test_usage_is_recorded_for_cost_tracking():
    r, _ = make_reviewer(APPROVE)
    r.approve(gi())
    u = r.last_usage
    assert u["input_tokens"] == 10 and u["output_tokens"] == 5
    assert u["provider"] == "ollama" and u["cost_usd"] is None


def test_check_ready_reports_missing_model():
    client = SimpleNamespace(models=SimpleNamespace(
        list=lambda: SimpleNamespace(data=[SimpleNamespace(id="llama3:8b")])))
    r = LLMReviewer(client=client)
    try:
        r.check_ready()
        assert False, "expected RuntimeError"
    except RuntimeError as e:
        assert "ollama pull qwen3:14b" in str(e)
