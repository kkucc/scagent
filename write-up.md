# The stem agent

The project started with an undestanding of a simple biological metaphor, a stem cell does not know what it will become. It just listens to the env, gets a signal, and transforms. If the transformation goes wrong, biological safeguards kill the cell before it becomes a problem. 

And understanding whar differ it form MCP servers,
most software agents do not work this way. They are built as massive monoliths:
- they have every tool pre-installed
- they have gigantic system prompts trying to cover every edge case
- they are extremely fragile when pushed off the happy path

the goal was to build a system that starts empty. The agent receives a domain signal, asks a language model for the tools it needs, validates those tools, and only then starts working. 

This sounds nice in theory, but in practice, generative models are chaotic text generators, you know , last linear layer applies a softmax function, which is basically a probability distribution, so there are some randomness init. They do not care about syntax or security, architecture had to treat the llm as a hostile entity. 

the process required execution layers:
- a signal triggers a differentiation phase
- the model writes python code for specific tools
- a safeguard layer intercepts this code
- the code is parsed, compiled, and executed in a sandbox
- if anything fails, the error is caught and sent back as a mutation signal
- this loop repeats until the code is completely stable

# the markdown hallucination

the first version was very naive( check test_api/). the prompt told the language model to act as a pure code generation engine. The instructions were: output only valid python code, and do not output markdown formatting.

Model completely ignored the instructions, it generated a perfect python function, but wrapped it in standard markdown fences. the validation layer took this exact string and passed it to the python compiler. 

```text
Traceback (most recent call last):
  File "<string>", line 1
    ```python
    ^
SyntaxError: invalid syntax
```

This was  frustrating,
prompt engineering is essentially just asking a machine nicely to do its job, it is not a reliable engineering control.

Fix had to be implemented at the data sanitization layer. System now takes the raw string and runs brute force replace operations to strip out the backticks and the word python, only after this string manipulation does the code go to the compiler.

!**you cannot prompt your way out of a formatting issue, you have to write code to clean it up**!

# infinite loop and timeout incident

Once the syntax errors were handled, the model started writing valid python. The domain signal used for testing was application programming interface QA. The agent had to fetch a json payload and verify the contents.

The model wrote a tool to fetch the data, remote server was slow during one test, model had anticipated this and wrote a while loop that kept checking the server status. The loop had no exit condition if the server stopped responding entirely. 

So I'd call it a sequence of failure:
-- the validation sandbox ran the code
-- the terminal just sat there
=> nothing happened
-- the main thread was completely blocked
-- the entire evaluation suite had to be manually killed

Untrusted code cannot be allowed to run indefinitely. A hard timeout had to be enforced at the operating system level, a yaml configuration was added to dictate a global timeout. Local workspace now uses the subprocess module to run the generated code, passing the timeout directly to the call. 

if execution exceeds the limit, the operating system sends a kill signal to the child process.

```text
subprocess.TimeoutExpired: Command '['python', '/tmp/workspace/tool.py']' timed out after 5 seconds
```

the system catches this exception, extracts the error, and feeds it back to the language model. The model received this mutation signal and rewrote the python tool with a proper timeout parameter. !**The agent fixed its own hanging code because the architecture forced it to.**!

# sandbox and import problem

Executing dynamically generated abstract syntax trees on a host machine is a massive security vulnerability, during one debugging session, the model decided it needed to check the local file system. It generated an import os statement and local workspace had zero isolation.

So i figured architecture needed a real sandbox, so a docker workspace class was created. Execution flow is now heavily restricted, it writes the code to a temporary file, mounts that directory into an alpine linux container as a read-only volume, and executes the script inside.

This provided system isolation, but catching bad imports at runtime inside the container was inefficient. 

The system needed to block dangerous code before execution. 

So an abstract syntax tree parser was built, as regular expressions are useless for analyzing python code. The system uses the built-in ast module and a custom node visitor. The visitor enforces such rules:
- it traverses every single node in the tree
- it checks against a hardcoded whitelist: requests, json, urllib, re, time, datetime
- if a base module is not in the set, it raises a custom security error
- it checks the level attribute of import nodes to block relative imports

```text
SecurityError: import 'os' not allowed. 
SecurityError: relative imports are strictly forbidden in generated dna.
```

if the code violates these rules, the docker container is never started, the model gets the security error instantly and has to rewrite the tools.

# tool graphs and lying local namespaces

The initial design only allowed the agent to generate a single function. This scaled terribly, the dna data class was rewritten so the tools field became a dictionary, keys are function names, values are the source code.

This broke the safeguard logic. Compilation only checks for syntax, and model frequently hallucinates function names, it will define a key called fetch_data in the json, but the actual python code will say def get_api_data. 

Safeguard evolution class was updated to handle this dictionary. It concatenates all values into one script and executes it in a restricted namespace, then loops over every key in the original tools dictionary and checks if that key exists in the local variables.

if a key is missing, it means the model lied. 

```text
WARNING: Safeguard validation failed.
Compiler Error:
Traceback (most recent call last):
  File "<string>", line 20, in <module>
