from dotenv import load_dotenv
load_dotenv()
import asyncio
from guardops_sdk.guardop.telemetry import GuardTelemetry
from guardops_sdk.guardop.decorators import guard_runtime
import mlflow
from mlflow.tracking import MlflowClient
import os
from custom_guards import update_session_turn, store_candidate_fact,_get_session



@guard_runtime(node_name="CriticAgent")
async def execute_critic_agent(payload:dict)->dict:
    """
    Universal Agent Node Middleware execution block.
    """
    await asyncio.sleep(0.1)
    return payload

@guard_runtime(node_name="LLM_Output_Generation_Node")
async def execute_llm_generation(payload:dict)->dict:
    print("[NODE EXECUTION] LLM_Output_Generation_Node evaluating rules...")
    await asyncio.sleep(0.05)
    return payload

@guard_runtime(node_name="Voice_Generation_Node")
async def execute_voice_generation(payload:dict)->dict:
    print("[NODE EXECUTION] Voice_Generation_Node validating persona...")
    await asyncio.sleep(0.05)
    return payload

@guard_runtime(node_name="Chat_Generation_Node")
async def execute_chat_generation(payload: dict) -> dict:
    print("[NODE EXECUTION] Chat_Generation_Node validating session context...")
    await asyncio.sleep(0.05)
    return payload

async def worker_conductor(payload_id:str,tenant_id:str,simulated_data:dict):
    """
    Universal Worker Conductor: Runs on an isolated, thread-safe memory context.
    Spawns the Langfuse parent trace session and drives the payload stream.
    """
    
    # 2. Build a completely abstract, universal payload structure

    GuardTelemetry.start_trace_session(
        trace_name=f"WorkerPipeline_{payload_id}",
        user_id=tenant_id,
        tags=["Production-Runtime-Shield", "Architecture-v1"]
    )
   
    payload = {
        "status": "PROCESSING",
        "agent_trace": [],
        **simulated_data  # <─── Unpacks any dynamic dictionary keys right into the payload!
    }

    print(f"Worker starting job for {payload_id}")
    try:
    
        #fire paylad to guard runtime
        payload = await execute_critic_agent(payload)
        if payload.get("status")=="BLOCKED_BY_GUARDOP_POLICY":
            print(f"[BYPASS TRIGGERED] Data override at CriticAgent. Halting execution pipeline.")   
            return payload

        payload= await execute_llm_generation(payload)
        if payload.get("status")=="BLOCKED_BY_GUARDOP_POLICY":
            print(f"[BYPASS TRIGGERED] Short-Circuit at LLM Generation Node. Halting execution pipeline.")
         
            return payload
        
        payload= await execute_voice_generation(payload)
        if payload.get("status")=="BLOCKED_BY_GUARDOP_POLICY":
            print(f"[BYPASS TRIGGERED] Data override at Voice Generation Node. Halting execution pipeline.")

            return payload

        payload = await execute_chat_generation(payload)
        if payload.get("status") == "BLOCKED_BY_GUARDOP_POLICY":
            print(f"[BYPASS TRIGGERED] Data override at Chat Generation Node.")
            return payload

        payload["status"]="COMPLETED_SUCCESSFULLY"
        print(f"Worker complete for {payload_id} -> Safety Status: {payload.get('status')}")
    
        print(f"Pipeline Execution Graph {payload_id} complete.")
        return sanitize_payload(payload)
    except Exception as e:
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
     # Simulates turns that already happened in the interview
    
    
    # DEMO ONLY — simulates 2 prior interview turns already completed
    # In production this builds automatically turn by turn

        # Voice session
    session = _get_session("interview_session_001")
    session["questions_asked"].append("Tell me about yourself")
    session["questions_asked"].append("Walk me through a system design")
    session["last_turns"] = [
        "User: I have 3 years Python experience in fintech",
        "Agent: Tell me about yourself",
        "User: I built a distributed caching layer",
        "Agent: Walk me through a system design"
    ]
    session["turn_count"] = 2 # ← belongs here not below

    # Chat session
    session_chat = _get_session("chat_session_001")  # ← must come first
    session_chat["questions_asked"].append("Tell me about yourself")
    session_chat["candidate_facts"]["python experience"] = "3 years in fintech"
    session_chat["last_turns"] = [
        "User: I have 3 years Python experience",
        "Agent: Tell me about yourself"
    ]
    session_chat["turn_count"] = 2
        
    tasks = [
        # ────────────────────────────────────────────────────────
        # JOB 1: CLEAN RUN (Passes all validations flawlessly)
        # ────────────────────────────────────────────────────────
        worker_conductor(
            payload_id="JOB-001-CLEAN", 
            tenant_id="Logistics_Corp_A", 
            simulated_data={
                "predicted_base_price": 4.00,               
                "operational_cost": 120.00,                  
                "operational_features": {"total_weight_kg": 45.0}, 
                "output": '{"waybill_id": "WB-2026-NYC", "status": "VERIFIED"}'
                
            }
        ),
        
        # ────────────────────────────────────────────────────────
        # JOB 2: OVERRIDE RUN (Triggers Pricing/Weight corrections & Competitor Leak Overrides)
        # ────────────────────────────────────────────────────────
        worker_conductor(
            payload_id="JOB-002-OVERRIDE-RUN", 
            tenant_id="Tenant_Enterprise_C", 
            simulated_data={
                "text_output": "Malformed text output string"
            }
        ), 
        
    
        
        
        # JOB 3: VOICE — question repeat breach
        worker_conductor(
            payload_id="INTERVIEW-VOICE-REPEAT",
            tenant_id="Candidate_Demo",
            simulated_data={
                "voice_output": "Tell me about yourself"  # already asked → VOICE_QUESTION_REPEATED
            }
        ),

        # JOB 4: VOICE — context loss breach
        # Agent says something completely off-topic
        worker_conductor(
            payload_id="INTERVIEW-VOICE-CONTEXT",
            tenant_id="Candidate_Demo_2",
            simulated_data={
                # Completely off topic from interview context → LLM judge says NO
                "voice_output": "What is today's weather in Mumbai?"
            }
        ),

        # JOB 5: CHAT — contradiction breach
        worker_conductor(
            payload_id="CHAT-AGENT-CONTRADICTION",
            tenant_id="Candidate_Chat",
            simulated_data={
                "chat_output": "Do you have any Python experience?"
            }
        ),

        # JOB 6: CHAT — question repeat breach
        worker_conductor(
            payload_id="CHAT-AGENT-REPEAT",
            tenant_id="Candidate_Chat_2",
            simulated_data={
                "chat_output": "Tell me about yourself"  # already asked in chat session
            }
        ),
    ]


    
    await asyncio.gather(*tasks,return_exceptions=True)

    GuardTelemetry.flush_records()
    print("\n All universal metrics safely streamed to observability databases.")

if __name__ == "__main__":
    print(os.getcwd())
    print(os.path.abspath("guard_manifest.json"))
    
    asyncio.run(main_entry())