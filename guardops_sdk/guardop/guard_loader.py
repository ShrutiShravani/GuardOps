import os
import importlib.util
from guardops_sdk.guardop import GuardRegistry

def find_project_root():
    return os.getcwd()


def load_manifest():
    root = find_project_root()

    manifest_path= os.path.join(root,"guard_manifest.json")

    if not os.path.exists(manifest_path):
        raise FileNotFoundError(f"guard_manifest.json does not exists")
    
    GuardRegistry.load_manifest(manifest_path)

    return manifest_path


def load_custom_guards():
    root = find_project_root()

    guard_file = os.path.join(root,"custom_guards.py")

    if not os.path.exists(guard_file):
        return None
    
    spec =importlib.util.spec_from_file_location(
        "custom_guards",
        guard_file
    )

    module= importlib.util.module_from_spec(spec)

    spec.loader.exec_module(module)

    return module


