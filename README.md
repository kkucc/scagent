#Stem Cell Agent

![Architecture](https://img.shields.io/badge/Architecture-Elegant_Objects-blue)

this thing is like a stem cell idea
agent gets a signal about domain and grows small tools it needs
we check code in sandbox first then run it

not a universal agent
it becomes specific for the task
for other tasks start a new stem agent

# docs 

- docs.md - how to run, config

- write-up.md - !!!!!

## Before and after Comparison

Evaluation task: fetch API data and verify nested key
```python benchmark.py --backend local --runs 5```

```bash

baseline:local         | runs 5   | pass 2/5  40% | mean 8.74s | total 43.69s
stem+safeguards:local  | runs 5   | pass 4/5  80% | mean 7.18s | total 35.91s

```
Baseline generic agent
Fail modes: syntax errors, undefined variables, missing imports

Stem agent with safeguards and AST
all syntax and import errors were caught and auto-fixed inside the sandbox during evolution
```bash
colima start
docker context use colima
docker info
# export OPENAI_API_KEY="..
# colima stop
```

```bash python benchmark.py --backend docker --runs 5 --timeout 40 --attempts 9```
```bash
=== benchmark result ===
baseline:docker        | runs 5   | pass 5/5 100% | mean 13.44s | total 67.22s
stem+safeguards:docker | runs 5   | pass 5/5 100% | mean 12.02s | total 60.10s
========================
note: docker needs daemon running; local has no net isolation
```
## Quick start

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pytest tests/ -v

export OPENAI_API_KEY="ur-key" 

python main.py

# benchmark
python benchmark.py --backend local --runs 5
```


## Configuration

Edit config/settings.yaml
- llm.model_name
- agent_settings.evolution_attempts
- workspace.backend: local or docker
- workspace.timeout_seconds: applies to validation and final run

optional(implementing)
 run with workspace.backend set to docker for stronger isolation
 
local is acceptable for quick dev but does not isolate the network

## What to expect

- the agent evolves DNA from the domain signal
- DNA contains tools as a dictionary of function names to source code
- AST security allows only whitelisted imports and forbids relative imports
- safeguards validate that all declared tool names exist
- the agent asks LLM for a tiny run script and executes tools under timeout
- stdout and stderr are captured and reported

## Security notes

- Docker workspace
  - per call network policy, bridge when requires_network true, none otherwise
  - read only bind mount by default
- Local workspace
  - no network isolation, for dev only
- AST validator
  - strict whitelist for imports
  - relative imports strictly forbidden
