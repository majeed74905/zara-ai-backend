"""Chat Mode end-to-end through the FastAPI route (providers faked, no network)."""

from app.services.llm_router import ProviderRoutingError
from tests.conftest import FakeProvider


def _chat(client, message, model="zara-fast", history=None, **extra):
    body = {"message": message, "model": model, "module": "chat", "interaction_mode": "chat"}
    if history is not None:
        body["history"] = history
    body.update(extra)
    return client.post("/api/v1/ai/chat", json=body)


def test_chat_uses_detected_language_in_prompt(client, fake_llm):
    fake_llm.reply = "Hi macha 😄 Nalla irukken! Nee eppadi irukka?"
    r = _chat(client, "hi macha eppadi irukka")
    assert r.status_code == 200
    data = r.json()
    assert data["detected_language"] == "Tanglish"
    assert data["model_used"] == "zara-fast"
    call = fake_llm.calls[-1]
    assert "TANGLISH" in call["system_prompt"] and "MODE: ZARA FAST" in call["system_prompt"]


def test_history_is_sent_as_turns_and_drives_language(client, fake_llm):
    fake_llm.reply = "Seri bro, callback flow check pannalaam."
    history = [
        {"role": "user", "content": "payment success aaguthu but db la save aagala"},
        {"role": "model", "content": "Callback URL check pannunga."},
    ]
    r = _chat(client, "ok", history=history)
    assert r.status_code == 200
    assert r.json()["detected_language"] == "Tanglish"
    call = fake_llm.calls[-1]
    assert [h["role"] for h in call["history"]] == ["user", "assistant"]
    # History is not duplicated inside the user prompt
    assert "Callback URL check pannunga" not in call["user_prompt"]


def test_language_switch_mid_conversation(client, fake_llm):
    fake_llm.reply = "Seri bro 👍 saapten! Nee saptiya?"
    history = [{"role": "user", "content": "Hi bro how are you?"}, {"role": "assistant", "content": "Hey! Doing good."}]
    r = _chat(client, "seri bro saptiya?", history=history)
    assert r.json()["detected_language"] == "Tanglish"


def test_model_switch_keeps_context_but_changes_personality(client, fake_llm):
    fake_llm.reply = "Makes sense. Check the webhook first, then the DB write."
    history = [{"role": "user", "content": "I'm working on a payment API"}, {"role": "assistant", "content": "Nice!"}]
    q = "What should I check first in the webhook flow to find why the payment status isn't saved?"
    _chat(client, q, model="zara-fast", history=history)
    _chat(client, q, model="zara-pro", history=history)
    _chat(client, q, model="zara-eco", history=history)
    fast, pro, eco = fake_llm.calls[-3:]
    assert "MODE: ZARA FAST" in fast["system_prompt"]
    assert "MODE: ZARA PRO" in pro["system_prompt"]
    assert "MODE: ZARA ECO" in eco["system_prompt"]
    for call in (fast, pro, eco):
        assert call["history"][0]["content"] == "I'm working on a payment API"
    assert eco["max_tokens"] < fast["max_tokens"] < pro["max_tokens"]


def test_user_text_used_for_detection_when_context_appended(client, fake_llm):
    fake_llm.reply = "Seri, file-la 3 sections irukku."
    appended = "idhu enna file?\n\nAnalysis of Uploaded Files:\nFile: report.pdf\nContent Summary:\nThe quarterly report describes revenue growth and the hiring plan for the year."
    r = _chat(client, appended, user_text="idhu enna file?")
    assert r.json()["detected_language"] == "Tanglish"


def test_english_reply_to_tanglish_user_is_corrected_once(client, fake_llm, monkeypatch):
    fake_llm.reply = "I'm doing great, thanks for asking! What are you working on today, my friend?"
    from app.services import response_controller as rc
    calls = []

    def fake_rewrite(text, lang):
        calls.append(lang)
        return "Nalla irukken macha 😄 Nee enna panra, innaiku enna plan?"

    monkeypatch.setattr(rc, "force_language_rewrite", fake_rewrite)
    r = _chat(client, "hi macha eppadi irukka")
    assert calls == ["Tanglish"]
    assert "Nalla irukken" in r.json()["response"]


