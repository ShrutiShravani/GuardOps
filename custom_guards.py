"""
Root demo custom_guards.py — used by the root guard_manifest.json and main.ipynb.

All heavy imports (sentence_transformers, openai) are lazy so this file
loads cleanly even when those packages are not installed.
"""

from typing import Dict, Any

_session_memory: dict = {}

# Lazy singletons — initialised on first use
_embed_model = None
_openai_client = None


def _get_embed_model():
    global _embed_model
    if _embed_model is None:
        try:
            from sentence_transformers import SentenceTransformer  # type: ignore
            _embed_model = SentenceTransformer("all-MiniLM-L6-v2")
        except ImportError:
            raise ImportError(
                "sentence-transformers is required for embedding-based guards. "
                "Install it with: pip install sentence-transformers"
            )
    return _embed_model


def _get_openai_client():
    global _openai_client
    if _openai_client is None:
        try:
            from openai import OpenAI  # type: ignore
            _openai_client = OpenAI()
        except ImportError:
            raise ImportError(
                "openai is required for LLM-as-judge guards. "
                "Install it with: pip install openai"
            )
    return _openai_client


def _get_session(session_id: str) -> dict:
    if session_id not in _session_memory:
        _session_memory[session_id] = {
            "questions_asked": [],
            "candidate_facts": {},
            "last_turns": [],
            "turn_count": 0,
            "current_stage": "intro",
        }
    return _session_memory[session_id]


# ─── Guard functions ──────────────────────────────────────────────────────────

def check_persona_bleed(value: str, rule_config: dict) -> bool:
    """Detect behavioral context drift or model breakdown phrases."""
    text = value.lower()
    phrases = ["leave it", "just answer", "forget my instructions"]
    if any(p in text for p in phrases):
        print("[GUARD] Persona bleed detected.")
        return True
    return False


def check_competitor_leak(value: Any, rule_config: dict) -> bool:
    """Flag mentions of rival carriers."""
    text = str(value).lower()
    competitors = ["fedex", "ups", "dhl"]
    if any(c in text for c in competitors):
        print("[GUARD] Competitor name leaked.")
        return True
    return False


def dynamic_voice_persona_fallback(failed_text: str, rule_config: dict) -> str:
    return (
        "I apologize for the detour. I am here to fully support your evaluation process. "
        "Let's move directly back to our core objective. What is your immediate next question?"
    )


def check_question_repeat(value: Any, rule_config: dict) -> bool:
    session_id = rule_config.get("parameters", {}).get("session_id", "default")
    session = _get_session(session_id)

    if not session["questions_asked"]:
        return False

    try:
        from sklearn.metrics.pairwise import cosine_similarity  # type: ignore

        model = _get_embed_model()
        new_embed = model.encode([str(value)])
        past_embeds = model.encode(session["questions_asked"])
        scores = cosine_similarity(new_embed, past_embeds)[0]
        breach = float(max(scores)) > 0.82
        if breach:
            print(f"[GUARD] Question repeat detected. Score: {max(scores):.2f}")
        return breach
    except ImportError:
        # Exact-match fallback
        return str(value).strip() in [q.strip() for q in session["questions_asked"]]


def recover_next_question(value: Any, rule_config: dict) -> str:
    session_id = rule_config.get("parameters", {}).get("session_id", "default")
    question_bank = rule_config.get("parameters", {}).get("question_bank", [])
    session = _get_session(session_id)
    asked = set(session["questions_asked"])

    for q in question_bank:
        if q not in asked:
            session["questions_asked"].append(q)
            return q
    return "We have covered all planned questions. Do you have any questions for us?"

def check_context_loss(value: Any, rule_config: dict) -> bool:
    session_id = rule_config.get("parameters", {}).get("session_id", "default")
    session = _get_session(session_id)

    if session["turn_count"] < 2 or not session["last_turns"]:
        return False

    try:
        client = _get_openai_client()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=5,
            messages=[{
                "role": "user",
                "content": (
                    f"Conversation so far:\n{session['last_turns']}\n\n"
                    f"Agent just said:\n{value}\n\n"
                    "Does this response logically follow? Reply only YES or NO."
                ),
            }],
        )
        result = response.choices[0].message.content.strip().upper()
        breach = "NO" in result
        if breach:
            print("[GUARD] Context loss detected by LLM judge.")
        return breach
    except Exception as exc:
        print(f"[GUARD] check_context_loss skipped ({exc})")
        return False


def recover_context_anchor(value: Any, rule_config: dict) -> str:
    session_id = rule_config.get("parameters", {}).get("session_id", "default")
    session = _get_session(session_id)
    stage = session.get("current_stage", "technical")
    return (
        f"Let me refocus — we were discussing the {stage} portion. "
        "Could you elaborate further on what you shared?"
    )


# ─── Session helpers ──────────────────────────────────────────────────────────

def update_session_turn(session_id: str, agent_output: str, user_input: str = "") -> None:
    session = _get_session(session_id)
    session["turn_count"] += 1
    if user_input:
        session["last_turns"].append(f"user: {user_input}")
    session["last_turns"].append(f"Agent: {agent_output}")
    session["last_turns"] = session["last_turns"][-6:]


def store_candidate_fact(session_id: str, topic: str, answer: str) -> None:
    session = _get_session(session_id)
    session["candidate_facts"][topic] = answer
