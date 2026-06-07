# 🛡️ GuardOps: Multi-Agent Telemetry & Real-Time Policy Guardrails

GuardOps is a high-performance, production-grade security and compliance proxy layer engineered specifically for **Multi-Agent Systems (MAS)**. It acts as an inline runtime proxy that intercepts data streams between decoupled agent nodes in real-time. By dynamically validating state transitions, GuardOps enforces automated corrections (`DATA_OVERRIDE`) or instantly halts dangerous trajectories (`SHORT_CIRCUIT`) before corruption can cascade across your agent ecosystem.

By natively pairing **OpenTelemetry (via Langfuse v4)** with **Experiment & Retraining Artifact Tracking (via MLflow)**, GuardOps transforms black-box agent behaviors into a completely deterministic, auditable, and observable engineering pipeline.

---

## 🛠️ Why GuardOps? (Core Value Proposition)

Traditional LLM validation frameworks operate entirely downstream *after* a multi-agent orchestration assembly has completed its pass. In complex, multi-turn agent networks, this latent approach is fundamentally broken:

* 🚨 **Cascading Failures:** A single persona bleed or context drift in a routing agent propagates toxic, hallucinated, or non-compliant states directly to downstream execution blocks.
* 📉 **Telemetry Blindspots:** Post-facto evaluation strips out execution context, making it incredibly difficult to isolate which node inside a **Directed Acyclic Graph (DAG)** initiated a compliance breach.

GuardOps solves this by embedding validation directly into the runtime layer of individual orchestration steps, acting as a fine-grained firewall for every node in your topology.


---

## ⚙️ Key Technical Capabilities

### 🔀 Inline Interception & Mutation
The engine captures inbound and outbound dictionary payloads mid-execution. When a soft operational rule triggers a breach, GuardOps intercepts the data stream and safely forces an absolute mutation (`DATA_OVERRIDE`) on the corrupted field, allowing downstream agents to continue processing clean, validated states.

### 🛑 Deterministic Short-Circuiting
For fatal compliance or behavioral violations, GuardOps executes a `SHORT_CIRCUIT` strategy. It intercepts execution, halts the agent node pathway instantly by raising a deterministic exception (`GuardOpsRefusalIntercept`), marks the global state as blocked, and safely routes a secure fallback message back to the pipeline gateway.

### 📊 Dual-Engine Telemetry Tracking
GuardOps splits operational instrumentation across two specialized enterprise engines to ensure comprehensive observability:

| Tracking Engine | Purpose & Telemetry Strategy | Captured Observability Data |
| :--- | :--- | :--- |
| **`Langfuse v4`** | **Live Span & Quality Observation** | Records step-by-step nested open-telemetry spans, maps exact mutation diffs (`applied_mutations`), and registers binary execution quality metrics (`Data_Override` / `Short_Circuit` scores). |
| **`MLflow Engine`** | **Operational Dashboards & Retraining Pipelines** | Emits atomic metric telemetry indicators to track continuous regression, updates system run parameters, and isolates exact corrupted data snapshots into a secure local artifact directory (`mlflow_retrain_data/`) for fine-tuning loops. |

---

