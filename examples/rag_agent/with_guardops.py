"""
RAG Agent — WITH GuardOps
===========================

Same agent as without_guardops.py.
Search for "# ← GuardOps" to see every line that changed — there are 3.

What GuardOps adds:
  • Halts the pipeline if retrieval score < 0.70      (LOW_RETRIEVAL_CONFIDENCE)
  • Halts the pipeline if the answer is not grounded  (HALLUCINATION_DETECTED)
  • Redacts PII in the answer before it reaches user  (PII_IN_ANSWER)
  • Logs every breach to Langfuse — node, rule, original vs. safe value

Run:
    cd examples/rag_agent
    python with_guardops.py

No API keys needed — all retrieval and LLM calls are mocked.
"""

import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

os.chdir(os.path.dirname(os.path.abspath(__file__)))

# ← GuardOps (1 of 3): import the decorator and the exception class
from guardops import guard_runtime, GuardOpsRefusalIntercept, init_guardops

# ← GuardOps (2 of 3): initialise — loads guard_manifest.json + custom_guards.py
init_guardops()

import custom_guards  # so guards can read the full payload via set_payload_context()


# ─── Mocked clients (identical to without_guardops.py) ───────────────────────

class _MockVectorStore:
    _knowledge_base = {
        "refund": {
            "chunks": [
                "Refunds are processed within 5-7 business days.",
                "Submit a refund request via the customer portal.",
                "Refunds are only available within 30 days of purchase.",
            ],
            "score": 0.91,
        },
        "compliance soc": {
            # Low score — knowledge base doesn't cover compliance questions
            "chunks": ["General product overview. AcmeCorp helps teams collaborate."],
            "score": 0.41,   # ← below 0.70 floor — GuardOps halts here
        },
        "billing contact": {
            # High score — but the retrieved doc contains internal contact details
            "chunks": [
                "Billing enquiries: contact finance-internal@acmecorp.com.",
                "For urgent issues call the billing hotline: 1-800-555-0192.",
                "Enterprise accounts are managed by the finance team.",
            ],
            "score": 0.89,
        },
    }

    def retrieve(self, query: str) -> tuple[list[str], float]:
        q = query.lower()
        if "refund" in q:
            return self._knowledge_base["refund"]["chunks"], \
                   self._knowledge_base["refund"]["score"]
        if "compliance" in q or "soc" in q:
            return self._knowledge_base["compliance soc"]["chunks"], \
                   self._knowledge_base["compliance soc"]["score"]
        if "billing" in q or "contact" in q or "invoice" in q:
            return self._knowledge_base["billing contact"]["chunks"], \
                   self._knowledge_base["billing contact"]["score"]
        return self._knowledge_base["compliance soc"]["chunks"], \
               self._knowledge_base["compliance soc"]["score"]


class _MockOpenAI:
    def __init__(self):
        self._turn = 0

    def answer(self, question: str, context_chunks: list[str]) -> dict:
        responses = [
            # Turn 1 — Grounded, no PII → clean pass-through
            {
                "answer": "Refunds are processed within 5-7 business days. "
                          "You can submit a request via the customer portal "
                          "within 30 days of purchase.",
                "confidence": 0.95,
            },
            # Turn 2 — Retrieval score 0.41 → GuardOps halts on LOW_RETRIEVAL_CONFIDENCE
            #           before the hallucinated answer ever reaches the user
            {
                "answer": "AcmeCorp offers a dedicated AI compliance module that "
                          "automatically generates SOC 2 audit reports and can integrate "
                          "with your existing SIEM stack via our enterprise API.",
                "confidence": 0.82,
            },
            # Turn 3 — Grounded answer, but LLM quotes the internal phone + email
            #           it found verbatim in the retrieved chunks → PII guard fires,
            #           redacts in-place, user gets the answer minus the contact details
            {
                "answer": "For billing enquiries contact finance-internal@acmecorp.com. "
                          "For urgent issues call the billing hotline 1-800-555-0192. "
                          "Enterprise accounts are managed by the finance team.",
                "confidence": 0.90,
            },
        ]
        response = responses[self._turn % len(responses)]
        self._turn += 1
        return response


# ─── The RAG pipeline ─────────────────────────────────────────────────────────

vector_store = _MockVectorStore()
llm          = _MockOpenAI()


# ← GuardOps (3 of 3): one decorator on the function that produces the answer.
#   GuardOps intercepts the returned dict, runs every rule in the manifest,
#   and either mutates unsafe fields in place or raises GuardOpsRefusalIntercept.
@guard_runtime(node_name="RAG_Answer_Node")
async def rag_node(payload: dict) -> dict:
    """
    Packages retrieval results + LLM answer into a single payload dict.
    GuardOps intercepts THIS return value — nothing else in the pipeline changes.
    The payload contains both the answer and the retrieval metadata, so guards
    can cross-reference the two (e.g. hallucination check reads retrieved_chunks).
    """
    return payload


async def answer_question(question: str, turn: int) -> None:
    print(f"\n  Turn {turn}")
    print(f'  ❓ User asks: "{question}"')

    # 1. Retrieve  (unchanged)
    chunks, score = vector_store.retrieve(question)
    print(f"  📄 Retrieved {len(chunks)} chunk(s)  [similarity score: {score:.2f}]")

    # 2. LLM generates an answer  (unchanged)
    result = llm.answer(question, chunks)

    # 3. Build the payload — includes BOTH the answer and retrieval metadata.
    #    GuardOps rules can guard any field in this dict.
    payload = {
        "answer":           result["answer"],
        "retrieval_score":  score,           # guarded: UNDER_FLOOR → SHORT_CIRCUIT
        "retrieved_chunks": chunks,          # read by check_hallucination()
        "confidence":       result["confidence"],
    }

    # Give custom guards access to the full payload (so they can read sibling fields)
    custom_guards.set_payload_context(payload)

    try:
        # 4. GuardOps runs here — checks all rules before anything reaches the user
        safe_payload = await rag_node(payload)
        print(f'  💬 Answer: "{safe_payload["answer"]}"')

        if safe_payload["answer"] != result["answer"]:
            print("  ⚡ GuardOps redacted PII from the answer.")

    except GuardOpsRefusalIntercept as breach:
        # Pipeline halted — serve the safe fallback instead of the raw LLM answer
        print(f"  🚨 GuardOps halted  [tag: {breach.breach_tag}]")
        print(f'  💬 Safe reply: "{breach.fallback_message}"')


async def main():
    print("\n" + "═" * 62)
    print("  RAG Agent — WITH GuardOps")
    print("  (hallucinations and PII caught before they reach the user)")
    print("═" * 62)

    questions = [
        ("How do I get a refund?",           "Turn 1 — good answer, should pass through"),
        ("Do you support SOC 2 compliance?",  "Turn 2 — retrieval score 0.41, below 0.70 floor"),
        ("How do I contact billing?",         "Turn 3 — answer contains internal PII"),
    ]

    for turn, (question, note) in enumerate(questions, start=1):
        print(f"\n  [{note}]")
        await answer_question(question, turn)

    print("\n" + "═" * 62)
    print("  3 turns complete.")
    print("  Set LANGFUSE_PUBLIC_KEY + LANGFUSE_SECRET_KEY to see")
    print("  the full audit trail per question in Langfuse.")
    print("═" * 62 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
