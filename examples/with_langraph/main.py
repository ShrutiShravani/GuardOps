"""
GuardOps + LangGraph Example
=============================

Shows how GuardOps drops into a real LangGraph pipeline with zero
framework-specific wiring.  The @guard_runtime decorator works at the
Python function boundary — LangGraph never needs to know GuardOps exists.

Architecture:

    User Input
         │
         ▼
    ┌──────────┐      @guard_runtime("ResearchAgent")
    │ Research │ ──►  GuardOps checks: cost ceiling
    │  Agent   │
    └──────────┘
         │
         ▼
    ┌──────────┐      @guard_runtime("WriterAgent")
    │  Writer  │ ──►  GuardOps checks: output schema + length
    │  Agent   │
    └──────────┘
         │
         ▼
    ┌──────────┐      @guard_runtime("ReviewAgent")
    │  Review  │ ──►  GuardOps checks: price floor on quoted cost
    │  Agent   │
    └──────────┘
         │
         ▼
    Final Answer

NOTE: This example uses a *mock* LangGraph-style state machine to avoid
requiring langgraph as a dependency.  The guard pattern is identical in
a real LangGraph graph — just replace the MockGraph with StateGraph.

Optional — for a real LangGraph run:
    pip install "guardops[telemetry]" langgraph langchain-openai
    OPENAI_API_KEY=sk-...

Run:
    cd examples/with_langgraph
    python main.py
"""

import asyncio
import os
import sys
from typing import TypedDict, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from guardops import guard_runtime, GuardOpsRefusalIntercept, GuardRegistry
from guardops.config import GuardConfig, ConditionType, FallbackStrategy

# ─── Register rules programmatically (no manifest file needed) ───────────────
# In a real project you'd use guard_manifest.json + init_guardops() instead.

GuardRegistry.register("ResearchAgent", [
    GuardConfig(
        metric_key="estimated_cost_usd",
        condition_type=ConditionType.OVER_CEILING,
        boundary_limit=10.00,
        fallback_value="Research budget exceeded — switching to cached results.",
        strategy=FallbackStrategy.SHORT_CIRCUIT,
        breach_tag="RESEARCH_COST_OVER_BUDGET",
    ),
])

GuardRegistry.register("WriterAgent", [
    GuardConfig(
        metric_key="word_count",
        condition_type=ConditionType.OVER_CEILING,
        boundary_limit=500,
        fallback_value=500,
        strategy=FallbackStrategy.DATA_OVERRIDE,
        breach_tag="OUTPUT_TOO_LONG",
    ),
])

GuardRegistry.register("ReviewAgent", [
    GuardConfig(
        metric_key="quoted_price_usd",
        condition_type=ConditionType.UNDER_FLOOR,
        boundary_limit=1.00,
        fallback_value=1.00,
        strategy=FallbackStrategy.DATA_OVERRIDE,
        breach_tag="QUOTED_PRICE_UNDER_FLOOR",
    ),
])


# ─── LangGraph-compatible TypedDict state ─────────────────────────────────────
# GuardOps works on dict payloads — TypedDict is just a dict at runtime.

class AgentState(TypedDict):
    query: str
    research_notes: str
    estimated_cost_usd: float
    draft_output: str
    word_count: int
    quoted_price_usd: float
    final_answer: str
    agent_trace: List[str]


# ─── Agent node functions ──────────────────────────────────────────────────────

@guard_runtime(node_name="ResearchAgent")
async def research_agent(state: dict) -> dict:
    """
    Searches for information and estimates retrieval cost.
    GuardOps halts the pipeline if cost exceeds the budget.
    """
    print(f"\n  [ResearchAgent] Researching: \"{state['query']}\" …")
    await asyncio.sleep(0.05)

    state["research_notes"] = f"Findings for: {state['query']}"
    state["estimated_cost_usd"] = state.get("_mock_cost", 3.50)
    return state


