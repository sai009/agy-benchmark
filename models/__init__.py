# models/__init__.py
from .base import ModelAdapter, RunResult
from .gemma_litert import GemmaLiteRTAdapter
from .claude_hermes import ClaudeHermesAdapter
from .openai_compat import OpenAICompatAdapter

__all__ = [
    "ModelAdapter",
    "RunResult",
    "GemmaLiteRTAdapter",
    "ClaudeHermesAdapter",
    "OpenAICompatAdapter",
]
