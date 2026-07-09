from typing import Dict,Any

from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from openai import OpenAI


_embed_model = SentenceTransformer("all-MiniLM-L6-v2")
_openai_client = OpenAI()

_session_memory = {}



def check_persona_bleed(value:str,rule_config:dict)->bool:
    """
    Scans specifically for behavioral context drift or model breakdown phrases.
    """
    text_to_check= value.lower()
    test_phrases= ["leave it", "just answer", "forget my instructions"]
    if  any(phrase in text_to_check for phrase in test_phrases):
        print("[GUARD] True Breach Detected: Persona Bleed.")
        return True
    return False

def check_competitor_leak(value:Any,rule_config:dict)->bool:
    """
    Scans strictly for rival corporate entities or pricing complaints.
    """
    text_to_check= str(value).lower()
    competitors=["fedex","ups","dhl"]
    if any(comp in text_to_check for comp in competitors):
        print("[GUARD] Compettitor leaked")
        return True
    return False

# DYNAMIC FALLBACK GENERTAOR
def dynamic_voice_persona_fallback(failed_text:str,rule_config:dict)->str:
    """
    [Automated Dialogue Recovery Slot]
    Dynamically generates context-aware conversational recovery phrases 
    for chatbots and voice agents to keep users cleanly aligned.
    """

    print("[DYNAMIC CORRECTOR]: Initiating dynamic dialogue recovery compilation")
    
    return (
         "I apologize for the detour. I am here to fully support your evaluation process. "
        "Let's move directly back to our core objective. What is your immediate next question?"
    )

def _get_session(session_id:str)->dict:
    if session_id not in _session_memory:
        _session_memory[session_id] = {
            "questions_asked": [],
            "candidate_facts": {},
            "last_turns": [],       # was missing before
            "turn_count": 0,
            "current_stage": "intro"
        }
    return _session_memory[session_id]
     
    
# guard1 question repeat
def check_question_repeat(value:any,rule_config:dict)->bool:
    session_id = rule_config.get("parameters",{}).get("session_id","default")

    session = _get_session(session_id)

    if not session["questions_asked"]:
        return False
    
    new_embed= _embed_model.encode([str(value)])
    past_embeds= _embed_model.encode(session["questions_asked"])

    scores= cosine_similarity(new_embed,past_embeds)[0]

    breach= float(max(scores))>0.82
    if breach:
       print(f"[GUARD] Question repeat detected. Score: {max(scores):.2f}")
    return breach

def recover_next_question(value:any,rule_config:dict)->str:
    session_id= rule_config.get("parameters",{}).get("session_id","default")
    question_bank = rule_config.get("parameters", {}).get("question_bank", [])
    session = _get_session(session_id)
    asked = set(session["questions_asked"])

    for q in question_bank:
        if q not in asked:
            session["questions_asked"].append(q)
            return q
    return "We have covered all planned questions. Do you have any questions for us?"


#guard 2 contetx loss

def check_context_loss(value:any,rule_config:dict)->bool:
    session_id=rule_config.get("parameters",{}).get("session_id","default")
    session= _get_session(session_id)

    if session["turn_count"]<2 or not session["last_turns"]:
        return False
    
    response =  _openai_client.chat.completions.create(
        model="gpt-4o-mini",
        max_tokens=5,
        messages=[{
            "role": "user",
            "content": f"""Conversation so far:
        {session["last_turns"]}

        Agent just said:
        {value}

Does this response logically follow? Reply only YES or NO."""
        }]
    )
    
    result=response.choices[0].message.content.strip().upper()

    breach="NO" in result

    if breach:
        print(f"[GUARD] Context loss detected by LLM judge")

    return breach


def recover_context_anchor(value:any, rule_config:dict)->str:
    session_id = rule_config.get("parameters", {}).get("session_id", "default")
    session = _get_session(session_id)
    stage = session.get("current_stage", "technical")
    return (
        f"Let me refocus — we were discussing the {stage} portion. "
        f"Could you elaborate further on what you shared?"
    )


#session helpers 

def update_session_turn(session_id:str,agent_output:str,user_input:str):
    session= _get_session(session_id)
    session["turn_count"]+=1
    session["last_turns"].append(f"user:{user_input}")
    session["last_turns"].append(f"Agent:{agent_output}")
    session["last_turns"]=session["last_turns"][-6:]

def store_candidate_fact(session_id:str,topic:str,answer:str):
    session= _get_session(session_id)
    session["candidate_facts"][topic]=answer






