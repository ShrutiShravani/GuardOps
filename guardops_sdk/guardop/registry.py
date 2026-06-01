import os
import json
from typing import Dict,List,Any
from guardops_sdk.guardop.config import GuardConfig,ConditionType,FallbackStrategy

class GuardRegistry:
    _registry:Dict[str,List[GuardConfig]]={}

    @classmethod
    def load_manifest(cls,filepath:str)->None:
        """Parses an external JSON manifest and compiles it into dynamic GuardConfigs."""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"Guardops Manifest file not found at :{filepath}")

        with open(filepath,"r") as f:
            manifest_data=json.load(f)

        cls._registry.clear()

        #compile losse text from json into strict python constants

        for node_name,rule_list in manifest_data.items():
            cls._registry[node_name]=[]

            for rule in rule_list:
                complied_config=GuardConfig(
                    metric_key=rule["metric_key"],
                    condition_type=ConditionType[rule["condition_type"]],
                    boundary_limit=rule["boundary_limit"],
                    fallback_value=rule["fallback_value"],
                    strategy=FallbackStrategy[rule["strategy"]],
                    breach_tag=rule["breach_tag"]
                )
                cls._registry[node_name].append(complied_config)


    @classmethod
    def get_rules_for_node(cls,node_name:str) -> List[GuardConfig]:
        """Returns the pre-compiled rules assigned to a specific agent node."""
        if not cls._registry:
            default_path="guard_manifest.json"
            if os.path.exists(default_path):
                print(f"[GUARD REGISTRY] Auto-detecting and compiling '{default_path}'...")
                cls.load_manifest(default_path)
            else:
                print(f" [GUARD REGISTRY] WARNING: No active rules in memory and '{default_path}' not found!")
        return cls._registry.get(node_name, [])

    
    @staticmethod
    def extract_value_by_path(payload:Dict[str,Any],path:str)->Any:
        """Traverses nested dictionaries using dot-notation string keys."""
        parts = path.split(".")
        current = payload
        for part in parts:
            if isinstance(current,dict) and part in current:
                current= current[part]
            else:
                return None
        return current
    
    @staticmethod
    def override_value_by_path(payload:Dict[str,Any],path:str,fallback_value:Any)->None:
        """Modifies a deep target key in place inside a nested dictionary."""
        parts=path.split(".")
        current=payload
        for part in parts[:-1]:
            if part not in current or not isinstance(current[part],dict):
                current[part]={}
            current=current[part]
        current[parts[-1]]=fallback_value