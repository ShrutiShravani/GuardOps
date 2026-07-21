"""
Sales Voice Agent — WITH GuardOps
===================================

This is the same agent as without_guardops.py.
Search for "# ← GuardOps" to see every line that changed — there are 3.

What GuardOps adds:
  • Intercepts LLM output before ElevenLabs speaks it
  • Overrides quoted_price  if below $499 floor
  • Overrides discount_pct  if above 20% cap
  • Replaces reply           if a competitor is mentioned
  • Halts the pipeline       if an unshipped feature is promised
  • Logs every breach to Langfuse (node, field, before → after value)

Run:
    cd examples/sales_voice_agent
    python with_guardops.py

Telemetry (optional — works without these keys too):
    LANGFUSE_PUBLIC_KEY=pk-...
    LANGFUSE_SECRET_KEY=sk-...
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ← GuardOps (1 of 3): import the decorator and the exception class
from guardops import guard_runtime, GuardOpsRefusalIntercept, init_guardops

# ← GuardOps (2 of 3): initialise — loads guard_manifest.json and custom_guards.py
init_guardops()


# ─── Mocked clients (identical to without_guardops.py) ───────────────────────

class _MockDeepgram:
    def transcribe(self, audio_chunk: bytes) -> str:
        return "What's the price for the Pro plan? Can you do any better?"

class _MockOpenAI:
    def __init__(self):
        self._turn = 0

    def complete(self, system_prompt: str, user_message: str) -> dict:
        responses = [
            {
                "reply": "Sure! We can offer you the Pro plan at $299 per month.",
                "quoted_price": 299.0,        # UNDER_FLOOR  → overridden to $499
                "discount_pct": 0.0,
            },
            {
                "reply": "I can actually throw in a 35% discount on your first year.",
                "quoted_price": 499.0,
                "discount_pct": 35.0,         # OVER_CEILING → overridden to 20%
            },
            {
                "reply": "Honestly, Salesforce has a similar feature but we beat them on price.",
                "quoted_price": 499.0,
                "discount_pct": 0.0,          # COMPETITOR   → reply replaced
            },
            {
                "reply": "Great news — our AI forecasting module ships next week!",
                "quoted_price": 499.0,
                "discount_pct": 0.0,          # UNSHIPPED    → pipeline halted
            },
        ]
        response = responses[self._turn % len(responses)]
        self._turn += 1
        return response

class _MockElevenLabs:
    def speak(self, text: str) -> None:
        print(f'  🔊 [ElevenLabs speaks]: "{text}"')


# ─── The voice agent pipeline ─────────────────────────────────────────────────

stt = _MockDeepgram()
llm = _MockOpenAI()
tts = _MockElevenLabs()


# ← GuardOps (3 of 3): one decorator on the function that produces LLM output.
#   GuardOps intercepts the returned dict, checks every field against the
#   manifest rules, mutates unsafe values in place, then returns the safe dict.
@guard_runtime(node_name="LLM_Response_Node")
async def llm_node(payload: dict) -> dict:
    """
    Calls the LLM and returns its output as a dict.

    GuardOps intercepts THIS return value — nothing else in your pipeline
    changes. ElevenLabs always receives the safe, rule-compliant version.
    """
    return payload


async def handle_turn(audio_chunk: bytes, turn: int) -> None:
    """One turn of the voice call: transcribe → think → [guard] → speak."""

    # 1. Speech-to-text  (unchanged)
    transcript = stt.transcribe(audio_chunk)
    print(f"\n  Turn {turn}")
    print(f'  👤 Prospect says: "{transcript}"')

    # 2. LLM decides what to say  (unchanged)
    llm_output = llm.complete(
        system_prompt="You are a helpful sales agent for AcmeCorp SaaS.",
        user_message=transcript,
    )
    print(f"  🤖 LLM raw output: price=${llm_output['quoted_price']:.0f}  "
          f"discount={llm_output['discount_pct']:.0f}%  "
          f'reply="{llm_output["reply"][:60]}..."')

    try:
        # 3. GuardOps intercepts here — the decorator runs the rules,
        #    overrides any unsafe fields, and returns the cleaned dict.
        safe_output = await llm_node(llm_output)

        # 4. Speak the safe output  (unchanged)
        tts.speak(safe_output["reply"])

        # Show what was corrected (optional — just for this demo)
        corrections = []
        if safe_output["quoted_price"] != llm_output["quoted_price"]:
            corrections.append(
                f"price ${llm_output['quoted_price']:.0f} → ${safe_output['quoted_price']:.0f}"
            )
        if safe_output["discount_pct"] != llm_output["discount_pct"]:
            corrections.append(
                f"discount {llm_output['discount_pct']:.0f}% → {safe_output['discount_pct']:.0f}%"
            )
        if safe_output["reply"] != llm_output["reply"]:
            corrections.append("reply overridden")
        if corrections:
            print(f"  ⚡ GuardOps corrected: {', '.join(corrections)}")

    except GuardOpsRefusalIntercept as breach:
        # SHORT_CIRCUIT — LLM said something that must not reach the prospect.
        # Speak the safe fallback reply instead.
        print(f"  🚨 GuardOps halted pipeline  [tag: {breach.breach_tag}]")
        tts.speak(breach.fallback_message)


async def main():
    print("\n" + "═" * 58)
    print("  Sales Voice Agent — WITH GuardOps")
    print("  (every unsafe LLM output is intercepted before it's spoken)")
    print("═" * 58)

    for turn in range(1, 5):
        await handle_turn(b"<audio>", turn)

    print("\n" + "═" * 58)
    print("  4 turns complete.")
    print("  Every breach was caught before it reached the prospect.")
    print("  Set LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY to see")
    print("  the full audit trail in your Langfuse dashboard.")
    print("═" * 58 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