👉 **Want to try GuardOps immediately? Jump to the [How to Run](#-how-to-run) section.**

---

##Rule Configuration Manifests (`manifest.json`)

The entire operational runtime routing of GuardOps is governed completely by a centralized policy layout file: `manifest.json`. The configuration schema is designed to allow developers to deploy out-of-the-box static parameters or plug in complex, custom-coded Python micro-policies seamlessly.

### Core Required Structural Parameters

Every single configuration object must declare these core architectural variables:

* **`metric_key`**: The specific key target inside the execution dictionary context. This supports dot-notation (e.g., `parent.child.target_key`) to seamlessly parse deeply nested payload dictionaries.
* **`condition_type`**: The internal validation parsing directive. The core engine exposes four production modes natively:
  * **`UNDER_FLOOR`**: Asserts that numeric states do not drop below a specific baseline value limit.
  * **`OVER_CEILING`**: Asserts that numeric states do not cross an upper bound limit.
  * **`REGEX_MISMATCH`**: Validates that string text streams conform strictly to an exact structural format pattern or schema boundary.
  * **`CUSTOM_CHECK`**: Instructs the execution engine to dynamically resolve and delegate evaluation tasks to custom-written Python functions.
* **`boundary_limit`**: The evaluation barrier rule. For native numerical/text modes, this is written as a direct static literal. For custom functions, this is defined as a fully qualified module string lookup reference (`file_name.function_name`).
* **`fallback_value`**: The immediate programmatic replacement value injected into the payload when a policy breach triggers. This accepts a **static literal** (integer, string, array, object) or a **dynamic functional module route path** (`file_name.generator_name`) to generate fallback strings on the fly.
* **`strategy`**: The mitigation enforcement action taken upon a breach event. Must match either **`"DATA_OVERRIDE"`** or **`"SHORT_CIRCUIT"`**.
* **`breach_tag`**: A unique tracking label string used to index and serialize the specific violation across Langfuse span tracking contexts, MLflow dashboard parameters, and artifact retrain files.

---

### 📊 Manifest Execution Breakdown Matrix

To map your logic requirements perfectly to the configuration engine, use the reference grid below:

| Target Use Case | Required `condition_type` | How to Declare `boundary_limit` | How to Declare `fallback_value` |
| :--- | :--- | :--- | :--- |
| **Numeric Floor Enforcement** | `"UNDER_FLOOR"` | Pass raw float/integer bounds parameter (`5.00`) | Pass raw float/integer value recovery parameter (`5.00`) |
| **Numeric Ceiling Halted Traces** | `"OVER_CEILING"` | Pass raw float/integer bounds parameter (`500.00`) | Pass standard text error message string block |
| **Deep Object Path Nested Check** | `"OVER_CEILING"` | Set dot-notation traversal string on `metric_key` | Pass target fallback data match value directly |
| **Silent Schema Format Scans** | `"REGEX_MISMATCH"` | Define compiled system Regex pattern raw string | Define static JSON recovery fallback schema string |
| **Custom Code & Function Fallbacks** | `"CUSTOM_CHECK"` | Route to validation script: `"custom_guards.check_persona_bleed"` | Route to generation code: `"custom_guards.dynamic_voice_persona_fallback"` |
| **Custom Code with Flat Fallbacks** | `"CUSTOM_CHECK"` | Route to validation script: `"custom_guards.check_competitor_leak"` | Write static string text variable straight into JSON configuration file |

### The Complete Complete Blueprint Manifest Blueprint

To fully understand how native checking, nested dot-notation paths, raw values, and functional routes interoperate, review the production-grade blueprint schema example from the repository root:

```json
{
  "CriticAgent": [
    {
      "metric_key": "predicted_base_price",
      "condition_type": "UNDER_FLOOR",
      "boundary_limit": 5.00,
      "fallback_value": 5.00,
      "strategy": "DATA_OVERRIDE",
      "breach_tag": "INDIVIDUAL_PRICE_UNDER_FLOOR"
    },
    {
      "metric_key": "operational_cost",
      "condition_type": "OVER_CEILING",
      "boundary_limit": 500.00,
      "fallback_value": "Cost ceiling exceeded. Request blocked.",
      "strategy": "SHORT_CIRCUIT",
      "breach_tag": "OPERATIONAL_COST_EXCEEDS_MAX_BUDGET"
    },
    {
      "metric_key": "operational_features.total_weight_kg",
      "condition_type": "OVER_CEILING",
      "boundary_limit": 150.0,
      "fallback_value": 150.0,
      "strategy": "DATA_OVERRIDE",
      "breach_tag": "NESTED_CLUSTER_WEIGHT_LIMIT_EXCEEDED"
    }
  ],
  "LLM_Output_Generation_Node": [
    {
      "metric_key": "llm_generation.text_output",
      "condition_type": "REGEX_MISMATCH",
      "boundary_limit": "^{.*\"waybill_id\":\\s*\"WB-[0-9]{4}-[A-Z]{3}\".*}$",
      "fallback_value": "{\"status\": \"FALLBACK_STRUCTURAL_RECOVERY\", \"waybill_id\": \"WB-0000-FAILED\"}",
      "strategy": "DATA_OVERRIDE",
      "breach_tag": "PROVIDER_SILENT_SCHEMA_SHIFT_DETECTED"
    }
  ],
  "Voice_Generation_Node": [
    {
      "metric_key": "voice_generation.output",
      "strategy": "DATA_OVERRIDE",
      "checks": [
        {
          "condition_type": "CUSTOM_CHECK",
          "boundary_limit": "custom_guards.check_persona_bleed",
          "fallback_value": "custom_guards.dynamic_voice_persona_fallback",
          "breach_tag": "INTERVIEWER_PERSONA_BLEED_DETECTED"
        },
        {
          "condition_type": "CUSTOM_CHECK",
          "boundary_limit": "custom_guards.check_competitor_leak",
          "fallback_value": "As an internal assistant, I am optimized to discuss our shipping networks.",
          "breach_tag": "COMPETITOR_LEAK_SABOTAGE"
        }
      ]
    }
  ]
}

---

### Writing Extensible Custom Guards (`custom_guards.py`)

When the built-in numeric or regex validation parameters do not suffice, GuardOps allows you to plug in highly tailored Python verification policies. This is achieved by setting your manifest's `condition_type` to `"CUSTOM_CHECK"` and routing the `boundary_limit` directly to your Python file.

### 📜 The Structural Function Contract

Every custom validation function and dynamic fallback generator must adhere to a strict positional argument signature. If this contract is broken, the core engine will fail to route runtime payload data into your logic correctly.

#### 1. Custom Check Function Signature

```python
def your_check_name(value: Any, rule_config: dict) -> bool:
    pass
```

- **`value`**: The data extracted dynamically from the runtime payload using the manifest's declared `metric_key`.
- **`rule_config`**: A serialized dictionary containing all configuration values associated with the current rule.
- **Expected Return (`bool`)**:
  - Return `True` to declare a policy breach.
  - Return `False` to indicate the value passed validation successfully.

---

### 💻 Production Blueprint Example (`custom_guards.py`)

Create a file named `custom_guards.py` in your project root and implement your custom validation logic as shown below:

```python
from typing import Any, Dict

# ====================================================================
# 1. CUSTOM SYSTEM COMPLIANCE VERIFICATION GUARDS
# ====================================================================

def check_persona_bleed(value: Any, rule_config: Dict[str, Any]) -> bool:
    """
    Detects persona drift or prompt-injection style behavior.
    """
    text_to_check = str(value).lower().strip()

    test_phrases = [
        "leave it",
        "just answer",
        "forget my instructions",
        "ignore previous directives"
    ]

    if any(phrase in text_to_check for phrase in test_phrases):
        print(
            f"[GUARD INTERCEPT] Breach detected: "
            f"{rule_config.get('breach_tag')}"
        )
        return True

    return False


def check_competitor_leak(value: Any, rule_config: Dict[str, Any]) -> bool:
    """
    Prevents internal systems from leaking competitor references.
    """
    text_to_check = str(value).lower().strip()

    competitors = ["fedex", "ups", "dhl"]

    if any(company in text_to_check for company in competitors):
        print(
            f"[GUARD INTERCEPT] Competitor leak detected: "
            f"{rule_config.get('breach_tag')}"
        )
        return True

    return False


def verify_pricing_limits(value: Any, rule_config: Dict[str, Any]) -> bool:
    """
    Validates pricing boundaries.
    """
    try:
        price = float(value)

        if price <= 0.0 or price > 10000.0:
            return True

    except (ValueError, TypeError):
        return True

    return False


# ====================================================================
# 2. DYNAMIC FALLBACK DATA GENERATORS
# ====================================================================

def dynamic_voice_persona_fallback(
    current_value: Any,
    rule_config: Dict[str, Any]
) -> str:
    """
    Generates a safe replacement response when persona drift is detected.
    """

    print(
        f"[FALLBACK LOGIC] Recovering metric: "
        f"{rule_config.get('metric_key')}"
    )

    return (
        "System Note: Secure assistant context restored. "
        "Please describe your shipping requirements."
    )
```

---

### 🧩 Mapping Your Code to the Manifest

Once your `custom_guards.py` file is created, reference the functions directly from your manifest using dot-notation paths.

```json
{
  "Voice_Generation_Node": [
    {
      "metric_key": "voice_generation.output",
      "strategy": "DATA_OVERRIDE",
      "condition_type": "CUSTOM_CHECK",
      "boundary_limit": "custom_guards.check_persona_bleed",
      "fallback_value": "custom_guards.dynamic_voice_persona_fallback",
      "breach_tag": "INTERVIEWER_PERSONA_BLEED_DETECTED"
    },
    {
      "metric_key": "voice_generation.output",
      "strategy": "DATA_OVERRIDE",
      "condition_type": "CUSTOM_CHECK",
      "boundary_limit": "custom_guards.check_competitor_leak",
      "fallback_value": "As an internal logistics assistant, I am optimized to discuss our shipping networks.",
      "breach_tag": "COMPETITOR_LEAK_SABOTAGE"
    }
  ]
}
```

GuardOps automatically resolves these references at runtime:

```text
custom_guards.check_persona_bleed
          ↓
custom_guards.py
          ↓
check_persona_bleed(...)
```

No manual registration is required.

---

## 🔌 Framework Integration

GuardOps is framework-agnostic.

Whether you use LangGraph, CrewAI, Autogen, OpenAI Agents SDK, or custom orchestration code, GuardOps operates at the Python function boundary through the `@guard_runtime(...)` decorator.

### LangGraph Example

```python
from typing import TypedDict
from langgraph.graph import StateGraph
from guardops_sdk import guard_runtime


class AgentGraphState(TypedDict):
    payload_id: str
    mlflow_run_id: str
    predicted_base_price: float
    operational_cost: float
    status: str


@guard_runtime("CriticAgent")
async def verify_financial_node(
    state: AgentGraphState
) -> AgentGraphState:

    print("Validating financial state...")
    return state


workflow = StateGraph(AgentGraphState)

workflow.add_node(
    "financial_critic",
    verify_financial_node
)

```
# Add conditional edges, set entry points, and compile...


## 🚀 How to Run

> ⚠️ **Development Note:** GuardOps is currently a localized architectural framework and has **not yet been packaged as a downloadable Python library**. To evaluate or execute the framework, clone the repository and run the source code locally.

---

### 1. Clone the Repository

Pull the source code and navigate into the project directory.

```bash
git clone https://github.com/ShrutiShravani/GuardOps.git
cd GuardOps
```

---

### 2. Installation Requirements

Install all required dependencies:

```bash
pip install -r requirements.txt
```

#### Core Dependencies

If setting up manually, install the required packages:

```bash
pip install mlflow langfuse openinference-instrumentation-langchain opentelemetry-api pydantic python-dotenv
```

---

### ⚙️ Environment Configuration (`.env`)

Create a `.env` file in the project root containing your telemetry and tracking credentials.

```env
# ====================================================================
# GuardOps Infrastructure Configuration
# ====================================================================

# Langfuse Configuration
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=https://cloud.langfuse.com

# MLflow Tracking Server
MLFLOW_TRACKING_URI=http://localhost:5000
```

The GuardOps runtime automatically loads these environment variables during initialization.

---

### 3. Initialize Required Runtime Assets

Before starting the framework, verify the following files exist in your working directory:

* `guard_manifest.json` — Centralized policy routing configuration
* `custom_guards.py` — Custom validation functions and dynamic fallbacks
* `workers.py` — Pipeline worker execution entrypoint

Example project structure:

```text
GuardOps/
│
├── .env
├── guard_manifest.json
├── custom_guards.py
├── workers.py
│
└── guardops_sdk/
```

---

### 4. Execute the Simulation Engine

Once your environment and policy assets are configured, launch the worker pipeline:

```bash
python workers.py
```

---

### 5. Expected Console Output

During execution, GuardOps continuously evaluates payloads and applies runtime safety policies.

Example output:

```text
🔄 Worker processing job pipeline sequence for: JOB-001-CLEAN
🔄 Worker processing job pipeline sequence for: JOB-002-OVERRIDE-RUN
🔄 Worker processing job pipeline sequence for: JOB-003-BUDGET-SHORT
🔄 Worker processing job pipeline sequence for: INTERVIEW-SHRUTI-01

[NODE EXECUTION] LLM_Output_Generation_Node evaluating rules...
[NODE EXECUTION] Voice_Generation_Node validating persona...

[GUARD INTERCEPT] Proprietary Leaks Blocked: COMPETITOR_LEAK_SABOTAGE

[BYPASS TRIGGERED] Short-Circuit at CriticAgent. Halting execution pipeline.
[BYPASS TRIGGERED] Short-Circuit at Voice Generation Node. Halting execution pipeline.

✅ Worker complete for JOB-001-CLEAN -> Safety Status: COMPLETED_SUCCESSFULLY

[TELEMETRY COMPLETE] All metrics and traces streamed to Langfuse and MLflow.
```

---

### 6. Runtime Execution Flow

When a decorated agent executes, GuardOps wraps the complete lifecycle:

```text
[Agent Input Payload]
       │
       ▼
 ┌───────────┐
 │   Agent   │ ──► Executes internal logic, tools, or LLM calls
 └───────────┘
       │
       ▼
[Raw Output Generated]

 ┌───────────┐
 │ GuardOps  │ ──► Loads rules from registry
 │  Engine   │ ──► Resolves custom checks
 │           │ ──► Evaluates policy boundaries
 └───────────┘
       │
       ├─► PASS
       │      └── Payload continues unchanged
       │
       ├─► DATA_OVERRIDE
       │      ├── Replaces unsafe values
       │      ├── Logs artifacts to MLflow
       │      └── Creates intervention spans in Langfuse
       │
       └─► SHORT_CIRCUIT
              ├── Raises GuardOpsRefusalIntercept
              ├── Halts downstream execution
              ├── Saves retraining artifacts
              └── Returns safe failure response
```

---

## 🚀 Enterprise GuardOps Scaling Roadmap

The current architecture establishes a low-latency runtime safety layer integrated with Langfuse and MLflow. Future iterations are designed to support enterprise-scale deployments.

### 1. Decoupled Custom Guard Directories

* Move beyond a single `custom_guards.py` file.
* Support modular guard packages:

```text
guards/
├── security/
├── compliance/
├── finance/
└── operations/
```

* Automatically discover and register guard modules at startup.

---

### 2. Full Multi-Agent DAG Interception

* Native support for complex DAG-based agent workflows.
* Validate state transitions across multiple agent boundaries.
* Enable end-to-end orchestration protection:

```text
Routing Agent
      ↓
Pricing Agent
      ↓
Risk Agent
      ↓
Auditor Agent
```

Each node can independently enforce GuardOps policies.

---

### 3. Manifest Parameterization & Centralized Control

* Move thresholds and evaluation parameters into manifests.
* Support JSON and YAML policy definitions.
* Enable zero-code policy updates without redeployment.

Example:

```json
{
  "boundary_limit": 5000,
  "fallback_value": 2500,
  "breach_tag": "PRICE_LIMIT_EXCEEDED"
}
```

This allows operators to modify policies without changing application code.
