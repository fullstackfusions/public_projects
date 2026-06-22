What was built: multi_agent_coding/
The system: 4 specialized agents in a LangGraph loop, running Gemma3:12b fully locally.


PLANNER  →  CODER  →  EVALUATOR  →  ✅ END
                           ↓ fail, < 3 iterations
                       DEBUGGER  →  EVALUATOR  →  loop
The harness (not the model) runs pytest, writes files, and routes between agents. The model only produces text.

Setup

cd projects/agent_harness/multi_agent_coding
pip install -e .

# Pull Gemma3:12b (one-time, ~8GB)
ollama pull gemma3:12b
Running — the 3 demo proofs

# Demo 1: Email validator (good first run — tests edge cases well)
python run.py --demo 1

# Demo 2: URL slug generator
python run.py --demo 2

# Demo 3: Run-length encoding + decoding (round-trip requirement)
python run.py --demo 3

# Your own task (you provide a test file)
python run.py --task "implement X" --tests /path/to/test.py

# Use a different model if Gemma tool-calling is shaky
python run.py --demo 1 --model qwen3:8b
python run.py --demo 1 --model llama3.1:8b
What the proof looks like
Each run writes proofs/proof_YYYYMMDD_HHMMSS.md capturing:

Section	What's in it
Header	Model name, result, iterations, total duration
Task	Exact requirement passed to agents
🗺️ PLANNER	Full plan + edge cases the model identified
💻 CODER	Lines written, timing
🧪 EVALUATOR	Pass/fail per test, raw pytest output
🔧 DEBUGGER	What was patched, which iteration
Final Solution	The working solution.py
Verdict	Pass/fail + proof it was local, no API
This document is the shareable artifact — open it in any Markdown viewer.
