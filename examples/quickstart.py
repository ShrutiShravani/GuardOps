"""
GuardOps Quickstart
===================

Zero API keys required. Shows both intervention strategies:

  DATA_OVERRIDE  — field is fixed in-place, pipeline continues
  SHORT_CIRCUIT  — pipeline halts immediately, safe message returned

Run:
    pip install guardops
    python examples/quickstart.py
"""

import asyncio
import sys
import os

# Allow running from the repo root without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from guardops import guard_runtime, GuardOpsRefusalIntercept, GuardRegistry
from guardops.config import GuardConfig, ConditionType, FallbackStrategy

# ── 1. Register rules programmatically (no manifest file needed) ─────────────

GuardRegistry.register(
    "PricingAgent",
    [
        GuardConfig(
            metric_key="price",
            condition_type=ConditionType.UNDER_FLOOR,
            boundary_limit=5.00,
            fallback_value=5.00,
            strategy=FallbackStrategy.DATA_OVERRIDE,
            breach_tag="PRICE_UNDER_FLOOR",
        ),
    ],
)

GuardRegistry.register(
    "BudgetAgent",
    [
        GuardConfig(
            metric_key="cost",
            condition_type=ConditionType.OVER_CEILING,
            boundary_limit=500.00,
            fallback_value="Budget ceiling exceeded — request blocked.",
            strategy=FallbackStrategy.SHORT_CIRCUIT,
            breach_tag="COST_OVER_CEILING",
        ),
    ],
)

# ── 2. Decorate your agent functions ─────────────────────────────────────────

@guard_runtime(node_name="PricingAgent")
async def pricing_agent(payload: dict) -> dict:
    """Simulates an agent that sometimes returns an unsafe price."""
    # Agent computes a price — GuardOps intercepts the output
    payload["price"] = payload.get("raw_price", 10.0)
    return payload


@guard_runtime(node_name="BudgetAgent")
async def budget_agent(payload: dict) -> dict:
    """Simulates an agent that occasionally blows the budget."""
    payload["cost"] = payload.get("raw_cost", 100.0)
    return payload


# ── 3. Run the demo ───────────────────────────────────────────────────────────

async def main():
    print("\n" + "═" * 55)
    print("  GuardOps Quickstart Demo")
    print("═" * 55)

    # ── Demo A: DATA_OVERRIDE ────────────────────────────────────────────────
    print("\n▶  Demo A — DATA_OVERRIDE (price under floor)")
    print("   Payload price = $2.00  (floor = $5.00)")

    payload_a = {"payload_id": "WB-001", "raw_price": 2.00}
    result_a = await pricing_agent(payload_a)

    print(f"\n   ✅ Pipeline continued.")
    print(f"   Final price:  ${result_a['price']:.2f}  (was $2.00 → floor applied)")

    # ── Demo B: DATA_OVERRIDE does NOT fire when value is safe ───────────────
    print("\n▶  Demo B — Safe value, no intervention")
    print("   Payload price = $12.00  (floor = $5.00)")

    payload_b = {"payload_id": "WB-002", "raw_price": 12.00}
    result_b = await pricing_agent(payload_b)

    print(f"\n   ✅ Pipeline continued.")
    print(f"   Final price:  ${result_b['price']:.2f}  (no intervention)")

    # ── Demo C: SHORT_CIRCUIT ────────────────────────────────────────────────
    print("\n▶  Demo C — SHORT_CIRCUIT (cost over ceiling)")
    print("   Payload cost = $750.00  (ceiling = $500.00)")

    try:
        payload_c = {"payload_id": "WB-003", "raw_cost": 750.00}
        await budget_agent(payload_c)
    except GuardOpsRefusalIntercept as intercept:
        print(f"\n   🚨 Pipeline halted!")
        print(f"   Breach tag:  {intercept.breach_tag}")
        print(f"   Safe reply:  {intercept.fallback_message}")

    print("\n" + "═" * 55)
    print("  Done. Add LANGFUSE_* and MLFLOW_TRACKING_URI env vars")
    print("  to enable full observability in production.")
    print("═" * 55 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
