OLLAMA_MODEL = "qwen2.5:7b"
OLLAMA_BASE_URL = "http://localhost:11434"

# Commands used in the benchmark — chosen because RTK has dedicated filters for all of them
BENCHMARK_COMMANDS = [
    "git log --oneline -20",
    "git status",
    "git log --format='%h %an %ae %s %ad' -15",
    "git branch -v",
    "git log --stat -2",
    "ls -la",
]

# Task used for the agent demo
DEMO_TASK = (
    "You are a dev-loop assistant analyzing a git repository. "
    "Run the following commands and summarize what you find: "
    "1) git log --oneline -10  "
    "2) git status  "
    "3) git log --stat -2  "
    "Provide a brief summary of recent activity."
)
