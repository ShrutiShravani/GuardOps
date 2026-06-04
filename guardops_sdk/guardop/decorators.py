import functools
import inspect
import time
import json
import os
from typing import Dict, Any, Callable
from guardops_sdk.guardop.engine import GuardExecutionEngine, GuardOpsRefusalIntercept
from guardops_sdk.guardop.telemetry import GuardTelemetry
from guardops_sdk.guardop.registry import GuardRegistry 
import mlflow
from mlflow.tracking import MlflowClient 
import copy 



def guard_runtime(node_name:str):
    """
    Unified Langfuse v4 + MLflow Multi-Agent Orchestrator Decorator.
    - Isolates execution streams via ContextVars.
    - Profiles individual node processing deltas.
    - Logs live system override differences and scores directly to Langfuse.
    - Emits metrics and saves corrupted payloads to MLflow for regression tracking.
    """

    def decorator(func:Callable):
        @functools.wraps(func)
        async def async_wrapper(*args,**kwargs):
            payload:Dict[str,Any]=None

            for arg in args:
                if isinstance(arg,dict):
                    payload=arg
                    break
            if not payload:
                for key,val in kwargs.items():
                    if isinstance(val,dict):
                        payload=val
                        break
            
            if payload is None:
                return await func(*args,**kwargs)
            
            start_time= time.monotonic()
            parent_trace_id= GuardTelemetry.get_active_trace()
            client= GuardTelemetry.get_global_client()

            native_trace_id=None 
            if parent_trace_id:
                if isinstance(parent_trace_id,str):
                    native_trace_id= parent_trace_id
                else:
                    native_trace_id= getattr(parent_trace_id,'trace_id',None) or getattr(parent_trace_id,'id',None)

            ctx_manager=None
            raw_input_snapshot = copy.deepcopy(payload)
            original_payload = {k: v for k, v in raw_input_snapshot.items() if k not in ["tenant_id", "mlflow_run_id"]}
            waybill_id=payload.get("payload_id","UNKNOWN")
            
            client= GuardTelemetry.get_global_client()

            run_id= payload.get("mlflow_run_id")
            mlflow_client= MlflowClient() if run_id else None
            
            if parent_trace_id:
                ctx_manager = client.start_as_current_observation(
                    name=f"NodeExecution:{node_name}",
                    as_type="span",
                    input= raw_input_snapshot
                )
                ctx_manager.__enter__()

            try:
                # 1. Run the agent's calculations
                if inspect.iscoroutinefunction(func):
                    result_payload = await func(*args, **kwargs)
                else:
                    result_payload = func(*args, **kwargs)
                raw_agent_output = copy.deepcopy(result_payload)

                active_rules = GuardRegistry.get_rules_for_node(node_name)
                pre_eval_states = {
                    rule.metric_key: GuardRegistry.extract_value_by_path(result_payload, rule.metric_key)
                    for rule in active_rules
                }

                # 2. Run through verification rules engine
                safeguarded_payload = GuardExecutionEngine.evaluate_node_rules(node_name, result_payload)
                print(f"[DEBUG]Node Name: {node_name} | Total Rules Found: {len(active_rules)}")
                duration = time.monotonic() - start_time


                 # ─── MLFLOW TRACKING FOR CASE A: DATA_OVERRIDE ───
                triggered_overrides={}

                for rule in active_rules:
                    pre_val = pre_eval_states[rule.metric_key]
                    post_val = GuardRegistry.extract_value_by_path(safeguarded_payload, rule.metric_key)
                    
                    if pre_val is not None and pre_val!=post_val:
                        triggered_overrides[rule.metric_key]={
                            "original_value":pre_val,
                            "safe_fallback_value":post_val,
                            "policy_rule_tag": rule.breach_tag
                        }

                        if mlflow_client and run_id:
                            # Log real-time parameter shifting to MLflow dashboard
                            mlflow_client.log_metric(run_id,f"override_triggered_{node_name}", 1.0)
                            mlflow_client.log_param(run_id,f"{node_name}_{rule.metric_key}_breached_metric_key","DATA_OVERRIDE_TRIGGERED")
                            #mlflow_client.log_param(run_id,f"{node_name}_{rule.metric_key}_original_untrusted_value", (pre_val))
                           # mlflow_client.log_param(run_id,f"{node_name}_{rule.metric_key}_replaced_safe_value", (post_val))
                
                if triggered_overrides and mlflow_client and run_id:
                    clean_log={
                        "node_name": node_name,
                        "intervention_type": "DATA_OVERRIDE",
                        "applied_overrides": triggered_overrides,
                        "sanitized_payload": {
                            k: v for k, v in safeguarded_payload.items() 
                            if k not in ["tenant_id", "mlflow_run_id"]
                        }
                    }

                            
                    # Export the exact breached payload to a local folder to log as an MLflow retraining artifact
                    artifact_path = f"mlflow_retrain_data/{node_name}_override_{waybill_id}.json"
                    os.makedirs("mlflow_retrain_data", exist_ok=True)
                    with open(artifact_path, "w") as f:
                        json.dump({"breached_input": original_payload, "applied_output": clean_log}, f, indent=2)
                    
                    # Log the file as an artifact inside MLflow so data scientists can access it for training
                    mlflow_client.log_artifact(run_id,artifact_path, artifact_path="breached_retraining_payloads")
                 

                if ctx_manager:
                    client.update_current_span(
                        input=raw_input_snapshot,
                        output= safeguarded_payload,
                        metadata={"shield_intervention_logged":bool(triggered_overrides),"intervention_type": "DATA_OVERRIDE" if triggered_overrides else "CLEAN_EXECUTION","applied_mutations":triggered_overrides}
                    )
                    
                    if triggered_overrides and native_trace_id:
                        
                        GuardTelemetry.log_score(
                            score_name="Data_Override",
                            score_value=1.0,
                            comment=f"Node '{node_name}'Corrected fields: {list(triggered_overrides.keys())}"
                        )
                        print("scores_logged")
                      
                    
                return safeguarded_payload
            
            except GuardOpsRefusalIntercept as intercept:
                if mlflow_client and run_id:
                    mlflow_client.log_metric(run_id, f"critical_policy_violation_{node_name}", 1.0)
                    
                    
                    target_error_state= raw_agent_output if 'raw_agent_output' in locals() else raw_input_snapshot

                    clean_sc_payload={
                        "node_name": node_name,
                        "intervention_type": "SHORT_CIRCUIT",
                        "breach_tag": intercept.breach_tag,
                        "fallback_message": intercept.fallback_message,
                        "halted_at_state": {
                            k: v for k, v in target_error_state.items() 
                            if k not in ["tenant_id", "mlflow_run_id"]
                        }

                    }
                    artifact_path = f"mlflow_retrain_data/{node_name}_override_{waybill_id}.json"
                    os.makedirs("mlflow_retrain_data", exist_ok=True)
                    with open(artifact_path, "w") as f:
                        json.dump({"breached_input": original_payload, "applied_output": clean_sc_payload}, f, indent=2)
                    
                    # Log the file as an artifact inside MLflow so data scientists can access it for training
                    mlflow_client.log_artifact(run_id,artifact_path, artifact_path="breached_retraining_payloads")

        
                payload["status"] = "BLOCKED_BY_GUARDOP_POLICY"
                payload["final_error_message"] = intercept.fallback_message
                payload["is_verified"] = False

                if "agent_trace" in payload and isinstance(payload["agent_trace"],list):
                    payload["agent_trace"].append(f"[POLICY INTERCEPT] Node '{node_name}': {intercept.breach_tag}")

                if ctx_manager:
                    client.update_current_span(input=raw_input_snapshot,output={"status": "INTERCEPTED", "reason": intercept.breach_tag})
                 
                    
                    GuardTelemetry.log_score(score_name="Short_Circuit", score_value=1.0, comment=f"Halted at node '{node_name}' via rule tag: {intercept.breach_tag}")
                
                return payload
            
            finally:
                if ctx_manager:
                    ctx_manager.__exit__(None,None,None)
        return async_wrapper
    return decorator
        


