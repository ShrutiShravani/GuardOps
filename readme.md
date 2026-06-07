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
---

### 🛠️ Writing Extensible Custom Guards (`custom_guards.py`)

When the built-in numeric or regex validation parameters do not suffice, GuardOps allows you to plug in highly tailored Python verification policies. This is achieved by setting your manifest's `condition_type` to `"CUSTOM_CHECK"` and routing the `boundary_limit` directly to your python file.

### 📜 The Structural Function Contract

Every single custom validation function and dynamic fallback generator must adhere to a strict structural positional argument signature. If this signature contract is broken, the core engine will fail to route data payload context variables to your logic module.

#### 1. Custom Check Function Signature

```python
def your_check_name(value: Any, rule_config: dict) -> bool:
    pass


* **`value`**: The data state dynamically isolated from the runtime payload using the manifest's declared `metric_key`.
* **`rule_config`**: A flat serialization dictionary containing all properties, keys, and routing tags declared for this specific rule object in the configuration file.
* **Expected Return (`bool`)**: Return `True` to explicitly declare a critical policy breach (this triggers your chosen remediation strategy). Return `False` to signal a safe execution state, letting the payload pass untouched.

### 💻 Production Blueprint Example (`custom_guards.py`)

Create a script file named `custom_guards.py` exactly inside your root execution directory workspace. Implement your evaluation logic blocks and dynamic message overrides as follows:

```python
import re
from typing import Any, Dict

# ====================================================================
# 1. CUSTOM SYSTEM COMPLIANCE VERIFICATION GUARDS
# ====================================================================

def check_persona_bleed(value: Any, rule_config: Dict[str, Any]) -> bool:
    """
    Scans raw agent output text streams for behavioral context drift,
    jailbreak attempts, or LLM system model-breakdown keywords.
    """
    # Ensure raw input is parsed into a clean string layout
    text_to_check = str(value).lower().strip()
    
    # Core adversarial instruction breakdown markers
    test_phrases = ["leave it", "just answer", "forget my instructions", "ignore previous directives"]
    
    # Evaluate context condition
    if any(phrase in text_to_check for phrase in test_phrases):
        print(f"[GUARD INTERCEPT] True Breach Detected via: {rule_config.get('breach_tag')}")
        return True  # 🚨 Trigger remediation routing instantly
        
    return False  # ✅ Passed validation check cleanly


def check_competitor_leak(value: Any, rule_config: Dict[str, Any]) -> bool:
    """
    Monitors proprietary multi-agent logistics pipelines to ensure internal 
    routing logic does not accidentally output external competitor network names.
    """
    text_to_check = str(value).lower().strip()
    competitors = ["fedex", "ups", "dhl"]
    
    if any(brand in text_to_check for brand in competitors):
        print(f"[GUARD INTERCEPT] Proprietary Leaks Blocked: {rule_config.get('breach_tag')}")
        return True  # 🚨 Operational policy violated
        
    return False  # ✅ Passed validation check cleanly


def verify_pricing_limits(value: Any, rule_config: Dict[str, Any]) -> bool:
    """
    Enforces strict high-precision pricing boundary validation on agent numeric values
    to shield financial layers from data truncation errors or massive outlier hallucinations.
    """
    try:
        price = float(value)
        # Violates policy if pricing is free, negative, or clearly anomalous
        if price <= 0.0 or price > 10000.0:
            return True
    except (ValueError, TypeError):
        # Defensively trigger breach state if structural typing is corrupted
        return True  
        
    return False


# ====================================================================
# 2. DYNAMIC FALLBACK DATA GENERATOR FUNCTIONS
# ====================================================================

def dynamic_voice_persona_fallback(current_value: Any, rule_config: Dict[str, Any]) -> str:
    """
    Generates a context-aware, structured replacement message on the fly 
    to recover processing states when a persona drift is successfully isolated.
    """
    print(f"[FALLBACK LOGIC] Reclaiming control state for metric: {rule_config.get('metric_key')}")
    
    # Clean fallback sequence tailored to maintain client-facing conversational flow
    return "System Note: Secure agent context established. Please outline your shipping con

