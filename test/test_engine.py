"""
Unit tests for GuardExecutionEngine.

These tests run with zero external services (no Langfuse, no MLflow,
no OpenAI) by registering rules programmatically.
"""

import pytest
from guardops.engine import GuardExecutionEngine, GuardOpsRefusalIntercept
from guardops.registry import GuardRegistry
from guardops.config import GuardConfig, ConditionType, FallbackStrategy


# ─── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def clear_registry():
    """Wipe the registry before each test so tests are isolated."""
    GuardRegistry.clear()
    yield
    GuardRegistry.clear()


def make_rule(**overrides) -> GuardConfig:
    defaults = dict(
        metric_key="price",
        condition_type=ConditionType.UNDER_FLOOR,
        boundary_limit=5.0,
        fallback_value=5.0,
        strategy=FallbackStrategy.DATA_OVERRIDE,
        breach_tag="PRICE_UNDER_FLOOR",
    )
    defaults.update(overrides)
    return GuardConfig(**defaults)


# ─── UNDER_FLOOR ──────────────────────────────────────────────────────────────

class TestUnderFloor:
    def test_breach_triggers_override(self):
        GuardRegistry.register("Node", [make_rule(boundary_limit=5.0, fallback_value=5.0)])
        payload = {"price": 2.0}
        result = GuardExecutionEngine.evaluate_node_rules("Node", payload)
        assert result["payload"]["price"] == 5.0
        assert len(result["interventions"]) == 1
        assert result["interventions"][0]["breach_tag"] == "PRICE_UNDER_FLOOR"

    def test_no_breach_when_at_floor(self):
        GuardRegistry.register("Node", [make_rule(boundary_limit=5.0)])
        payload = {"price": 5.0}
        result = GuardExecutionEngine.evaluate_node_rules("Node", payload)
        assert result["payload"]["price"] == 5.0
        assert result["interventions"] == []

    def test_no_breach_when_above_floor(self):
        GuardRegistry.register("Node", [make_rule(boundary_limit=5.0)])
        payload = {"price": 10.0}
        result = GuardExecutionEngine.evaluate_node_rules("Node", payload)
        assert result["interventions"] == []


# ─── OVER_CEILING ─────────────────────────────────────────────────────────────

class TestOverCeiling:
    def test_breach_triggers_override(self):
        rule = make_rule(
            condition_type=ConditionType.OVER_CEILING,
            boundary_limit=100.0,
            fallback_value=100.0,
            breach_tag="COST_OVER_CEILING",
        )
        GuardRegistry.register("Node", [rule])
        payload = {"price": 250.0}
        result = GuardExecutionEngine.evaluate_node_rules("Node", payload)
        assert result["payload"]["price"] == 100.0
        assert result["interventions"][0]["breach_tag"] == "COST_OVER_CEILING"

    def test_short_circuit_on_breach(self):
        rule = make_rule(
            condition_type=ConditionType.OVER_CEILING,
            boundary_limit=100.0,
            fallback_value="Budget exceeded.",
            strategy=FallbackStrategy.SHORT_CIRCUIT,
            breach_tag="HARD_LIMIT",
        )
        GuardRegistry.register("Node", [rule])
        with pytest.raises(GuardOpsRefusalIntercept) as exc_info:
            GuardExecutionEngine.evaluate_node_rules("Node", {"price": 500.0})
        assert exc_info.value.breach_tag == "HARD_LIMIT"
        assert "Budget exceeded." in exc_info.value.fallback_message

    def test_no_breach_at_ceiling(self):
        rule = make_rule(condition_type=ConditionType.OVER_CEILING, boundary_limit=100.0)
        GuardRegistry.register("Node", [rule])
        result = GuardExecutionEngine.evaluate_node_rules("Node", {"price": 100.0})
        assert result["interventions"] == []


# ─── REGEX_MISMATCH ───────────────────────────────────────────────────────────

