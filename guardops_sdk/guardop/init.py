from guardops_sdk.guardop.guard_loader import load_custom_guards,load_manifest
from dotenv import load_dotenv


_INITIALIZED = False

def init_guardops():
    global _INITIALIZED

    if _INITIALIZED:
        return
    

    load_dotenv(override=False)

    load_manifest()
    load_custom_guards()

    _INITIALIZED = True