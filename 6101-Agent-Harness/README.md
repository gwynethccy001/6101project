
# 6101 Agent Harnesses

Safety gate for LLM agents using the AgentDojo framework. The system intercepts tool calls and applies policies to approve, deny, or escalate requests based on tool risk metadata.

This project also includes **R5 evaluation, cost tracking, and analysis utilities** to study the trade-offs between task completion, security, human review workload, and model usage cost.

## Features

### R1 — Safety Gate and Risk-Based Policy

- Intercepts agent tool calls before execution.
- Supports `AUTO_APPROVE`, `AUTO_DENY`, and `ESCALATE` decisions.
- Uses YAML-based tool risk metadata.
- Supports human review through a Reviewer interface.
- Tracks and enforces a per-task escalation budget.
- Provides a pipeline factory for integrating the safety gate with AgentDojo.

### R5 — Evaluation, Cost, and Analysis

- **Experiment Logger:** Records gate decisions and task-level results in JSONL format.
- **Cost Tracker:** Records model calls, token usage, reported costs, and cost information by component.
- **Metrics:** Calculates task completion and safety metrics, human-review workload, and cost summaries.
- **Experiment Runner:** Generates experiment plans across benchmark tasks, policy configurations, and escalation budgets, and exports the plan to CSV.

The R5 utilities provide the foundation for reproducible experiments. Full end-to-end integration with AgentDojo and completed benchmark runs remain work in progress.

## Setup

### Prerequisites

- Python 3.11+
- AgentDojo
- Ollama for local LLM execution, or an OpenAI-compatible API
- Git

### Installation

Clone the repository:

```bash
git clone <repo-url>
cd 6101-agent-harness
```

Create and activate a Conda environment:

```bash
conda create -n agent python=3.11
conda activate agent
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Install Ollama from [https://ollama.com](https://ollama.com).

Pull the model:

```bash
ollama pull qwen3:14b
```

Check the installed model:

```bash
ollama list
```

Start the Ollama service if it is not already running:

```bash
ollama serve
```

Keep the Ollama service running in a separate terminal when using the local model.

## Usage

### Running Tests

Run the test suite from the repository root:

```bash
python -m pytest tests/ -v
```

The expected number of passing tests should be confirmed against the current repository version. The original R1 README reported 23 tests; additional R5 tests and later changes may affect the total.

To run the main R1 gate and risk-policy tests:

```bash
python -m pytest tests/test_gate.py tests/test_gate_integration.py tests/test_risk_policy.py -q
```

### Building a Pipeline

Load tool risk metadata:

```python
from src.pipeline import build_pipeline
from src.risk_based_policy import RiskBasedPolicy
from src.tool_risk import load_tool_risk_metadata
from openai import OpenAI

md = load_tool_risk_metadata("src/tool_risk_metadata.yaml")
```

Create a policy:

```python
policy = RiskBasedPolicy(md)
```

Create an OpenAI-compatible client for Ollama:

```python
client = OpenAI(
    base_url="http://localhost:11434/v1",
    api_key="ollama",
)
```

Build the pipeline:

```python
pipeline = build_pipeline(
    model="qwen3:14b",
    policy=policy,
    k=5,
    reviewer=my_reviewer,
    tool_risk_metadata=md,
    system_prompt="You are a banking assistant.",
    client=client,
)
```

Here, `my_reviewer` must be an implementation of the project's Reviewer interface.

### Running on AgentDojo

Use the built pipeline with an AgentDojo task suite. Refer to the [AgentDojo documentation](https://agentdojo.spylab.ai/) for task execution and benchmark APIs.

The evaluation should record task utility and security results separately.

## R1: Safety Gate

### Tool Risk Metadata

Edit `src/tool_risk_metadata.yaml` to configure tool risk levels and default decisions.

Example:

```yaml
tools:
  send_money:
    risk: high
    category: execute
    default_decision: ESCALATE
