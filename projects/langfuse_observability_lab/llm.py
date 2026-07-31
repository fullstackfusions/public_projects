"""Chat model factory. Defaults to a local Ollama model (free, no API key);
set LLM_PROVIDER=openai to swap in a hosted model for real cost tracking.
"""
import os


def get_chat_model(temperature: float = 0.0):
    provider = os.getenv("LLM_PROVIDER", "ollama").lower()
    model = os.getenv("LLM_MODEL", "qwen2.5:7b")

    if provider == "openai":
        from langchain_openai import ChatOpenAI

        return ChatOpenAI(model=model, temperature=temperature)

    if provider == "ollama":
        from langchain_ollama import ChatOllama

        return ChatOllama(
            model=model,
            temperature=temperature,
            base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        )

    raise ValueError(f"Unknown LLM_PROVIDER '{provider}'. Use 'ollama' or 'openai'.")