### 🧩 Mapping your Code to the Configuration Manifest

Once your `custom_guards.py` file is written, declare your custom routes inside your central `manifest.json` block. Notice how `boundary_limit` and `fallback_value` cleanly use **dot-notation references** matching your file naming architecture:

```json
{
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
          "fallback_value": "As an internal logistics assistant, I am optimized to discuss our shipping networks.",
          "breach_tag": "COMPETITOR_LEAK_SABOTAGE"
        }
      ]
    }
  ]
}

### 🔌 Framework Integration: How to Apply GuardOps to Your Actual Code

In a real production system, you are likely not passing a manual dictionary from function to function via an explicit `asyncio.gather`. Instead, you are using agentic orchestration frameworks like **LangGraph**, **CrewAI**, or custom business logic pipelines.

> 💡 **Core Benefit:** The beauty of the GuardOps decorator is that it is **framework-agnostic**. It operates strictly at the function boundary. No matter what orchestrator you use, your agents are ultimately just Python functions or methods that accept an input state and return an updated output state.


---

#### LangGraph State Channels Integration

In LangGraph, state is passed between graph nodes as a central, mutable state schema (usually a subclass of `TypedDict` or a Pydantic model). To secure a LangGraph node, simply place the `@guard_runtime` decorator directly over the node function definition.

The decorator intercepts the incoming graph state channel, runs the evaluation matrix, mutates or short-circuits if needed, and returns the updated state directly back to the graph runner.


```python
from typing import TypedDict
from langgraph.graph import StateGraph, END
from guardops_sdk.guardop.decorators import guard_runtime

# 1. Define your standard LangGraph State
class AgentGraphState(TypedDict):
    payload_id: str
    mlflow_run_id: str
    predicted_base_price: float
    operational_cost: float
    status: str

# 2. Decorate your node function normally
@guard_runtime(node_name="CriticAgent")
async def verify_financial_node(state: AgentGraphState) -> AgentGraphState:
    """
    An actual LangGraph compilation node function.
    """
    # Your internal routing, tool calls, or LLM evaluation logic happens here
    print(f"Validating state pricing bounds inside LangGraph channel...")
    return state

# 3. Build your graph framework normally
workflow = StateGraph(AgentGraphState)
workflow.add_node("financial_critic", verify_financial_node)
# Add conditional edges, set entry points, and compile...


### 🚀HOW TO RUN 

> ⚠️ **Development Note:** GuardOps is currently a localized architectural framework and has **not been packaged as a downloadable distribution library yet**. To execute or evaluate this framework, you must clone the repository directly and run its modular assets locally inside your workspace sandbox.

### 1. Clone the Architecture Repository
Pull down the source code and ensure you extract all baseline core infrastructure elements (including the compliance engine, telemetry registry, and custom scripts) into your local project root:

```bash
git clone https://github.com/ShrutiShravani/GuardOps
cd GuardOps

### 2 Installation Requirements

Ensure your Python execution sandbox has the necessary monitoring packages and internal SDK elements installed:
pip install -r requirements.txt


#### If you are setting up a clean workspace manually, the core package dependencies are:

```bash
pip install mlflow langfuse openinference-instrumentation-langchain opentelemetry-api pydantic


### 2⚙️ Environment Configuration (`.env`)

To activate the dual-engine monitoring infrastructure, create a `.env` file in your root workspace containing your target credentials. The runtime decorator automatically references these variables to bind open-telemetry channels and MLflow client sessions securely.

