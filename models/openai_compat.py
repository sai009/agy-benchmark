"""
models/openai_compat.py — Any OpenAI-compatible endpoint (Ollama, vLLM, LM Studio, OpenAI).

Usage examples:
  # Ollama (local)
  OllamaAdapter(model="llama3.2:latest", base_url="http://localhost:11434/v1")

  # vLLM (local)
  OllamaAdapter(model="mistralai/Mistral-7B-Instruct-v0.3", base_url="http://localhost:8000/v1")

  # OpenAI (cloud)
  OllamaAdapter(model="gpt-4o", api_key=os.environ["OPENAI_API_KEY"])
"""
from __future__ import annotations
import os
import time
from .base import ModelAdapter, RunResult


class OpenAICompatAdapter(ModelAdapter):

    def __init__(
        self,
        model: str,
        base_url: str = "http://localhost:11434/v1",
        api_key: str = "ollama",       # Ollama ignores this; set real key for OpenAI
        label: str | None = None,
    ):
        self.model = model
        self._base_url = base_url
        self._api_key = api_key
        self.model_id = f"openai-compat/{model}"
        self.model_label = label or f"{model} (OpenAI-compat @ {base_url})"

    async def run(self, task_id: str, task_label: str, prompt: str, max_tokens: int) -> RunResult:
        result = self._make_result(task_id, task_label, prompt)

        try:
            import openai  # pip install openai
            client = openai.OpenAI(base_url=self._base_url, api_key=self._api_key)

            t0 = time.perf_counter()
            resp = client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
            )
            elapsed = time.perf_counter() - t0

            result.response = resp.choices[0].message.content.strip()
            result.latency_s = round(elapsed, 2)
            result.tokens_out = resp.usage.completion_tokens if resp.usage else len(result.response.split())
            result.tok_per_sec = round(result.tokens_out / elapsed, 1) if elapsed > 0 else 0
        except ImportError:
            result.error = "openai package not installed: pip install openai"
        except Exception as e:
            result.error = str(e)

        return result
