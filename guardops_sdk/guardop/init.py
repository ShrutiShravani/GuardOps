import os
from dotenv import load_dotenv

# 1. Load environment variables BEFORE importing MLflow
load_dotenv(override=True)

# 2. Explicitly force the unblock variables into system memory if they aren't set
if not os.getenv("MLFLOW_ALLOW_FILE_STORE"):
    os.environ["MLFLOW_ALLOW_FILE_STORE"] = "true"

if not os.getenv("MLFLOW_TRACKING_URI"):
    os.environ["MLFLOW_TRACKING_URI"] = "sqlite:///mlflow.db"

import mlflow
from guardops_sdk.guardop.guard_loader import (
    load_custom_guards,
    load_manifest,
)
import os

_INITIALIZED = False
_EXPERIMENT_ID = None

def get_experiment_id():
    return _EXPERIMENT_ID

def is_initialized():
    return _INITIALIZED

def init_guardops():

    global _INITIALIZED
    global _EXPERIMENT_ID

    if _INITIALIZED:
        return

    load_dotenv(override=False)

    tracking_uri = os.getenv("MLFLOW_TRACKING_URI")

    if tracking_uri:
        mlflow.set_tracking_uri(tracking_uri)

    experiment_name = "GuardOps_Universal_Shield_Analytics"

    exp = mlflow.get_experiment_by_name(experiment_name)

    if exp is None:
        _EXPERIMENT_ID = mlflow.create_experiment(experiment_name)
    else:
        _EXPERIMENT_ID = exp.experiment_id

    load_manifest()
    load_custom_guards()

    _INITIALIZED = True