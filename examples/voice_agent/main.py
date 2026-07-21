"""
Voice Interview Agent Example
==============================

Demonstrates GuardOps intercepting a voice interview agent that:
  - Detects repeated questions via semantic similarity
  - Detects context loss via LLM-as-judge
  - Recovers gracefully with the next unasked question

Optional deps:
    pip install "guardops[embeddings,llm]"
    OPENAI_API_KEY=sk-...

Run (works without OpenAI — embeddings fall back to exact-match):
    cd examples/voice_agent
    python main.py
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from guardops import guard_runtime, GuardOpsRefusalIntercept, init_guardops
import custom_guards  # loads session helpers into scope

os.chdir(os.path.dirname(os.path.abspath(__file__)))
init_guardops()

SESSION_ID = "voice_interview_001"


@guard_runtime(node_name="Voice_Generation_Node")
async def voice_agent(payload: dict) -> dict:
    """
    Simulates a voice interview agent.

    In production this would call your TTS pipeline.
    GuardOps intercepts the output before it is spoken to the candidate.
    """
    await asyncio.sleep(0.05)
    return payload


async def run_turn(question: str, turn: int) -> str:
    print(f"\n  Turn {turn}: Agent asks → \"{question}\"")

    payload = {
        "payload_id": f"interview-turn-{turn}",
        "voice_output": question,
        "session_id": SESSION_ID,
        "agent_trace": [],
    }

    result = await voice_agent(payload)
    final_output = result["voice_output"]

    if final_output != question:
        print(f"  ⚡ GuardOps override → \"{final_output}\"")
    else:
        print(f"  ✅ No intervention — question delivered as-is.")

    # Record the question as asked
    session = custom_guards._get_session(SESSION_ID)
    if question not in session["asked_questions"]:
        session["asked_questions"].append(question)
    custom_guards.update_session_turn(SESSION_ID, final_output)

    return final_output


async def main():
    print("\n" + "═" * 55)
    print("  GuardOps — Voice Interview Agent Demo")
    print("═" * 55)

    turns = [
        ("Tell me about yourself", "First question — should pass"),
        ("Walk me through a system design you are proud of", "Second question — should pass"),
        ("Tell me about yourself", "REPEAT — GuardOps should intercept and serve next unasked question"),
        ("Describe a conflict with a teammate", "Fresh question — should pass"),
        ("Walk me through a system design you are proud of", "REPEAT again — should serve next"),
    ]

    for i, (question, description) in enumerate(turns, start=1):
        print(f"\n  [{description}]")
        await run_turn(question, turn=i)

    print("\n" + "═" * 55)
    print("  Interview session complete.")
    print("═" * 55 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
