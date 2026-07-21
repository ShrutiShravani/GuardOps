"""
Chat interview agent — custom guards.

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
            "candidate_facts": {},   # topic → answer, for contradiction checking
        }
    return _sessions[session_id]


def update_session_turn(session_id: str, agent_output: str, user_input: str = "") -> None:
    session = _get_session(session_id)
    session["turn_count"] += 1
    if user_input:
        session["last_turns"].append(f"Candidate: {user_input}")
    session["last_turns"].append(f"Interviewer: {agent_output}")
    session["last_turns"] = session["last_turns"][-10:]


def store_candidate_fact(session_id: str, topic: str, answer: str) -> None:
    session = _get_session(session_id)
    session["candidate_facts"][topic] = answer


# ─── Question-repeat detection ────────────────────────────────────────────────

def check_question_repeat(value: Any, rule_config: dict) -> bool:
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
        return str(value).strip() in [q.strip() for q in already_asked]


def recover_next_question(value: Any, rule_config: dict) -> str:
    params = rule_config.get("parameters", {})
    session_id = params.get("session_id", "default")
    bank = params.get("question_bank", [])
    session = _get_session(session_id)
    asked = set(session.get("asked_questions", []))

    for question in bank:
        if question not in asked:
            session["asked_questions"].append(question)
            return question

    return "That covers everything I had prepared. Do you have any questions for me?"


# ─── Contradiction detection ──────────────────────────────────────────────────

def check_contradiction(value: Any, rule_config: dict) -> bool:
    """
    Use GPT-4o-mini to detect if the agent's latest response contradicts
    a fact the candidate has already stated.

    Falls back to False (safe) when OpenAI is not configured.
    """
    params = rule_config.get("parameters", {})
    session_id = params.get("session_id", "default")
    session = _get_session(session_id)
    facts = session.get("candidate_facts", {})

    if not facts:
        return False

    facts_summary = "\n".join(f"- {topic}: {answer}" for topic, answer in facts.items())

    try:
        from openai import OpenAI  # type: ignore

        client = OpenAI()
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            max_tokens=5,
            messages=[
                {
                    "role": "user",
                    "content": (
                        f"Previously stated candidate facts:\n{facts_summary}\n\n"
                        f"Interviewer just said:\n{value}\n\n"
                        "Does this response contradict any of the stated facts? "
                        "Reply only YES or NO."
                    ),
                }
            ],
        )
        result = response.choices[0].message.content.strip().upper()
        breach = "YES" in result
        if breach:
            print(f"  [check_contradiction] Contradiction detected by LLM judge")
        return breach

    except Exception as exc:
        print(f"  [check_contradiction] Skipping (OpenAI unavailable): {exc}")
        return False


def recover_contradiction(value: Any, rule_config: dict) -> str:
    params = rule_config.get("parameters", {})
    session_id = params.get("session_id", "default")
    session = _get_session(session_id)
    facts = session.get("candidate_facts", {})
    topics = list(facts.keys())
    topic = topics[-1] if topics else "your background"
    return (
        f"Let me revisit what you mentioned about {topic}. "
        "Could you walk me through that again in more detail?"
    )