```

The risk-based policy currently follows these rules:

| Configuration | Decision |
|---|---|
| `default_decision: AUTO_APPROVE` | Automatically approve |
| `default_decision: AUTO_DENY` | Automatically deny |
| `risk: low` | Automatically approve |
| `risk: medium` | Escalate for review |
| `risk: high` | Escalate for review |

Explicit `default_decision` values take precedence over the risk-based default rules.

### Escalation Budget

The `k` parameter in `build_pipeline` controls the available human-review budget.

- Each escalation that actually invokes the Reviewer consumes one budget unit.
- When the budget is exhausted, further escalation requests are denied.
- The budget is reset at the start of each task.

The budget limits the number of reviewer consultations and helps evaluate the trade-off between security and review workload.

## R5: Evaluation, Cost, and Analysis

R5 adds utilities for recording experiments and analyzing the performance of different safety policies.

### 1. Experiment Logger

File: `src/experiment_logger.py`

The `ExperimentLogger` writes structured records in JSONL format.

It supports two types of records:

- **Gate decisions:** policy, initial budget, task ID, tool name, decision, approval status, remaining budget, and rationale.
- **Episode results:** task status, task completion, and whether an unauthorized tool call was observed.

Each record includes a run ID and timestamp. Logs are appended to files rather than overwriting previous records.

Output files:

- `gate_decisions.jsonl`
- `episode_results.jsonl`

These logs are intended to support later metric calculation and experiment analysis.

### 2. Cost Tracker

File: `src/cost_tracker.py`

The `CostTracker` records model-call usage and cost information for three components:

- `agent`
- `policy`
- `reviewer`

Supported fields include model name, provider, input tokens, output tokens, reported cost, call status, request ID, and usage source.

It also provides a summary of calls, token usage, known costs, and calls with unknown costs.

Unknown costs are tracked separately rather than silently treated as zero. Actual cost analysis depends on connecting the tracker to real model calls and collecting available usage information.

Output file:

- `cost_calls.jsonl`

### 3. Evaluation Metrics

File: `src/metrics.py`

The `calculate_metrics()` function processes episode records, gate decision records, and optional cost records.

The current metric design includes:

**Task Completion Rate at Budget k (TCR@k)**

Measures the proportion of tasks completed safely under a given escalation budget.

\[
\mathrm{TCR@k}
=
\frac{\text{Safely completed tasks}}
{\text{Tasks with known safety labels}}
\]

A task should not be counted as safely completed merely because it finished. Security labels must also be considered. Tasks with unknown safety labels should not automatically be treated as safe.

**Human-in-the-Loop Workload (HITL Load)**

Measures the human-review workload associated with successful tasks. The analysis can report total reviewer consultations and average consultations per successful task.

\[
\mathrm{HITL\ Load}
=
\frac{\text{Reviewer consultations on successful tasks}}
{\text{Number of successful tasks}}
\]

The exact counting convention should remain consistent across all compared policies.

**Cost Analysis**

The cost summary separates known costs by component:

\[
C_{\mathrm{total}}
=
C_{\mathrm{agent}}
+
C_{\mathrm{policy}}
+
C_{\mathrm{reviewer}}
\]

Unknown cost records are reported separately so that incomplete usage information does not distort the comparison.

### 4. Experiment Runner

File: `src/experiment_runner.py`

The current Experiment Runner generates a CSV experiment manifest using the AgentDojo task suite, policy labels, and escalation-budget values.

Default configuration:

| Parameter | Value |
|---|---|
| Benchmark version | `v1.2.2` |
| Task suite | `banking` |
| Policy labels | `full_approve`, `full_escalate`, `risk_based` |
| Escalation budgets | `0`, `1`, `3`, `5` |

The current configuration generates 1,728 planned combinations:

\[
16 \times 9 \times 3 \times 4 = 1728
\]

Generate the experiment plan from the repository root:

```bash
python -m src.experiment_runner
```

Output:

`runs/r5_experiment_plan.csv`

The CSV contains the benchmark version, suite, user-task ID, injection-task ID, policy label, escalation budget, status, and error field.

**Important:** The current runner creates an experiment plan only. It does not yet execute all benchmark tasks or establish completed experimental results. The policy labels in the plan must also be connected to the corresponding implementations before running the final evaluation.

## Experiment Design

The planned evaluation compares three policy configurations:

| Policy | Purpose |
|---|---|
| Full-approve | Permissive baseline |
| Full-escalate | Human-review-oriented baseline |
| Risk-based | Risk-aware approval policy |

The experiment varies the escalation budget `k` across `0`, `1`, `3`, and `5`.

The main analysis goals are to:

1. Compare safe task completion rates across policies.
2. Measure the effect of review budget on task completion and security.
3. Quantify human-review workload.
4. Compare agent, policy, and reviewer costs.
5. Examine the trade-off between restrictive approval and permissive approval.

AgentDojo utility and security outcomes should be collected and analyzed separately. Final conclusions should be based on actual benchmark runs rather than the experiment manifest alone.

## Project Structure

```text
6101-agent-harness/
├── src/
│   ├── types.py                  # Core types and interfaces
│   ├── gate.py                   # Tool approval gate
│   ├── budget.py                 # Per-task budget reset
│   ├── policy.py                 # Legacy policy interface
│   ├── reviewer.py               # Legacy reviewer interface
│   ├── risk_based_policy.py      # Risk-based policy
│   ├── tool_risk.py              # Risk metadata loader
│   ├── tool_risk_metadata.yaml   # Tool risk configuration
│   ├── pipeline.py               # Pipeline factory
│   ├── experiment_logger.py      # R5: Experiment logging
│   ├── cost_tracker.py           # R5: Model-call cost tracking
│   ├── metrics.py                # R5: Evaluation metrics
│   └── experiment_runner.py      # R5: Experiment plan generation
├── tests/                        # Unit and integration tests
├── runs/
│   └── r5_experiment_plan.csv    # Generated experiment manifest
├── configs/                      # Experiment configurations
├── requirements.txt
├── conftest.py
└── README.md
```

The file list reflects the current development structure and may change as the project evolves.

## Current Development Status

| Component | Status |
|---|---|
| R1 safety gate | Basic implementation available |
| R1 risk-based policy | Basic implementation available |
| R1 escalation budget | Basic implementation available |
| R5 experiment logger | Basic implementation available; integration pending |
| R5 cost tracker | Basic implementation available; real-call integration pending |
| R5 metrics | Basic implementation available; validation with benchmark results pending |
| R5 experiment runner | Experiment manifest generation implemented |
| End-to-end AgentDojo execution | Pending |
| Automated retries and resume support | Pending |
| Final result tables and plots | Pending |
| Full comparative analysis | Pending |

Some module-level tests have been run during development. Their results do not imply that the complete R5 evaluation pipeline or all benchmark experiments have passed.

## Changelog

### v0.2.0 — October 2026

- Added the initial safety gate implementation.
- Added `RiskBasedPolicy` with YAML-based tool risk metadata.
- Added the pipeline factory and per-task budget reset.
- Added the initial R5 experiment logger.
- Added model-call cost tracking utilities.
- Added evaluation metric calculation utilities.
- Added experiment manifest generation and CSV export.

The original R1 changelog reported 23 passing unit tests. Confirm the current total by running the test suite against the latest repository version.

## Future Work

- Integrate R5 logging with the live safety gate and AgentDojo execution.
- Record utility, security, reviewer usage, and model costs during real experiments.
- Implement experiment execution, retries, and resumable runs.
- Validate metric definitions against the project specification.
- Generate comparison tables and plots for all policy and budget settings.
- Document reproducible experimental settings and limitations.

## Acknowledgements

This project uses the AgentDojo framework for evaluating tool-using language model agents under utility and security tasks.