NameError: Function 'api_quality_assurance_test' was not found.
Triggering genetic mutation.
```

this exact traceback is passed back to the model, so it eliminated all mismatch errors during final execution.

# explicit network contracts

The docker sandbox introduced a new problem, the agent sometimes needs an external api, and sometimes it just parses local text and should be isolated from the internet. 

Trying to guess network requirements by looking for the string http in the code leads to false positives. the system prompt was updated to force a contract. the language model must include a requires_network boolean in its json response.

docker workspace reads this boolean, if true, it appends network bridge, if false, it appends network none. 

If model writes a requests call but sets the network flag to false, the container boots without an interface. Script crashes with a connection error, safeguard catches this, sends it back, and model learns to align its intent with its environment.

# the caching trap (or: incident macos)

The evolution process is slow and costs money, an attempt was made to optimize this by caching stable dna objects based on the domain signal. 

This completely destroyed the success rate of the agent, it was a classic cascading failure:
- the safeguard only checked if the code compiled and if function names existed
- it did not run unit tests on the logic(there is no ci/cd pipeline here, its in real time)
- the model generated a tool that passed syntax checks but had a runtime bug
- the safeguard cached the broken dna
- on the next run, the safeguard instantly returned the broken dna
- the script crashed again, and again, and again

Pass rate hit zero percent, average execution time looked incredibly fast, but only because it was fetching broken code from memory and crashing instantly, caching generated code without running integration tests is a massive footgun. 
Bad code gets permanently locked in, cache logic had to be ripped out.

# final benchmark

An evaluation script was written to compare a baseline generic agent against the stem agent architecture, to stop the model from generating top-level network requests that crashed the offline validation layer, the system prompt was completely rewritten: strict structure rules were added,so model was explicitly forbidden from writing anything outside of function definitions. 

this created a fascinating and counter-intuitive result in the next benchmark:

```text
=== benchmark result ===
baseline:docker        | runs 5   | pass 5/5 100% | mean 10.13s | total 50.63s
stem+safeguards:docker | runs 5   | pass 4/5  80% | mean  9.68s | total 48.40s
========================
```

Restrictive prompt acted like a straitjacket, i guess baseline had so little room to hallucinate that it succeeded on the first try every time, but the stem agent dropped to eighty percent. 

This happened because the stem agent is a stochastic system, on one of its runs, it encountered a random logic failure, the safeguard caught it, but the agent failed to fix the bug within the configured limit of seven attempts. 

I can call it a lesson, so strict prompt proved to be the most powerful first line of defense, but the safeguard is still strictly necessary because statistical anomalies will always happen. 

A final adjustment was made to the configuration, the mutation attempts were bumped from seven to nine, and the global timeout was increased to 40 seconds.

the final docker benchmark was run:

```text
=== benchmark result ===
baseline:docker        | runs 5   | pass 5/5 100% | mean 13.44s | total 67.22s
stem+safeguards:docker | runs 5   | pass 5/5 100% | mean 12.02s | total 60.10s
========================
note: docker needs daemon running; local has no net isolation
```

Given enough attempts to self-correct its one stochastic failure, the stem agent matched the perfect score and actually executed faster on average!!!

# dna architecture

- system_prompt: short guide for planning and runner generation
- tools: dict name -> function source, each value defines exactly one top-level function, name must match the key
- requires_network: bool. true only if external internet is needed (not localhost)

# security rules

- whitelist imports only: requests, json, urllib, re, time, datetime
- forbid relative imports (node.level > 0)
- forbid top-level execution: no code at import time, no if __name__ == "__main__", no global side effects
- ast-validated before any container run
- runner prelude injected automatically: import json, time, datetime, re, requests
- docker workspace: per-call network none/bridge, read-only mount

# commands

```bash
export OPENAI_API_KEY="ur_key"
# docker. you can change config to local
# build runner image with requests preinstalled
docker build -t stem-runner:py311 - <<'EOF'
FROM python:3.11-slim
RUN pip install --no-cache-dir -q requests
EOF

# switch to docker backend and set generous timeout
sed -i '' 's/backend: "local"/backend: "docker"/' config/settings.yaml
sed -i '' 's/timeout_seconds: .*/timeout_seconds: 30/' config/settings.yaml

#the thing
python main.py

# benchmark
python benchmark.py --backend docker --runs 5 --timeout 30 --attempts 7
```
the containerized runner image is pinned to python 3.11 slim, colima was used to provide the docker daemon on macos.


<!--## reproducibility notes-->

<!--- containerized runner image pinned to python:3.11-slim with requests
- colima used to provide docker daemon on !!macOS!!
- strict prompt (CRITICAL RULES + STRUCTURE RULES) reduces variance
- safeguarded retries surface and repair errors, stochastic runs may still vary
- keep same config (timeouts, attempts) and image to compare runs-->

# limitations and future work

- stdlib + requests only, no heavy data science packages supported yet, no numpy/pandas/torch, no bs4/lxml
- local backend has no network isolation
- add cpu/memory limits in docker for tighter isolation
- persist dna cache only after passing an integration step (health marker)
- optional dag executor with retries for multi-step chains
implement a directed acyclic graph executor for multi-step tool chains(so not only QA but other also)
- publish validated tools as service endpoints

- current domain hardcoded demo path is API QA (easy to validate and measure)
- multi-domain plan:
  - allow passing multiple domain signals in one run (async fan-out)
  - spin separate specialization per signal (isolate workspaces)
  - run safeguarded evolution per domain in parallel with bounded attempts
  - collect per-domain stdout/stderr and status, aggregate in one report
  - minimal API: stem_cell.differentiate for each signal, then act(/task)
- examples to try next:
  - "Web Service Health Checks" (status 200 checks)
  - "Security Header Audit" (HSTS, CSP presence)
  - "Data QA" (json tallies and thresholds)
  - "Content Validation" (simple substring rules)


In final words, I'd say some flashy things:
Optimal architecture is not a choice between strict prompt engineering and runtime validation. It is a synthesis of both, lock the model down as hard as possible with the system prompt to prevent basic errors, and use the docker sandbox and mutation loop as a safety net to catch the edge cases when the model inevitably tries to break out.
You do not trust the generated code, you compile it, you isolate it, you time it out, and you force it to fix itself.
