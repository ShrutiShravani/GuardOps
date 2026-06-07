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
from guardops_sdk.guardop.init import init_guardops


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
            init_guardops()
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

            parent_trace_id= GuardTelemetry.get_active_trace()
            client= GuardTelemetry.get_global_client()


            raw_input_snapshot = copy.deepcopy(payload)
            original_payload = {k: v for k, v in raw_input_snapshot.items() if k not in ["tenant_id", "mlflow_run_id"]}
            waybill_id=payload.get("payload_id","UNKNOWN")
            

            run_id= payload.get("mlflow_run_id")
            mlflow_client= MlflowClient() if run_id else None
            clean_input_snapshot = {
                k: v for k, v in raw_input_snapshot.items() 
                if k not in ["tenant_id", "mlflow_run_id", "agent_trace"]
            }
            
            
    
            try:
                # 1. Run the agent's calculations
                if inspect.iscoroutinefunction(func):
                    result_payload = await func(*args, **kwargs)
                else:
                    result_payload = func(*args, **kwargs)
                raw_agent_output = copy.deepcopy(result_payload)

                #active_rules = GuardRegistry.get_rules_for_node(node_name)
               # print(f"[DEBUG]Node Name: {node_name} | Total Rules Found: {len(active_rules)}")
              

                # 2. Run through verification rules engine
                engine_result = GuardExecutionEngine.evaluate_node_rules(
                    node_name,
                    result_payload
                )

                safeguarded_payload = engine_result["payload"]
                interventions = engine_result["interventions"]
    

                 # ─── MLFLOW TRACKING FOR CASE A: DATA_OVERRIDE ───
                triggered_overrides={}


                for intervention in interventions:

                    breach_tag = intervention["breach_tag"]
                    if mlflow_client and run_id:
                     mlflow_client.log_metric(
                        run_id,
                        f"override_triggered_{node_name}",
                        1.0
                    )

                     mlflow_client.log_param(
                            run_id,
                            f"{node_name}_{breach_tag}",
                            "DATA_OVERRIDE_TRIGGERED"
                        )

                    clean_log = {
                    "node_name": node_name,
                    "intervention_type": "DATA_OVERRIDE",
                    "applied_override": intervention,
                    "sanitized_payload": {
                        k: v
                        for k, v in safeguarded_payload.items()
                        if k not in ["tenant_id", "mlflow_run_id"]
                    }
                }
                                
        
                            
                    # Export the exact breached payload to a local folder to log as an MLflow retraining artifact
                    artifact_path = f"mlflow_retrain_data/{node_name}_{breach_tag}_{waybill_id}.json"
                    os.makedirs("mlflow_retrain_data", exist_ok=True)
                    with open(artifact_path, "w") as f:
                        json.dump({"breached_input": clean_input_snapshot, "applied_output": clean_log}, f, indent=2)
                    
                    # Log the file as an artifact inside MLflow so data scientists can access it for training
                    mlflow_client.log_artifact(run_id,artifact_path, artifact_path="breached_retraining_payloads")
                 

               
                    if parent_trace_id and client:
                        with client.start_as_current_observation(
                            name=f"NodeIntervention:{node_name}",
                            as_type="span",
                            input=clean_input_snapshot
                        ):

                            client.update_current_span(
                                input=clean_input_snapshot,
                                output=clean_log,
                                metadata={
                                    "shield_intervention_logged": True,
                                    "intervention_type": "DATA_OVERRIDE",
                                    "breach_tag": breach_tag
                                }
                            )

                      
                    
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
                        json.dump({"breached_input": clean_input_snapshot, "applied_output": clean_sc_payload}, f, indent=2)
                    
                    # Log the file as an artifact inside MLflow so data scientists can access it for training
                    mlflow_client.log_artifact(run_id,artifact_path, artifact_path="breached_retraining_payloads")

        
                payload["status"] = "BLOCKED_BY_GUARDOP_POLICY"
                payload["final_error_message"] = intercept.fallback_message
                payload["is_verified"] = False

                if "agent_trace" in payload and isinstance(payload["agent_trace"],list):
                    payload["agent_trace"].append(f"[POLICY INTERCEPT] Node '{node_name}': {intercept.breach_tag}")
                

                if parent_trace_id and client:
                    with client.start_as_current_observation(
                        name=f"NodeShortCircuit:{node_name}",
                        as_type="span",
                        input=clean_input_snapshot
                    ) as live_span:
                        client.update_current_span(
                                input=clean_input_snapshot, 
                                output={"status": "INTERCEPTED", "reason": intercept.breach_tag}
                            )
                
                raise intercept
             
        return async_wrapper  
    return decorator
                    
        


