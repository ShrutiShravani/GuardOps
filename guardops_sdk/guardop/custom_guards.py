from typing import Dict,Any

def check_persona_bleeed(value:str,rule_config:dict)->bool:
    """
    Scans specifically for behavioral context drift or model breakdown phrases.
    """
    text_to_check= value.lower()
    test_phrases= ["leave it", "just answer", "forget my instructions"]
    return any(phrase in text_to_check for phrase in test_phrases)

def check_competitor_leak(value:Any,rule_config:dict)->bool:
    """
    Scans strictly for rival corporate entities or pricing complaints.
    """
    text_to_check= str(value).lower()
    competitors=["fedex","ups","dhl"]
    return any(comp in text_to_check for comp in competitors)

"""
def check_persona_bleed_llm_judge(text_to_check: str, rule_config: dict) -> bool:
    
    [Use Case B: LLM-As-A-Judge Model]
    Pulls 'fallback_value' out of rule_config dynamically to use as a semantic anchor.
    
    breach_tag= rule_config.get("breach_tag", "GENERIC_BEHAVIORAL_DRIFT")

    evaluator_prompt = f"
    [SYSTEM JUDGE EVALUATOR]
    Analyze if the generated text completely deviates from the baseline topic intent.
    Generated Text to Inspect: "{text_to_check}"
    
    Output rules: Reply exactly 'True' if it deviates, or 'False' if it adheres.
    
    
    # Simulating a call to a low-latency utility model (e.g., Llama-3-8B)
    # Mocking behavior: If user forces a reset break phrase, simulate LLM returning True
    untrusted_text= text_to_chcek.lower()
    if "forget my instructions" in text_to_check.lower() or "leave it" in text_to_check.lower():
        print(" [LLM JUDGE EVALUATOR]: Intent drift captured. Score: 1.0 (VIOLATION)")
        return True
    return False

"""
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