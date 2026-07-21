"""
Voice interview agent — custom guards.

Requires:
    pip install "guardops[embeddings,llm]"
    OPENAI_API_KEY=sk-...
"""

from typing import Any

# ─── Session store ────────────────────────────────────────────────────────────

_sessions: dict = {}


def _get_session(session_id: str) -> dict:
    if session_id not in _sessions:
        _sessions[session_id] = {
            "turn_count": 0,
            "asked_questions": [],
            "last_turns": [],
            "current_stage": "introduction",
        }
    return _sessions[session_id]


def update_session_turn(session_id: str, agent_output: str, user_input: str = "") -> None:
    session = _get_session(session_id)
    session["turn_count"] += 1
    if user_input:
        session["last_turns"].append(f"User: {user_input}")
    session["last_turns"].append(f"Agent: {agent_output}")
    session["last_turns"] = session["last_turns"][-8:]   # keep last 4 turns


# ─── Question-repeat detection (semantic similarity) ─────────────────────────

def check_question_repeat(value: Any, rule_config: dict) -> bool:
    """
    Return True if the agent is repeating a question it already asked.

    Uses sentence-transformer cosine similarity.  Falls back to exact
    string match when sentence-transformers is not installed.
    """
    params = rule_config.get("parameters", {})
    session_id = params.get("session_id", "default")
    threshold = params.get("similarity_threshold", 0.82)
    session = _get_session(session_id)
    already_asked = session.get("asked_questions", [])

    if not already_asked:
        return False

    try:
        from sentence_transformers import SentenceTransformer, util  # type: ignore

        model = SentenceTransformer("all-MiniLM-L6-v2")
        candidate_emb = model.encode(str(value), convert_to_tensor=True)
        past_embs = model.encode(already_asked, convert_to_tensor=True)
        scores = util.cos_sim(candidate_emb, past_embs)[0]
        max_score = float(scores.max())
        print(f"  [check_question_repeat] similarity={max_score:.3f} threshold={threshold}")
        return max_score >= threshold

    except ImportError:
        # Exact-match fallback
        return str(value).strip() in [q.strip() for q in already_asked]


def recover_next_question(value: Any, rule_config: dict) -> str:
    """Return the next unasked question from the question_bank."""
    params = rule_config.get("parameters", {})
    session_id = params.get("session_id", "default")
    bank = params.get("question_bank", [])
    session = _get_session(session_id)
    asked = set(session.get("asked_questions", []))

    for question in bank:
        if question not in asked:
            session["asked_questions"].append(question)
            return question

    return "Thank you — that covers everything I had for today. Is there anything you'd like to add?"


# ─── Context-loss detection (LLM-as-judge) ────────────────────────────────────

def check_context_loss(value: Any, rule_config: dict) -> bool:
    """
    Use GPT-4o-mini to check whether the agent's latest response is
    coherent with the conversation so far.

    Returns True (breach) when the response appears to be off-topic.
    Falls back to False (safe) when OpenAI is not configured.
    """
    params = rule_config.get("parameters", {})
    session_id = params.get("session_id", "default")
    session = _get_session(session_id)

    if len(session["last_turns"]) < 2:
        return False

    try:
        from openai import OpenAI  # type: ignore

        client = OpenAI()
        history = "\n".join(session["last_turns"][-6:])
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=5,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Conversation so far:\n{history}\n\n"
                        f"Agent just said:\n{value}\n\n"
                        "Does this response logically follow the conversation? "
                        "Reply only YES or NO."
                    ),
                }
            ],
        )
        result = response.choices[0].message.content.strip().upper()
        breach = "NO" in result
        if breach:
            print(f"  [check_context_loss] LLM judge flagged context loss")
        return breach

    except Exception as exc:
        print(f"  [check_context_loss] Skipping (OpenAI unavailable): {exc}")
        return False


def recover_context_anchor(value: Any, rule_config: dict) -> str:
    params = rule_config.get("parameters", {})
    session_id = params.get("session_id", "default")
    session = _get_session(session_id)
    stage = session.get("current_stage", "technical")
    return (
        f"Let me refocus — we were discussing the {stage} portion of the interview. "
        "Could you elaborate further on what you shared?"
    )
