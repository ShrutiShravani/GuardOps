import re
from typing import Dict,Any,List
from guardops_sdk.guardop.config import GuardConfig,ConditionType,FallbackStrategy
from guardops_sdk.guardop.registry import GuardRegistry

class GuardOpsRefusalIntercept(Exception):
    """
    Case B Exception:Pipeline Intercept.
    Raised when a safety policy requries stopping the entire agent network
    instantly to return a safe, direct message to the user.
    """
    def __init__(self,fallback_message:str,breach_tag:str):
        self.fallback_message=fallback_message
        self.breach_tag= breach_tag
        super().__init__(f"[GuardOps Intercept] Execution halted by policy rule:{breach_tag} {fallback_message}")

class GuardExecutionEngine:
    """
    The stateless automation engine. It evaluates in-flight dictionary data
    against the cached rules loaded from the user's manifest file.
    """
    @classmethod
    def evaluate_node_rules(cls, node_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Processes an in-flight dictionary payload for a targeted agent node.
        
        1. Asks the GuardRegistry to get compiled rules for this node.
        2. Reads the deep metrics using extract_value_by_path.
        3. Executes the specified fallback strategy if a boundary is breached.
        """

        #get the rules of node from registry

        active_rules:List[GuardConfig]=GuardRegistry.get_rules_for_node(node_name)
        print(f"\n==========================================")
        print(f"[GUARD RUNTIME] Checking Node: '{node_name}'")
        
        for rule in active_rules:
            current_value= GuardRegistry.extract_value_by_path(payload,rule.metric_key)
            if current_value is None:
                print(f"ℹ[GUARD ENGINE] Skipping rule '{rule.breach_tag}': Key '{rule.metric_key}' not present in this payload.")
                continue
            print(f"[DEBUG] Rule: {type(rule.metric_key)}{rule.metric_key} | Extracted: {current_value} (Type: {type(current_value)}) | Limit: {type(rule.boundary_limit)} {rule.boundary_limit}")
            print(f"Target Rule Metric Key: '{rule.metric_key}'")
            print(f"Expected Condition: {rule.condition_type} | Boundary: {rule.boundary_limit} (Type: {type(rule.boundary_limit)})")

            # if specific key is not rpesent in this transaction step,skip safely
            if current_value is None:
                continue

            #run mathematical and validation pattern checks

            # Run mathematical and validation pattern checks
            if cls._check_condition(current_value, rule.condition_type, rule.boundary_limit):
                
                # ─── CASE A: LOCAL NODE OVERRIDE (Fix-and-Continue) ───
                if rule.strategy == FallbackStrategy.DATA_OVERRIDE:
                    # Uses our write pathtool to update the dictionary in memory
                    GuardRegistry.override_value_by_path(payload, rule.metric_key, rule.fallback_value)
                    cls._append_trace(payload, f"[Local Fix] Field '{rule.metric_key}' overrode to safe default.")
                
                # ─── CASE B: PIPELINE INTERCEPT (Stop-and-Refuse) ───
                elif rule.strategy == FallbackStrategy.SHORT_CIRCUIT:
                    # Instantly raises an exception to bypass all downstream agent execution nodes
                    raise GuardOpsRefusalIntercept(
                        fallback_message=str(rule.fallback_value),
                        breach_tag=rule.breach_tag
                    )
                    
        return payload

    @staticmethod
    def _check_condition(value: Any, condition_type: ConditionType, boundary: Any) -> bool:
        """Evaluates thresholds against active application values."""
        try:
            if condition_type == ConditionType.OVER_CEILING:
                return float(value) > float(boundary)
            elif condition_type == ConditionType.UNDER_FLOOR:
                return float(value) < float(boundary)
            elif condition_type == ConditionType.REGEX_MISMATCH:
                return not bool(re.match(str(boundary), str(value)))
        except (ValueError, TypeError):
            # Fail-closed policy: treat malformed data as a data threat breach
            return True 
        return False

    @staticmethod
    def _append_trace(payload: Dict[str, Any], message: str) -> None:
        """Appends audit events directly into the payload history tracker."""
        if "agent_trace" in payload and isinstance(payload["agent_trace"], list):
            payload["agent_trace"].append(message)