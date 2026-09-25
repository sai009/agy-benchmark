"""
models/base.py — Abstract base class for all model adapters.

To add a new model:
  1. Subclass ModelAdapter
  2. Implement async run()
  3. Register in bench.py MODEL_REGISTRY
"""
from __future__ import annotations
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class RunResult:
    model_id: str
    model_label: str
    task: str
    task_label: str
    prompt: str
    response: str = ""
    latency_s: float = 0.0
    tokens_out: int = 0
    tok_per_sec: float = 0.0
    error: Optional[str] = None
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "model_id": self.model_id,
            "model_label": self.model_label,
            "task": self.task,
            "task_label": self.task_label,
            "prompt": self.prompt,
            "response": self.response,
            "latency_s": self.latency_s,
            "tokens_out": self.tokens_out,
            "tok_per_sec": self.tok_per_sec,
            "error": self.error,
            "metadata": self.metadata,
        }


class ModelAdapter(ABC):
    """
    Subclass this for each model. One instance is reused across all tasks
    in a benchmark run, so expensive setup (model load, auth) happens once.
    """

    #: Short identifier used in CLI --models flag and result JSON
    model_id: str = ""
    #: Human-readable label for reports
    model_label: str = ""

    @abstractmethod
    async def run(self, task_id: str, task_label: str, prompt: str, max_tokens: int) -> RunResult:
        """Run a single task. Must be async. Should not raise — catch and set result.error."""
        ...

    async def setup(self) -> None:
        """Optional: called once before the first task. Override for lazy init."""
        pass

    async def teardown(self) -> None:
        """Optional: called after the last task. Override for cleanup."""
        pass

    def _make_result(self, task_id: str, task_label: str, prompt: str) -> RunResult:
        return RunResult(
            model_id=self.model_id,
            model_label=self.model_label,
            task=task_id,
            task_label=task_label,
            prompt=prompt,
        )