def test_consistent_reply_triggers_no_extra_llm_call(client, fake_llm, monkeypatch):
    fake_llm.reply = "Hey! I'm good 😊 What's up with you today?"
    from app.services import response_controller as rc
    monkeypatch.setattr(rc, "force_language_rewrite", lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not rewrite")))
    r = _chat(client, "Hi, how are you doing today?")
    assert r.status_code == 200 and len(fake_llm.calls) == 1


def test_code_block_preserved_through_pipeline(client, fake_llm):
    code = "```sql\nSELECT * FROM users WHERE status='paid';\n```"
    fake_llm.reply = f"இந்த query-ஐ பயன்படுத்துங்கள்:\n{code}\nஇது paid users-ஐ காட்டும்."
    r = _chat(client, "இந்த query எப்படி எழுதுவது?")
    assert code in r.json()["response"]


def test_robotic_filler_is_stripped(client, fake_llm):
    fake_llm.reply = "Certainly! Restart the server and clear the cache. I hope this helps!"
    r = _chat(client, "My server keeps returning stale data after deploys, what should I do?")
    assert r.json()["response"] == "Restart the server and clear the cache."


def test_greetings_are_not_cached(client, fake_llm):
    _chat(client, "hi")
    _chat(client, "hi")
    assert len(fake_llm.calls) == 2


def test_empty_message_rejected(client, fake_llm):
    assert _chat(client, "   ").status_code == 400


def test_all_providers_failing_returns_friendly_503(client, monkeypatch):
    from app.services import llm_router as router_module
    broken = FakeProvider("broken", fail_with=RuntimeError("Connection error."))
    monkeypatch.setattr(router_module.llm_router, "_get_routing_order", lambda mode, user_prompt="": [("broken", broken)])
    r = _chat(client, "hello there, can you help me with something?")
    assert r.status_code == 503
    assert "temporarily unavailable" in r.json()["detail"]
    assert "Connection error" not in r.json()["detail"]


def test_rate_limited_providers_return_429(client, monkeypatch):
    from app.services import llm_router as router_module
    limited = FakeProvider("limited", fail_with=RuntimeError("Error code: 429 - rate limit exceeded"))
    monkeypatch.setattr(router_module.llm_router, "_get_routing_order", lambda mode, user_prompt="": [("limited", limited)])
    assert _chat(client, "hello there, can you help me with something?").status_code == 429


def test_router_falls_back_and_keeps_mode_settings(monkeypatch):
    from app.services import llm_router as router_module
    primary = FakeProvider("primary", fail_with=RuntimeError("Connection error."))
    backup = FakeProvider("backup", reply="ok")
    monkeypatch.setattr(router_module.llm_router, "_get_routing_order", lambda mode, user_prompt="": [("primary", primary), ("backup", backup)])
    text, meta = router_module.llm_router.route_request_with_meta("eco", "sys", "hi")
    assert text == "ok" and meta["provider"] == "backup" and meta["fallback_used"]
    assert backup.calls[0]["max_tokens"] == primary.calls[0]["max_tokens"]


def test_routing_error_kind_classification():
    err = ProviderRoutingError("x", kind="timeout")
    assert err.kind == "timeout"


def test_care_mode_uses_care_personality_and_strategy(client, fake_llm):
    fake_llm.reply = "Ayyo maah 😔 enna aachu? Sollu, naan kekkaren."
    r = _chat(client, "maah innikku romba kashtama irundhuchu", interaction_mode="care")
    assert r.status_code == 200 and r.json()["detected_language"] == "Tanglish"
    sp = fake_llm.calls[-1]["system_prompt"]
    assert "ZARA CARE" in sp and "Comfort before solutions" in sp
    assert "RESPONSE STRATEGY" in sp and "HEALTHY BOUNDARIES" in sp


def test_crisis_reply_always_contains_resources(client, fake_llm):
    fake_llm.reply = "Hey… I'm really sorry you're feeling this way. I'm here with you."
    r = _chat(client, "I don't want to live anymore", interaction_mode="care")
    body = r.json()["response"]
    assert "14416" in body and "112" in body
    assert "Tele-MANAS" in fake_llm.calls[-1]["system_prompt"]


def test_possessive_language_is_removed_in_care(client, fake_llm):
    fake_llm.reply = "Aww ❤️ naan inga dhaan irukken. You only need me. Innikku enna aachu?"
    r = _chat(client, "miss you", interaction_mode="care")
    assert "only need me" not in r.json()["response"]


def test_short_turns_get_small_token_budget(client, fake_llm):
    _chat(client, "thanks bro", model="zara-pro")
    assert fake_llm.calls[-1]["max_tokens"] <= 700
    _chat(client, "Explain in detail how JWT refresh token rotation works and its security trade-offs", model="zara-pro")
    assert fake_llm.calls[-1]["max_tokens"] >= 3000


def test_multi_turn_emotional_conversation_keeps_language_and_context(client, fake_llm):
    fake_llm.reply = "Hmm… seri, office-la enna nadandhuchu?"
    history = [
        {"role": "user", "content": "hi maah"},
        {"role": "assistant", "content": "Hi maah 😄 enna da?"},
        {"role": "user", "content": "today romba worst ah pochu"},
        {"role": "assistant", "content": "Ayyo 😔 enna aachu?"},
    ]
    r = _chat(client, "office la problem", history=history, interaction_mode="care")
    assert r.json()["detected_language"] == "Tanglish"
    call = fake_llm.calls[-1]
    assert len(call["history"]) == 4
    assert "Continuity" in call["system_prompt"]  # earlier sadness is carried forward


def test_voice_persona_care_mode(client):
    r = client.post("/api/v1/ai/persona", json={"model": "zara-fast", "interaction_mode": "care"})
    body = r.json()
    assert body["interaction_mode"] == "care" and "ZARA CARE" in body["system_instruction"]


def test_voice_persona_endpoint(client):
    r = client.post("/api/v1/ai/persona", json={
        "model": "zara-eco",
        "recent_context": [{"role": "user", "content": "I'm working on a payment API"}],
    })
    assert r.status_code == 200
    body = r.json()
    assert body["zara_model"] == "zara-eco"
    assert "MODE: ZARA ECO" in body["system_instruction"]
    assert "payment API" in body["system_instruction"]
