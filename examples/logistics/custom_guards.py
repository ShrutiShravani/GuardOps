"""
Logistics-specific custom guards.

These are referenced by string path in examples/logistics/guard_manifest.json.
"""

from typing import Any


def recover_delivery_estimate(value: Any, rule_config: dict) -> str:
    """
    Called when estimated_delivery_days exceeds the ceiling.
    Returns a human-readable message instead of a raw number.
    """
    ceiling = rule_config.get("boundary_limit", 14)
    return (
        f"Delivery estimate of {value} days exceeds the {ceiling}-day SLA window. "
        "A logistics coordinator will contact you to arrange an alternative."
    )