class TestRegexMismatch:
    def test_breach_on_mismatch(self):
        rule = GuardConfig(
            metric_key="output",
            condition_type=ConditionType.REGEX_MISMATCH,
            boundary_limit=r"^\{.*\}$",
            fallback_value='{"status": "fallback"}',
            strategy=FallbackStrategy.DATA_OVERRIDE,
            breach_tag="SCHEMA_DRIFT",
        )
        GuardRegistry.register("Node", [rule])
        payload = {"output": "plain text, not JSON"}
        result = GuardExecutionEngine.evaluate_node_rules("Node", payload)
        assert result["payload"]["output"] == '{"status": "fallback"}'
        assert result["interventions"][0]["breach_tag"] == "SCHEMA_DRIFT"

    def test_no_breach_on_match(self):
        rule = GuardConfig(
            metric_key="output",
            condition_type=ConditionType.REGEX_MISMATCH,
            boundary_limit=r"^\{.*\}$",
            fallback_value='{"status": "fallback"}',
            strategy=FallbackStrategy.DATA_OVERRIDE,
            breach_tag="SCHEMA_DRIFT",
        )
        GuardRegistry.register("Node", [rule])
        payload = {"output": '{"waybill_id": "WB-1234-ABC"}'}
        result = GuardExecutionEngine.evaluate_node_rules("Node", payload)
        assert result["interventions"] == []


# ─── Dot-notation key paths ───────────────────────────────────────────────────

class TestNestedKeyPath:
    def test_nested_key_override(self):
        rule = GuardConfig(
            metric_key="features.weight_kg",
            condition_type=ConditionType.OVER_CEILING,
            boundary_limit=150.0,
            fallback_value=150.0,
            strategy=FallbackStrategy.DATA_OVERRIDE,
            breach_tag="WEIGHT_EXCEEDED",
        )
        GuardRegistry.register("Node", [rule])
        payload = {"features": {"weight_kg": 300.0}}
        result = GuardExecutionEngine.evaluate_node_rules("Node", payload)
        assert result["payload"]["features"]["weight_kg"] == 150.0

    def test_missing_key_skipped_gracefully(self):
        GuardRegistry.register("Node", [make_rule(metric_key="nonexistent.key")])
        payload = {"price": 2.0}
        # Should not raise, should not add intervention
        result = GuardExecutionEngine.evaluate_node_rules("Node", payload)
        assert result["interventions"] == []


# ─── Multiple rules on same node ──────────────────────────────────────────────

class TestMultipleRules:
    def test_all_matching_rules_fire(self):
        rules = [
            make_rule(metric_key="price", boundary_limit=5.0, fallback_value=5.0,
                      breach_tag="PRICE_FLOOR"),
            GuardConfig(
                metric_key="cost",
                condition_type=ConditionType.OVER_CEILING,
                boundary_limit=100.0,
                fallback_value=100.0,
                strategy=FallbackStrategy.DATA_OVERRIDE,
                breach_tag="COST_CEILING",
            ),
        ]
        GuardRegistry.register("Node", rules)
        payload = {"price": 1.0, "cost": 999.0}
        result = GuardExecutionEngine.evaluate_node_rules("Node", payload)
        assert result["payload"]["price"] == 5.0
        assert result["payload"]["cost"] == 100.0
        assert len(result["interventions"]) == 2

    def test_short_circuit_stops_remaining_rules(self):
        rules = [
            GuardConfig(
                metric_key="cost",
                condition_type=ConditionType.OVER_CEILING,
                boundary_limit=100.0,
                fallback_value="Blocked",
                strategy=FallbackStrategy.SHORT_CIRCUIT,
                breach_tag="COST_HARD_LIMIT",
            ),
            make_rule(metric_key="price", boundary_limit=5.0, fallback_value=5.0),
        ]
        GuardRegistry.register("Node", rules)
        payload = {"price": 1.0, "cost": 999.0}
        with pytest.raises(GuardOpsRefusalIntercept) as exc_info:
            GuardExecutionEngine.evaluate_node_rules("Node", payload)
        assert exc_info.value.breach_tag == "COST_HARD_LIMIT"


# ─── Node with no rules ───────────────────────────────────────────────────────

class TestNoRules:
    def test_node_with_no_rules_passes_through(self):
        # Don't register any rules for "UnknownNode"
        payload = {"price": 1.0}
        result = GuardExecutionEngine.evaluate_node_rules("UnknownNode", payload)
        assert result["payload"] == payload
        assert result["interventions"] == []


# ─── Pydantic support ─────────────────────────────────────────────────────────

class TestPydanticSupport:
    def test_pydantic_model_override(self):
        try:
            from pydantic import BaseModel  # type: ignore
        except ImportError:
            pytest.skip("pydantic not installed")

        class Shipment(BaseModel):
            price: float
            cost: float

        GuardRegistry.register("Node", [
            make_rule(metric_key="price", boundary_limit=5.0, fallback_value=5.0)
        ])
        payload = Shipment(price=2.0, cost=100.0)
        result = GuardExecutionEngine.evaluate_node_rules("Node", payload)
        final = result["payload"]
        assert isinstance(final, Shipment)
        assert final.price == 5.0
        assert final.cost == 100.0
