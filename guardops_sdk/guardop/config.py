from enum import Enum,auto
from typing import Any,Optional,List,Union,Dict
from dataclasses import dataclass,field
import json
import os 

from enum import Enum

class ConditionType(Enum):
    UNDER_FLOOR = "UNDER_FLOOR"
    OVER_CEILING = "OVER_CEILING"
    REGEX_MISMATCH = "REGEX_MISMATCH"
    NOT_IN_SET = "NOT_IN_SET"
    SCHEMA_MISSING_KEYS = "MISSING_KEYS"

class FallbackStrategy(Enum):
    DATA_OVERRIDE = "DATA_OVERRIDE"
    SHORT_CIRCUIT = "SHORT_CIRCUIT"  # Matches your manifest perfectly!
    STATIC_REFUSAL = "STATIC_REFUSAL"
    

@dataclass
class GuardConfig:
    """
    The universal data contract for an isolated GuardOps boundary gate.
    Defines exactly what parameter to monitor and the mitigation rules.
    """
    metric_key:str
    condition_type:ConditionType
    boundary_limit: Any
    fallback_value:Any
    strategy:FallbackStrategy=FallbackStrategy.SHORT_CIRCUIT
    breach_tag: str="GUARDOPS_BREACH_WARNING"
    metadata:dict=field(default_factory=dict)

