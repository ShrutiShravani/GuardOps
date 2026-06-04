import re
from typing import Dict,Any,List
from guardops_sdk.guardop.config import GuardConfig,ConditionType,FallbackStrategy
from guardops_sdk.guardop.registry import GuardRegistry
import os
import sys
import importlib

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

    @staticmethod
    def resolve_function(func_path:str)->callable:
        """
        Dynamically imports and maps string paths to live executable code blocks.
        Transforms 'custom_guards.check_persona_bleed' into a live functional call.
        """
        try:
            current_working_dir= os.getcwd()

            if current_working_dir not in sys.path:
                sys.path.insert(0,current_working_dir)
            
            module_name,func_name= func_path.rsplit(".",1)
            mod =  importlib.import_module(module_name)
            return getattr(mod,func_name)
        except (ValueError,ImportError,AttributeError) as e:
            raise RuntimeError(f"[Refelction ERROR] Failed to resolve function a path '{func_path}':{e}")


    @classmethod
    def evaluate_node_rules(cls,node_name: str, payload: Dict[str, Any]) -> Dict[str, Any]:
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
            
            #prepare a clean dictionary for custom functions transforming enums to readable strings
            rule_serializable_config={
                 "metric_key": rule.metric_key,
            "condition_type": rule.condition_type.value,  
            "boundary_limit": rule.boundary_limit,
            "fallback_value": rule.fallback_value,
            "strategy": rule.strategy.value,             
            "breach_tag": rule.breach_tag,
            "metadata": getattr(rule, "metadata", {})
            }

            # if specific key is not rpesent in this transaction step,skip safely
            if current_value is None:
                continue

            # Run mathematical and validation pattern checks
            if cls._check_condition(current_value, rule.condition_type,rule_serializable_config):

                print(f"[GUARD ENGINE] Breach detected on node '{node_name}' under tag :{rule.breach_tag}")
                
                raw_fallback = rule.fallback_value
                if isinstance(raw_fallback,str) and "." in raw_fallback:
                    try:
                        fallback_generator= GuardExecutionEngine.resolve_function(raw_fallback)
                        resolved_fallback_message=fallback_generator(current_value,rule_serializable_config)
                    except Exception as fallback_err:
                        print(f"[GUARD ERROR] Dynamic fallback function execution failed: {fallback_err}")
                else:
                    resolved_fallback_message = raw_fallback 

                # ─── CASE A: LOCAL NODE OVERRIDE (Fix-and-Continue) ───
                if rule.strategy == FallbackStrategy.DATA_OVERRIDE:
                    # Uses our write pathtool to update the dictionary in memory
                    GuardRegistry.override_value_by_path(payload, rule.metric_key,resolved_fallback_message)
                    cls._append_trace(payload, f"[Local Fix] Field '{rule.metric_key}' overrode to safe default.")
                
                # ─── CASE B: PIPELINE INTERCEPT (Stop-and-Refuse) ───
                if rule.strategy == FallbackStrategy.SHORT_CIRCUIT:
                    # Instantly raises an exception to bypass all downstream agent execution nodes
                    raise GuardOpsRefusalIntercept(
                        fallback_message=str(resolved_fallback_message),
                        breach_tag=rule.breach_tag
                    )
                
            else:
                resolved_fallback_message="No fallback value provided"       
        return payload


    @staticmethod
    def _check_condition(value: Any, condition_type: ConditionType,rule_serializable_config) -> bool:
        """Evaluates thresholds against active application values."""
        try:
            if condition_type == ConditionType.OVER_CEILING:
                return float(value) > float(rule_serializable_config["boundary_limit"])
            elif condition_type == ConditionType.UNDER_FLOOR:
                return float(value) < float(rule_serializable_config["boundary_limit"])
            elif condition_type == ConditionType.REGEX_MISMATCH:
                return not bool(re.match(str(rule_serializable_config["boundary_limit"]), str(value)))
            elif condition_type == ConditionType.CUSTOM_CHECK:
                eval_path = rule_serializable_config.get("boundary_limit")

                if eval_path and "." in eval_path:
                    custom_evaluator_func= GuardExecutionEngine.resolve_function(eval_path)

                    print(f"[GUARD ENGINE] Dynamic Reflection Triggered -> Executing: {eval_path}()")
                    
                    return bool(custom_evaluator_func(value,rule_serializable_config))

                print("[GUARD WARNING] SEMANTIC_BEHAVIORAL_VIOLATION rule found but no valid 'evaluator_type' path provided.")
                return False
             
            else:
                # Catch-all: If user introduces an unknown type, block execution for explicit safety
                print(f"[GUARD CRITICAL] Unsupported condition type '{condition_type}' detected. Forcing intercept.")
                return True

        except (ValueError, TypeError) as e:
            print(f"[GUARD EXCEPTION] error evaluating condition engine:{e}")
            return True 
        return False


    @staticmethod
    def _append_trace(payload: Dict[str, Any], message: str) -> None:
        """Appends audit events directly into the payload history tracker."""
        if "agent_trace" in payload and isinstance(payload["agent_trace"], list):
            payload["agent_trace"].append(message)