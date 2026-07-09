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
    CUSTOM_CHECK= "CUSTOM_CHECK"

class FallbackStrategy(Enum):
    DATA_OVERRIDE = "DATA_OVERRIDE"
    SHORT_CIRCUIT = "SHORT_CIRCUIT" 


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
    strategy:FallbackStrategy
    breach_tag: str="GUARDOPS_BREACH_WARNING"
    parameters: Dict[str, Any] = field(default_factory=dict)

