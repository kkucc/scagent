# stem agent
## overview

- idea: like stem cell, agent grows tools it needs
- gives domain signal (exp. like API QA)
- LLM returns DNA: 
  - system_prompt (what do i behave like?)
  - tools: dict[name -> python function source]
  - requires_network: bool (true/false)
- we validate code in sandbox
- if ok, ask LLM for small run script and execute
- result is stdout/stderr + success flag

## flow

1) differentiate
   - send domain signal to evolution
   - LLM returns JSON dna with tools and flags
2) safeguards
   - glue all tools into one file
   - run minimal check: each function name exists
   - on error, feed back details to LLM and retry (few times)
3) specialize
   - ask LLM to write tiny script that uses those tools
4) execute
   - run combined code (tools + script) in workspace
   - timeout always enforced
   - capture stdout/stderr

## map

- main.py
  - wires config, picks workspace (local/docker), runs sample task
- stem_core/interfaces.py
  - contracts (Task, Result, Dna, Workspace, etc)
- stem_core/evolution.py
  - PromptDrivenEvolution (LLM DNA build)
  - SecurityASTVisitor (import whitelist, no relative imports)
- stem_core/safeguards.py
  - SafeguardedEvolution (retries + validate all tools)
  - small dna cache by domain
- stem_core/agents.py
  - StemCell (orchestrates)
  - SpecializedCell (plans + runs)
- stem_core/workspace.py
  - LocalWorkspace (subprocess, no real net isolation)
- stem_core/docker_workspace.py
  - DockerWorkspace (container run, network switch by flag)
- config/settings.yaml
  - llm, attempts, workspace backend + timeout
- tests/*
  - unit tests for workspace, safeguards, ast security

## install & run

prereqs:
- python 3.10+
- internet (for LLM and API test)
- OpenAI API key in env (OPENAI_API_KEY)
- docker installed if you want container isolation (implementing...)

steps:
- create venv
- pip install -r requirements.txt
- export OPENAI_API_KEY="ur-key"
- edit config/settings.yaml if needed
- run: python main.py
- see logs for evolution/validation/execution

tests:
- run: pytest ( pytest tests/ -v)

## config

file: config/settings.yaml

- llm.model_name
  - name of model (default "gpt-4o")
- agent_settings.evolution_attempts
  - how many mutation retries on failure (default 3)
- workspace.backend
  - "local" for subprocess, "docker" for container
  - docker recommended for security
- workspace.timeout_seconds
  - hard limit for code run (validation + final)
  - increase if your task is slow

env:
- OPENAI_API_KEY must be set and export OPENAI_API_KEY="..."

## how i see functional requirements would've been

- evolve dna from domain signal
- dna has tools: dict[name -> function code string]
- validate all tool names exist after import/exec
- ast whitelist imports only: requests, json, urllib, time, datetime, re
- forbid relative imports (from .foo etc)
- execute in workspace with timeout
- capture stdout/stderr, return success flag
- optional docker isolation, network off by default
- network on only if dna.requires_network == true

### non-functional requirements

- safety first (deny dangerous imports, sandbox)
- predictable time (timeout)
- logs readable (info level ok)
- easy to swap workspaces (protocol)
- minimal deps (stdlib + requests inside sandbox)
- portability (mac/linux, docker optional)

###  security notes

- ast security:
  - only whitelisted imports allowed
  - relative imports strictly forbidden
- docker mode:
  - by call, sets `--network none` or bridge via `requires_network`
  - read-only bind mount by default
- local mode:
  - does not isolate network (warning in logs)
- timeout:
  - stops infinite loops / hangs
- threat model basics:
  - do not trust LLM code, always validate + sandbox
  - prefer docker in CI/prod
  - never pass secrets into generated code

## errors/logs

- error: OPENAI_API_KEY missing
  - export key in shell, restart terminal
- error: Docker not found
  - install docker, ensure in PATH, set backend: docker
- error: ConnectionError / network blocked
  - dna.requires_network false → docker runs with --network none
  - fix upstream by letting LLM return requires_network: true
  - or switch backend to local (less safe) for quick test
- error: SyntaxError in validation
  - LLM tool code invalid, safeguards will retry
  - if repeats, lower task complexity or tune prompt
- error: Functions not found: X, Y
  - tool names in dna.keys must match def names in code
  - safeguards feed this back to LLM to fix
- error: timeout exceeded
  - increase workspace.timeout_seconds in config
  - or simplify task/tool logic
- nothing happens / empty logs
  - run with python -u main.py for unbuffered stdout
  - check that dependencies installed

<!--## faq i guess

- why docker
  - stronger isolation, control net, ro fs
- why ast whitelist
  - text filters easy to bypass, ast is robust
- why dict of tools not single func
  - real tasks need several steps, better composition
- can i add more allowed imports
  - yes, extend whitelist in evolution security visitor
- can i cache dna forever
  - basic in-memory now; for prod use sqlite/json store-->

## checklist

- [ ] python 3.10+
- [ ] pip install -r requirements.txt
- [ ] export OPENAI_API_KEY
- [ ] config workspace.backend: docker or local
- [ ] python main.py
- [ ] see logs: evolution → safeguards → specialized run
