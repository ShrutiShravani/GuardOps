"""
Unit tests for GuardRegistry — manifest loading, schema validation,
programmatic registration, and payload traversal helpers.
"""

import json
import os
import tempfile

import pytest

from guardops.registry import GuardRegistry
from guardops.config import GuardConfig, ConditionType, FallbackStrategy
from guardops.schema import ManifestValidationError


@pytest.fixture(autouse=True)
def clear_registry():
    GuardRegistry.clear()
    yield
    GuardRegistry.clear()


# ─── Programmatic registration ────────────────────────────────────────────────

class TestRegister:
    def test_register_and_retrieve(self):
        rules = [
            GuardConfig(
                metric_key="price",
                condition_type=ConditionType.UNDER_FLOOR,
                boundary_limit=5.0,
                fallback_value=5.0,
                strategy=FallbackStrategy.DATA_OVERRIDE,
                breach_tag="TEST",
            )
        ]
        GuardRegistry.register("MyNode", rules)
        retrieved = GuardRegistry.get_rules_for_node("MyNode")
        assert len(retrieved) == 1
        assert retrieved[0].breach_tag == "TEST"

    def test_unknown_node_returns_empty_list(self):
        result = GuardRegistry.get_rules_for_node("DoesNotExist")
        assert result == []

    def test_clear_wipes_all_rules(self):
        GuardRegistry.register("Node", [
            GuardConfig("x", ConditionType.UNDER_FLOOR, 1.0, 1.0,
                        FallbackStrategy.DATA_OVERRIDE, "T")
        ])
        GuardRegistry.clear()
        assert GuardRegistry.get_rules_for_node("Node") == []


# ─── Manifest loading from file ───────────────────────────────────────────────

class TestLoadManifest:
    def _write_manifest(self, data: dict) -> str:
        f = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        )
        json.dump(data, f)
        f.close()
        return f.name

    def test_load_simple_manifest(self):
        manifest = {
            "PricingAgent": [
                {
                    "metric_key": "price",
                    "condition_type": "UNDER_FLOOR",
                    "boundary_limit": 5.0,
                    "fallback_value": 5.0,
                    "strategy": "DATA_OVERRIDE",
                    "breach_tag": "PRICE_FLOOR",
                }
            ]
        }
        path = self._write_manifest(manifest)
        try:
            GuardRegistry.load_manifest(path)
            rules = GuardRegistry.get_rules_for_node("PricingAgent")
            assert len(rules) == 1
            assert rules[0].condition_type == ConditionType.UNDER_FLOOR
            assert rules[0].boundary_limit == 5.0
        finally:
            os.unlink(path)

    def test_load_multi_check_manifest(self):
        manifest = {
            "VoiceNode": [
                {
                    "metric_key": "output",
                    "strategy": "DATA_OVERRIDE",
                    "checks": [
                        {
                            "condition_type": "CUSTOM_CHECK",
                            "boundary_limit": "custom_guards.check_repeat",
                            "fallback_value": "custom_guards.recover",
                            "breach_tag": "REPEAT",
                        },
                        {
                            "condition_type": "CUSTOM_CHECK",
                            "boundary_limit": "custom_guards.check_context",
                            "fallback_value": "custom_guards.recover_ctx",
                            "breach_tag": "CONTEXT_LOST",
                        },
                    ],
                }
            ]
        }
        path = self._write_manifest(manifest)
        try:
            GuardRegistry.load_manifest(path)
            rules = GuardRegistry.get_rules_for_node("VoiceNode")
            assert len(rules) == 2
            assert rules[0].breach_tag == "REPEAT"
            assert rules[1].breach_tag == "CONTEXT_LOST"
        finally:
            os.unlink(path)

    def test_file_not_found_raises(self):
        with pytest.raises(FileNotFoundError):
            GuardRegistry.load_manifest("/nonexistent/path/manifest.json")

    def test_invalid_strategy_raises_validation_error(self):
        manifest = {
            "Node": [
                {
                    "metric_key": "x",
                    "condition_type": "UNDER_FLOOR",
                    "boundary_limit": 1.0,
                    "fallback_value": 1.0,
                    "strategy": "INVALID_STRATEGY",
                    "breach_tag": "T",
                }
            ]
        }
        path = self._write_manifest(manifest)
        try:
            with pytest.raises(ManifestValidationError, match="strategy"):
                GuardRegistry.load_manifest(path)
        finally:
            os.unlink(path)

    def test_invalid_condition_type_raises_validation_error(self):
        manifest = {
            "Node": [
                {
                    "metric_key": "x",
                    "condition_type": "TYPO_FLOOR",
                    "boundary_limit": 1.0,
                    "fallback_value": 1.0,
                    "strategy": "DATA_OVERRIDE",
                    "breach_tag": "T",
                }
            ]
        }
        path = self._write_manifest(manifest)
        try:
            with pytest.raises(ManifestValidationError, match="condition_type"):
                GuardRegistry.load_manifest(path)
        finally:
            os.unlink(path)

    def test_missing_metric_key_raises(self):
        manifest = {
            "Node": [
                {
                    "condition_type": "UNDER_FLOOR",
                    "boundary_limit": 1.0,
                    "fallback_value": 1.0,
                    "strategy": "DATA_OVERRIDE",
                    "breach_tag": "T",
                }
            ]
        }
        path = self._write_manifest(manifest)
        try:
            with pytest.raises(ManifestValidationError, match="metric_key"):
                GuardRegistry.load_manifest(path)
        finally:
            os.unlink(path)


# ─── Payload traversal helpers ────────────────────────────────────────────────

class TestPayloadTraversal:
    def test_extract_top_level(self):
        payload = {"price": 42.0, "status": "ok"}
        assert GuardRegistry.extract_value_by_path(payload, "price") == 42.0

    def test_extract_nested(self):
        payload = {"features": {"weight_kg": 75.0}}
        assert GuardRegistry.extract_value_by_path(payload, "features.weight_kg") == 75.0

    def test_extract_missing_key_returns_none(self):
        payload = {"price": 10.0}
        assert GuardRegistry.extract_value_by_path(payload, "nonexistent") is None

    def test_extract_missing_nested_returns_none(self):
        payload = {"features": {}}
        assert GuardRegistry.extract_value_by_path(payload, "features.weight_kg") is None

    def test_override_top_level(self):
        payload = {"price": 2.0}
        GuardRegistry.override_value_by_path(payload, "price", 5.0)
        assert payload["price"] == 5.0

    def test_override_nested(self):
        payload = {"features": {"weight_kg": 300.0}}
        GuardRegistry.override_value_by_path(payload, "features.weight_kg", 150.0)
        assert payload["features"]["weight_kg"] == 150.0

    def test_override_creates_missing_intermediate_dicts(self):
        payload = {}
        GuardRegistry.override_value_by_path(payload, "a.b.c", 99)
        assert payload["a"]["b"]["c"] == 99
