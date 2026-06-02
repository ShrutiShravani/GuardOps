from dotenv import load_dotenv
load_dotenv()
import asyncio
from modulefinder import test
import uuid
from guardops_sdk.guardop.telemetry import GuardTelemetry
from guardops_sdk.guardop.decorators import guard_runtime
import mlflow
from mlflow.tracking import MlflowClient
import os

DB_URI= os.getenv("DB_URI")
MLFLOW_TRACKING_URI = os.getenv("MLFLOW_TRACKING_URI")
client = MlflowClient()
#print("MLFLOW_TRACKING_URI =", MLFLOW_TRACKING_URI)

mlflow.set_tracking_uri(MLFLOW_TRACKING_URI)


@guard_runtime(node_name="CriticAgent")
async def execute_critic_agent(payload:dict)->dict:
    """
    Universal Agent Node Middleware execution block.
    """
    await asyncio.sleep(0.1)
    return payload

@guard_runtime(node_name="LLM_Output_Generation_Node")
async def execute_llm_generation(payload:dict)->dict:
    print("   [NODE EXECUTION] LLM_Output_Generation_Node evaluating rules...")
    await asyncio.sleep(0.05)
    return payload

@guard_runtime(node_name="Voice_Generation_Node")
async def execute_voice_generation(payload:dict)->dict:
    print("   [NODE EXECUTION] Voice_Generation_Node validating persona...")
    await asyncio.sleep(0.05)
    return payload

async def worker_conductor(payload_id:str,tenant_id:str,simulated_data:dict):
    """
    Universal Worker Conductor: Runs on an isolated, thread-safe memory context.
    Spawns the Langfuse parent trace session and drives the payload stream.
    """
    client=MlflowClient()
    experiment_name = "GuardOps_Universal_Shield_Analytics"
    exp=mlflow.get_experiment_by_name(experiment_name)
    if not exp:
        exp_id= mlflow.create_experiment(experiment_name)
    else:
        exp_id= exp.experiment_id

    run= client.create_run(
        experiment_id= exp_id,
        tags= {"mlflow.runName": f"ExecutionGraph_{payload_id}"}
    )
    
    run_id = run.info.run_id

    GuardTelemetry.start_trace_session(trace_name=f"UniversalPipeline_{payload_id}",
        user_id=tenant_id,
        tags=["Production-Runtime-Shield", "Architecture-v1"])
    
    # 2. Build a completely abstract, universal payload structure
   
    payload = {
        "payload_id": payload_id,
        "tenant_id": tenant_id,
        "mlflow_run_id": run_id,  #
        "status": "PROCESSING",
        "agent_trace": [],
        **simulated_data  # <─── Unpacks any dynamic dictionary keys right into the payload!
    }

    print(f"Worker starting job for {payload_id}")
    try:
    
        client.log_param(run_id,"tenant_owner", tenant_id)

        #fire paylad to guard runtime
        payload = await execute_critic_agent(payload)
        if payload.get("status")=="BLOCKED_BY_GUARDOP_POLICY":
            print(f"[BYPASS TRIGGERED] Short-Circuit at CriticAgent. Halting execution pipeline.")
            client.set_terminated(run_id, status="KILLED")
            payload= sanitize_payload(payload)
            return payload

        payload= await execute_llm_generation(payload)
        if payload.get("status")=="BLOCKED_BY_GUARDOP_POLICY":
            print(f"[BYPASS TRIGGERED] Short-Circuit at LLM Generation Node. Halting execution pipeline.")
            client.set_terminated(run_id, status="KILLED")
            payload= sanitize_payload(payload)
            return payload
        
        payload= await execute_voice_generation(payload)
        if payload.get("status")=="BLOCKED_BY_GUARDOP_POLICY":
            print(f"[BYPASS TRIGGERED] Short-Circuit at Voice Generation Node. Halting execution pipeline.")
            client.set_terminated(run_id, status="KILLED")
            payload= sanitize_payload(payload)
            return payload

        payload["status"]="COMPLETED_SUCCESSFULLY"
        print(f"Worker complete for {payload_id} -> Safety Status: {payload.get('status')}")
    

        client.set_terminated(run_id,status="FINISHED")
        print(f"Pipeline Execution Graph {payload_id} complete.")
        return sanitize_payload(payload)
    except Exception as e:
        client.set_terminated(run_id,status="FAILED")
        print(f"Pipeline Execution Graph {payload_id} failed: {e}")
        if payload and isinstance(payload,dict):
            payload= sanitize_payload(payload)
            return payload
        
        return {"status":"FAILED","error":str(e),"payload_id": payload_id}
        
        
def sanitize_payload(payload:dict)->dict:
    """
    Strips out all internal AgentOps/MLOps infrastructure keys 
    before sending the payload back to the client interface.
    """
    if not isinstance(payload,dict):
        return payload

    infrastructure_keys={"mlflow_run_id","agent_trace","tenant_id"}

    return {k:v for k,v in payload.items() if k not in infrastructure_keys}


async def main_entry():
    """
    Simulates 4 distinct multi-tenant requests hitting the universal framework 
    concurrently at the exact same millisecond.
    """

    tasks=[
        worker_conductor(
            payload_id="JOB-001-CLEAN", 
            tenant_id="Logistics_Corp_A", 
            simulated_data={
                "predicted_base_price": 25.00,               
                "operational_cost": 120.00,                  
                "operational_features": {"total_weight_kg": 45.0}, 
                "llm_generation": {
                    "text_output": '{"waybill_id": "WB-2026-NYC", "status": "VERIFIED"}' 
                }
            }
        ),
        
        # ────────────────────────────────────────────────────────
        # JOB 2: THE DATA_OVERRIDE TEST (Sequentially hits corrections in Node 1 AND Node 2)
        # ────────────────────────────────────────────────────────
        worker_conductor(
            payload_id="JOB-002-OVERRIDE-RUN", 
            tenant_id="Tenant_Enterprise_C", 
            simulated_data={
                "predicted_base_price": 2.10,                
                "operational_cost": 185.00,                    
                "operational_features": {"total_weight_kg": 195.0}, 
                "llm_generation": {
                    "text_output": "Malformed text output string" 
                }
            }
        ), 
        
        # ────────────────────────────────────────────────────────
        # JOB 3: NODE 1 SHORT_CIRCUIT (Halts immediately at CriticAgent, Bypasses Node 2 & 3)
        # ────────────────────────────────────────────────────────
        worker_conductor(
            payload_id="JOB-003-BUDGET-SHORT", 
            tenant_id="Logistics_Corp_C", 
            simulated_data={
                "predicted_base_price": 15.00,
                "operational_cost": 650.00,                  
                "operational_features": {"total_weight_kg": 20.0},
                "llm_generation": {"text_output": "{}"}     
            }
        ), 
        
        # ────────────────────────────────────────────────────────
        # JOB 4: NODE 3 SHORT_CIRCUIT (Passes Node 1 and Node 2, but Halts at Node 3)
        # ────────────────────────────────────────────────────────
        worker_conductor(
            payload_id="INTERVIEW-SHRUTI-01", 
            tenant_id="Candidate_Shruti", 
            simulated_data={
                "predicted_base_price": 10.00,                 
                "operational_cost": 45.00,                    
                "operational_features": {"total_weight_kg": 5.0}, 
                "llm_generation": {
                    "text_output": "Leave it Shruti, just answer the current question." 
                }
            }
        )
    ]

    
    await asyncio.gather(*tasks)

    GuardTelemetry.flush_records()
    print("\n All universal metrics safely streamed to observability databases.")

if __name__ == "__main__":
    asyncio.run(main_entry())