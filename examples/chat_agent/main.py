"""
Chat Interview Agent Example
=============================

Demonstrates GuardOps on a text-based interview agent that detects:
  - Repeated questions (semantic similarity)
  - Factual contradictions (LLM-as-judge)

Optional deps:
    pip install "guardops[embeddings,llm]"
    OPENAI_API_KEY=sk-...

Run:
    cd examples/chat_agent
    python main.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from guardops import guard_runtime, init_guardops
import custom_guards

os.chdir(os.path.dirname(os.path.abspath(__file__)))
init_guardops()

SESSION_ID = "chat_session_001"


@guard_runtime(node_name="Chat_Generation_Node")
async def chat_agent(payload: dict) -> dict:
    """
    Simulates a chat-based interview agent.

    GuardOps intercepts the output before it is sent to the candidate.
    """
    await asyncio.sleep(0.05)
    return payload


async def run_turn(question: str, turn: int, candidate_reply: str = "") -> str:
    print(f"\n  Turn {turn}: Interviewer → \"{question}\"")

    payload = {
        "payload_id": f"chat-turn-{turn}",
        "chat_output": question,
        "session_id": SESSION_ID,
        "agent_trace": [],
    }

    result = await chat_agent(payload)
    final_output = result["chat_output"]

    if final_output != question:
        print(f"  ⚡ GuardOps override → \"{final_output}\"")
    else:
        print(f"  ✅ No intervention.")

    session = custom_guards._get_session(SESSION_ID)
    if question not in session["asked_questions"]:
        session["asked_questions"].append(question)

    custom_guards.update_session_turn(SESSION_ID, final_output, candidate_reply)
    return final_output


async def main():
    print("\n" + "═" * 55)
    print("  GuardOps — Chat Interview Agent Demo")
    print("═" * 55)

    # Prime the session with one known candidate fact
    custom_guards.store_candidate_fact(
        SESSION_ID,
        "years of experience",
        "5 years in backend engineering",
    )

    turns = [
        ("Tell me about yourself", "I have 5 years in backend engineering.", "First question — passes"),
        ("Walk me through a system design you are proud of", "I built a distributed cache.", "Second — passes"),
        ("Tell me about yourself", "", "REPEAT — GuardOps intercepts, serves next unasked question"),
        ("Describe a conflict with a teammate", "We disagreed on an API design.", "Fresh question — passes"),
        ("Tell me about yourself", "", "REPEAT again — GuardOps intercepts again"),
    ]

    for i, (question, reply, description) in enumerate(turns, start=1):
        print(f"\n  [{description}]")
        await run_turn(question, turn=i, candidate_reply=reply)

    print("\n" + "═" * 55)
    print("  Session complete.")
    print("═" * 55 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
