def my_enterprise_security_shield(text_to_check:str,rule_config:dict)->bool:
    """
    Returns True if the text violates boundaries.
    """
    if "internal_server_ip" in text_to_check.lower():
        return True
    return False

def check_sales_persona(text_to_check:str,rule_config:dict)->bool:
    if "competitor" in text_to_check.items():
        return True
    return False
