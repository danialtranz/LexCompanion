# LangGraph Base

## Overview

This repository is a starting point for **LangGraph**-based agents. It is organized around a **multi-agent style layout** under `deepagent/` and currently contains a **minimal Q&A agent graph** used as a skeleton for local experimentation.

The implemented graph is **linear** (a single node) and **does not call an LLM or any retrieval system**; it echoes the user input with a fixed prefix so you can verify wiring and execution.

> **Note:** `pyproject.toml` declares a console script (`langgraph-base` → `legal_agent.cli:main`) and `langgraph.json` points the `base_agent` graph at `legal_agent.agent:graph`. Those modules are **not present** in this tree as of the current layout. The runnable graph lives under `deepagent/multiagent/q&a_agent/`. Resolving that mismatch (package name, `src/` layout, and graph entry path) is part of making `uv sync`, `uv run langgraph-base`, and `uv run langgraph dev` work end-to-end.

## Features

- **LangGraph `StateGraph`** compiled to a `graph` object, exported from the Q&A agent package.
- **Typed graph state** (`user_input`, `response`) via `TypedDict`.
- **CLI-style entry** in `deepagent/multiagent/q&a_agent/cli.py`: loads environment from `.env` (via `python-dotenv`) and invokes the graph once with a sample input.
- **`langgraph.json`** for LangGraph CLI / deployment-style configuration (graph id `base_agent`; env file `./.env`).
- **Optional HTTP surface placeholder**: `api/app.py` exists but is **empty** (no API is implemented there yet).

## Architecture

- **Graph builder:** `deepagent/multiagent/q&a_agent/agent.py` builds a `StateGraph(AgentState)`, adds one node, and wires `START → generate_response → END`.
- **Node logic:** `deepagent/multiagent/q&a_agent/nodes.py` implements `generate_response`, which normalizes `user_input` and sets `response` to a deterministic string derived from that input.
- **State:** `deepagent/multiagent/q&a_agent/state.py` defines `AgentState`.
- **Package surface:** `deepagent/multiagent/q&a_agent/__init__.py` re-exports `graph`.

There is **no** separate retriever, memory, or router module in the repository; routing is only the fixed edges above.

## Project Structure

```
langgraph-base/
├── api/
│   └── app.py                 # Empty placeholder (no implemented server)
├── deepagent/
│   └── multiagent/
│       └── q&a_agent/         # Q&A agent package (folder name includes "&")
│           ├── __init__.py
│           ├── agent.py       # Graph definition and compile
│           ├── cli.py         # load_dotenv + sample invoke
│           ├── nodes.py       # Node implementations
│           └── state.py       # AgentState TypedDict
├── .env.example               # OPENAI_API_KEY template (optional for current graph)
├── .gitignore
├── langgraph.json             # LangGraph app config (graphs, env path)
├── pyproject.toml             # Dependencies and metadata
├── README.md
└── uv.lock
```

## Current use case: Legal Q&A (Vietnam law)

The **folder and module naming** (`deepagent`, `multiagent`, `q&a_agent`) reflects an intended direction toward **domain-specific Q&A** (for example, Vietnam legal questions). The **code that exists today** does not encode legal sources, jurisdiction, or prompts—it is a **minimal graph** suitable as a scaffold before adding retrieval, tools, and legal-specific behavior.

## Roadmap

- **Document-based Q&A** — ingest and index legal (or other) documents; answer grounded in sources.
- **Advanced reasoning over legal docs** — multi-step reasoning, citations, and structured outputs over retrieved material.
- **Legal document generation** — contracts, forms, and similar artifacts with guardrails and templates.

## Tech stack

Inferred from `pyproject.toml` and imports in the agent code:

| Area                        | Technology                                                                                                          |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| Language                    | Python **3.12+** (`requires-python` in `pyproject.toml`)                                                            |
| Orchestration               | **LangGraph** (`langgraph.graph.StateGraph`, `START` / `END`)                                                       |
| LLM integrations (declared) | **langchain**, **langchain-openai** (present as dependencies; **not used** by the current `generate_response` node) |
| CLI / dev server            | **langgraph-cli** with `inmem` extra                                                                                |
| Configuration               | **python-dotenv** (used in `cli.py`)                                                                                |
| Packaging / lockfile        | **uv** (`uv.lock`; build backend `uv_build` per `pyproject.toml`)                                                   |

## Getting started

### Prerequisites

- Python 3.12 or newer
- [uv](https://github.com/astral-sh/uv) (recommended) or another way to install the dependencies listed in `pyproject.toml`

### Environment

Copy the example env file and set variables as needed:

```bash
cp .env.example .env
```

`OPENAI_API_KEY` is listed for future LLM use; the **current** demo graph does not require it.

### Install dependencies

If `uv sync` fails because the project expects a different package layout (for example `src/langgraph_base/`), install the runtime libraries you need directly, for example:

```bash
uv venv .venv
source .venv/bin/activate
uv pip install "langchain>=1.2.15" "langchain-openai>=1.1.12" "langgraph>=1.1.6" "python-dotenv>=1.2.2"
```

Adjust versions to match `pyproject.toml` / `uv.lock` as you align packaging.

### Run the sample graph (current layout)

From the repository root, with `deepagent/multiagent` on `PYTHONPATH` and the project virtualenv’s Python:

```bash
source .venv/bin/activate
cd deepagent/multiagent
PYTHONPATH=. python -c "import importlib; importlib.import_module('q&a_agent.cli').main()"
```

Expected output:

```text
LangGraph base says: Hello LangGraph
```

### LangGraph CLI

When `langgraph.json`’s graph path matches an importable module that exposes `graph`, you can use:

```bash
uv run langgraph dev
```

Until the `legal_agent` / packaging layout matches the code on disk, this may not load successfully without configuration changes.

## Contributing

## License
generated by cursor