```bash
# ====================================================================
# GuardOps Infrastructure Configuration
# ====================================================================

# Langfuse v4 OpenTelemetry Core Connection Keys
LANGFUSE_PUBLIC_KEY="pk-lf-..."
LANGFUSE_SECRET_KEY="sk-lf-..."
LANGFUSE_HOST="https://cloud.langfuse.com](https://cloud.langfuse.com)" # Or your dedicated self-hosted server URI

# MLflow Central Tracking Engine Coordinates
MLFLOW_TRACKING_URI="http://localhost:5000" # Target tracking URI for experiment metrics & logs

---

### 3. Initialize the Active Policy Manifest

** Before running the engine, verify that the following vital orchestration assets are co-located within your current working execution directory:

** *manifest.json — The centralized active policy routing configuration.

** *custom_guards.py — The functional system compliance validation logic and dynamic fallbacks.

** *workers.py — The universal parent pipeline worker conductor and multi-tenant simulator.

---

### 4. Execute the Simulation Engine

With your tracking credentials connected and your policy manifest initialized, launch your master pipeline conductor directly from your system console:

python -m workers.py

---

### 5. Expected Console Outputs & Intercept Activity

** When running the concurrent simulation engine, look at your terminal log tracking. You will see the asynchronous lifecycle showing exactly how soft violations trigger data overrides while critical violations natively raise a GuardOpsRefusalIntercept to stop subsequent processing blocks instantly:

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

[TELEMETRY COMPLETE] All metrics and traces cleanly streamed to Langfuse and MLflow.

---

### 6. Behind the Scenes Runtime Trace Flow

When the decorated agent function fires, GuardOps wraps the asynchronous execution lifecycle completely:

```text
[Agent Input Payload]
       │
       ▼
 ┌───────────┐
 │   Agent   │ ──► Executes raw internal neural calculations / tools
 └───────────┘
       │
       ▼ [Raw Output Generated]
 ┌───────────┐
 │ GuardOps  │ ──► Extracts rule list for "auditor_agent_node" from registry
 │  Engine   │ ──► Maps target paths and tests custom function conditions
 └───────────┘
       │
       ├─► [PASS] ──► Returns payload downstream completely unmodified.
       │
       ├─► [DATA_OVERRIDE]
       │     ├── Replaces corrupted text with safe system fallbacks inline.
       │     ├── Logs explicit metric shifts + file snapshots to MLflow server.
       │     └── Pushes span mutations and score telemetry to Langfuse UI.
       │
       └─► [SHORT_CIRCUIT]
             ├── Raises a `GuardOpsRefusalIntercept` exception to instantly halt node processing, short-circuit the execution flow, and completely bypass all subsequent downstream nodes.
             ├── Saves raw corrupted states to 'mlflow_retrain_data/'.
             └── Appends telemetry errors and safely returns error dictionary downstream.

---

### 7 🚀 Enterprise GuardOps Scaling Roadmap

The current architecture establishes a zero-dependency baseline built for low-latency tracing across MLflow metrics and Langfuse open telemetry. To scale this framework into an enterprise-ready API gateway, the codebase is structurally prepared for the following iterations:

### 1. Decoupled Custom Guard Directories
- Transition from a single `custom_guards.py` script into an structured module package layout (`/guards/domain_a`, `/guards/domain_b`).
- Implement dynamic directory path scanning into the `GuardExecutionEngine` to auto-discover and load domain-isolated custom rules.

### 2. Full Multi-Agent DAG Interception
- Map evaluation node chains to align natively with Directed Acyclic Graphs (DAG) structures.
- Inject the `@guard_runtime` decorator across cross-functional agent boundaries (e.g., Routing Agent ➔ Pricing Agent ➔ Auditor Agent) to ensure cross-node state validation.

### 3. Manifest Parameterization & Centralized Control
- Move hardcoded evaluation thresholds and string matches out of python runtime definitions and into flat JSON/YAML manifests.
- Leverage the engine's built-in `rule_serializable_config` payload transfer to feed runtime variables directly into reusable custom guard blocks, achieving zero-redeploy system modifications.