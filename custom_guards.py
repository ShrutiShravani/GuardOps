from typing import Dict,Any

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