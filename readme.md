# GuardOps

Runtime safety proxy for multi-agent AI systems. Intercepts payloads between agent nodes in real-time — before failures cascade across the pipeline.

## What it does

- **DATA_OVERRIDE** — detects a breach, mutates the unsafe field in-place, pipeline continues
- **SHORT_CIRCUIT** — raises `GuardOpsRefusalIntercept`, halts the pipeline immediately
- **Telemetry** — every breach is logged to Langfuse (live spans) and MLflow (retraining artifacts)

## Project structure

```
guardops/           ← installable Python package (pip install .)
  __init__.py       ← public API
  config.py         ← GuardConfig, ConditionType, FallbackStrategy
  engine.py         ← GuardExecutionEngine (stateless, Pydantic-aware)
  registry.py       ← GuardRegistry (rule store, manifest loader)
  decorators.py     ← @guard_runtime decorator
  telemetry.py      ← optional Langfuse integration
  init.py           ← optional MLflow integration
  guard_loader.py   ← file-based manifest + custom_guards discovery
  base.py           ← BaseGuard ABC for typed custom guards
  schema.py         ← manifest JSON schema validation
  cli.py            ← `guardops init` / `guardops validate` CLI


examples/
  quickstart.py          ← zero-config demo (no API keys needed)
  logistics/             ← multi-node logistics pipeline
  voice_agent/           ← voice interview agent (repeat + context detection)
  chat_agent/            ← chat interview agent (repeat + contradiction detection)
  with_langgraph/        ← LangGraph integration pattern

tests/
  test_engine.py         ← engine unit tests
  test_registry.py       ← registry + manifest loading tests
  test_cli.py            ← CLI tests

guard_manifest.json      ← root demo manifest
custom_guards.py         ← root demo custom guards
main.ipynb               ← original demo notebook
```

## How to run

### Quickstart (no API keys needed)
```bash
pip install -e .
python examples/quickstart.py
```

### With full observability
```bash
# Add to .env:
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com
MLFLOW_TRACKING_URI=sqlite:///mlflow.db   # or a remote URI

pip install -e ".[telemetry]"
python examples/logistics/main.py
```

### CLI
```bash
guardops init              # scaffold manifest + custom_guards.py
guardops validate          # validate an existing manifest
```

### Tests
```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Core concept

```python
from guardops import guard_runtime, GuardOpsRefusalIntercept

@guard_runtime(node_name="PricingAgent")
async def pricing_agent(payload: dict) -> dict:
    payload["price"] = compute_price(payload)
    return payload   # GuardOps intercepts before the result leaves this node
```

Rules live in `guard_manifest.json`. Custom logic lives in `custom_guards.py`.
Run `guardops init` to scaffold both.

## Environment variables

| Variable | Purpose | Required |
|---|---|---|
| `LANGFUSE_PUBLIC_KEY` | Langfuse observability | Optional |
| `LANGFUSE_SECRET_KEY` | Langfuse observability | Optional |
| `LANGFUSE_HOST` | Langfuse host URL | Optional |
| `MLFLOW_TRACKING_URI` | MLflow tracking server | Optional |
| `GUARDOPS_MLFLOW_ENABLED` | Force-enable MLflow with local sqlite | Optional |
| `OPENAI_API_KEY` | LLM-as-judge custom guards | Optional |

## User preferences

- Do not restructure or remove the demo notebook (`main.ipynb`)
- Telemetry stays fully intact — Langfuse + MLflow are features, not optional extras
