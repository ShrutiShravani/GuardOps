"""
Logistics Pipeline Example
==========================

A multi-node logistics pipeline with GuardOps intercepting at every
agent boundary.  Shows three different condition types:

  - UNDER_FLOOR         price floor enforcement
  - OVER_CEILING        weight / cost / route limits
  - REGEX_MISMATCH      waybill schema drift detection
  - CUSTOM_CHECK        dynamic delivery SLA recovery (custom_guards.py)

Setup:
    pip install "guardops[telemetry]"   # adds Langfuse + MLflow

    # Optional — add to .env for full observability:
    # LANGFUSE_PUBLIC_KEY=pk-lf-...
    # LANGFUSE_SECRET_KEY=sk-lf-...
    # LANGFUSE_HOST=https://cloud.langfuse.com
    # MLFLOW_TRACKING_URI=sqlite:///mlflow.db

Run:
    cd examples/logistics
    python main.py
"""

import asyncio
import os
import sys

# Allow running from repo root without installing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from guardops import guard_runtime, GuardOpsRefusalIntercept, init_guardops

# Initialise: load THIS example's manifest, not the root one
os.chdir(os.path.dirname(os.path.abspath(__file__)))
init_guardops()


# ─── Agent definitions ────────────────────────────────────────────────────────

@guard_runtime(node_name="CriticAgent")
async def critic_agent(payload: dict) -> dict:
    """
    Evaluates pricing and weight metrics for a shipment cluster.
    GuardOps enforces floor/ceiling/weight limits after this returns.
    """
    print(f"\n  [CriticAgent] Processing shipment {payload.get('payload_id')} …")
    await asyncio.sleep(0.05)
    return payload


@guard_runtime(node_name="RouteOptimizerAgent")
async def route_optimizer(payload: dict) -> dict:
    """Optimises the delivery route for the shipment."""
    print(f"  [RouteOptimizerAgent] Computing route …")
    await asyncio.sleep(0.05)
    return payload


@guard_runtime(node_name="OutputFormatterAgent")
async def output_formatter(payload: dict) -> dict:
    """Formats the final waybill JSON.  GuardOps checks schema compliance."""
    print(f"  [OutputFormatterAgent] Formatting waybill …")
    await asyncio.sleep(0.05)
    return payload


# ─── Pipeline orchestrator ────────────────────────────────────────────────────

async def run_shipment(payload: dict, label: str) -> None:
    print(f"\n{'━' * 55}")
    print(f"  Scenario: {label}")
    print(f"  Payload:  {payload}")
    print(f"{'━' * 55}")

    try:
        result = await critic_agent(payload)
        result = await route_optimizer(result)
        result = await output_formatter(result)
        print(f"\n  ✅  Pipeline complete.")
        print(f"  Final payload: {result}")

    except GuardOpsRefusalIntercept as intercept:
        print(f"\n  🚨  Pipeline halted by GuardOps!")
        print(f"  Breach:  {intercept.breach_tag}")
        print(f"  Message: {intercept.fallback_message}")


# ─── Demo scenarios ───────────────────────────────────────────────────────────

async def main():
    print("\n" + "═" * 55)
    print("  GuardOps — Logistics Pipeline Demo")
    print("═" * 55)

    # Scenario 1: Price under floor → DATA_OVERRIDE fixes it
    await run_shipment(
        {
            "payload_id": "WB-1001-SYD",
            "predicted_base_price": 2.50,       # below $5.00 floor → overridden
            "operational_cost": 120.00,
            "operational_features": {"total_weight_kg": 80.0},
            "estimated_delivery_days": 7,
            "route_distance_km": 1200.0,
            "waybill_json": '{"waybill_id": "WB-1001-SYD", "status": "READY"}',
            "agent_trace": [],
        },
        label="Price under floor (DATA_OVERRIDE)",
    )

    # Scenario 2: Weight over ceiling → DATA_OVERRIDE clamps it
    await run_shipment(
        {
            "payload_id": "WB-1002-MEL",
            "predicted_base_price": 18.00,
            "operational_cost": 200.00,
            "operational_features": {"total_weight_kg": 220.0},  # over 150kg → clamped
            "estimated_delivery_days": 5,
            "route_distance_km": 800.0,
            "waybill_json": '{"waybill_id": "WB-1002-MEL", "status": "READY"}',
            "agent_trace": [],
        },
        label="Weight over ceiling (DATA_OVERRIDE)",
    )

    # Scenario 3: Delivery SLA exceeded → custom recovery message
    await run_shipment(
        {
            "payload_id": "WB-1003-BNE",
            "predicted_base_price": 22.00,
            "operational_cost": 180.00,
            "operational_features": {"total_weight_kg": 60.0},
            "estimated_delivery_days": 21,      # over 14-day SLA → custom recovery
            "route_distance_km": 1800.0,
            "waybill_json": '{"waybill_id": "WB-1003-BNE", "status": "READY"}',
            "agent_trace": [],
        },
        label="Delivery SLA exceeded (custom recovery)",
    )

    # Scenario 4: Cost over ceiling → SHORT_CIRCUIT halts pipeline
    await run_shipment(
        {
            "payload_id": "WB-1004-PER",
            "predicted_base_price": 35.00,
            "operational_cost": 750.00,         # over $500 ceiling → SHORT_CIRCUIT
            "operational_features": {"total_weight_kg": 90.0},
            "estimated_delivery_days": 9,
            "route_distance_km": 4200.0,
            "waybill_json": '{"waybill_id": "WB-1004-PER", "status": "READY"}',
            "agent_trace": [],
        },
        label="Cost over ceiling (SHORT_CIRCUIT)",
    )

    # Scenario 5: Waybill schema drift → DATA_OVERRIDE with fallback JSON
    await run_shipment(
        {
            "payload_id": "WB-1005-ADL",
            "predicted_base_price": 15.00,
            "operational_cost": 95.00,
            "operational_features": {"total_weight_kg": 45.0},
            "estimated_delivery_days": 4,
            "route_distance_km": 600.0,
            "waybill_json": "malformed output from LLM provider",   # schema drift
            "agent_trace": [],
        },
        label="Waybill schema drift (REGEX_MISMATCH)",
    )

    print("\n" + "═" * 55)
    print("  All scenarios complete.")
    print("═" * 55 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
