"""
models/gemma_litert.py — Gemma 4 26B via Google Antigravity SDK + LiteRT-LM.

Requires:
  pip install google-antigravity litert-lm
  litert-lm import --from-huggingface-repo=litert-community/gemma-4-26B-A4B-it-litert-lm \\
    gemma-4-26B-A4B-it-gpu.litertlm gemma4-26b
"""
from __future__ import annotations
import os
import time
from .base import ModelAdapter, RunResult

DEFAULT_MODEL_PATH = os.path.expanduser("~/.litert-lm/models/gemma4-26b/model.litertlm")


class GemmaLiteRTAdapter(ModelAdapter):
    model_id = "gemma4-26b-litert"
    model_label = "Gemma 4 26B (LiteRT/local)"

    def __init__(self, model_path: str = DEFAULT_MODEL_PATH):
        self.model_path = model_path

    async def run(self, task_id: str, task_label: str, prompt: str, max_tokens: int) -> RunResult:
        result = self._make_result(task_id, task_label, prompt)
        result.metadata["model_path"] = self.model_path

        if not os.path.exists(self.model_path):
            result.error = f"Model not found: {self.model_path}. Run: litert-lm import ..."
            return result

        try:
            from google.antigravity import Agent, LiteRTAgentConfig

            config = LiteRTAgentConfig(model_path=self.model_path).lightweight()
            t0 = time.perf_counter()
            async with Agent(config) as agent:
                response_obj = await agent.chat(prompt)
                tokens = []
                async for tok in response_obj:
                    tokens.append(tok)
            elapsed = time.perf_counter() - t0

            result.response = "".join(tokens).strip()
            result.latency_s = round(elapsed, 2)
            result.tokens_out = len(result.response.split())
            result.tok_per_sec = round(result.tokens_out / elapsed, 1) if elapsed > 0 else 0
        except Exception as e:
            result.error = str(e)

        return result