@guard_runtime(node_name="WriterAgent")
async def writer_agent(state: dict) -> dict:
    """
    Drafts the output from research notes.
    GuardOps caps the word_count if the draft is too long.
    """
    print(f"  [WriterAgent] Drafting output …")
    await asyncio.sleep(0.05)

    mock_word_count = state.get("_mock_word_count", 280)
    state["draft_output"] = f"Draft based on: {state['research_notes']}"
    state["word_count"] = mock_word_count
    return state


@guard_runtime(node_name="ReviewAgent")
async def review_agent(state: dict) -> dict:
    """
    Reviews and prices the output.
    GuardOps enforces a minimum price floor.
    """
    print(f"  [ReviewAgent] Reviewing draft …")
    await asyncio.sleep(0.05)

    state["quoted_price_usd"] = state.get("_mock_price", 5.00)
    state["final_answer"] = state["draft_output"]
    return state


# ─── Mock graph (identical pattern to a real LangGraph StateGraph) ────────────

async def run_graph(initial_state: dict, label: str) -> None:
    print(f"\n{'━' * 55}")
    print(f"  Scenario: {label}")
    print(f"{'━' * 55}")

    state = {**initial_state, "agent_trace": []}

    try:
        state = await research_agent(state)
        state = await writer_agent(state)
        state = await review_agent(state)

        print(f"\n  ✅ Graph complete.")
        print(f"  word_count:       {state['word_count']}")
        print(f"  quoted_price_usd: ${state['quoted_price_usd']:.2f}")
        print(f"  final_answer:     {state['final_answer'][:60]} …")

    except GuardOpsRefusalIntercept as intercept:
        print(f"\n  🚨 Graph halted by GuardOps!")
        print(f"  Breach:  {intercept.breach_tag}")
        print(f"  Message: {intercept.fallback_message}")


# ─── Demo ─────────────────────────────────────────────────────────────────────

async def main():
    print("\n" + "═" * 55)
    print("  GuardOps + LangGraph Pattern Demo")
    print("═" * 55)

    # Scenario 1: Normal run — no interventions
    await run_graph(
        {"query": "What is transformer attention?",
         "_mock_cost": 2.50, "_mock_word_count": 280, "_mock_price": 5.00},
        label="Happy path — no interventions",
    )

    # Scenario 2: Word count over ceiling — DATA_OVERRIDE clamps it
    await run_graph(
        {"query": "Explain the entire history of deep learning",
         "_mock_cost": 4.00, "_mock_word_count": 820, "_mock_price": 7.50},
        label="Word count over ceiling (DATA_OVERRIDE)",
    )

    # Scenario 3: Price under floor — DATA_OVERRIDE applies floor
    await run_graph(
        {"query": "Summarise this paragraph",
         "_mock_cost": 1.00, "_mock_word_count": 120, "_mock_price": 0.25},
        label="Quoted price under floor (DATA_OVERRIDE)",
    )

    # Scenario 4: Research cost over budget — SHORT_CIRCUIT halts graph
    await run_graph(
        {"query": "Index all 10M documents in this corpus",
         "_mock_cost": 42.00, "_mock_word_count": 300, "_mock_price": 6.00},
        label="Research cost over budget (SHORT_CIRCUIT)",
    )

    print("\n" + "═" * 55)
    print("  Real LangGraph integration:")
    print()
    print("    graph = StateGraph(AgentState)")
    print("    graph.add_node('research', research_agent)  # decorated ")
    print("    graph.add_node('writer',   writer_agent)    # decorated ")
    print("    graph.add_node('review',   review_agent)    # decorated ")
    print("    graph.add_edge(START, 'research')")
    print("    graph.add_edge('research', 'writer')")
    print("    graph.add_edge('writer', 'review')")
    print("    graph.add_edge('review', END)")
    print("    app = graph.compile()")
    print("    result = await app.ainvoke({'query': '...'})")
    print("═" * 55 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
