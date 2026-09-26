"""
models/claude_hermes.py — Claude via Hermes OAuth credential pool.

Uses the Hermes auth store (no raw API key needed) — works on any machine
where `hermes auth` has been run for the anthropic provider.
"""
from __future__ import annotations
import os
import sys
import time
from pathlib import Path
from .base import ModelAdapter, RunResult

# Hermes install path — override with HERMES_AGENT_PATH env var if your install differs
HERMES_AGENT_PATH = os.environ.get(
    "HERMES_AGENT_PATH",
    os.path.expanduser("~/.hermes/hermes-agent"),
)
HERMES_HOME = os.environ.get(
    "HERMES_HOME",
    os.path.expanduser("~/.hermes"),
)

# Models available via this adapter
CLAUDE_MODELS = {
    "claude-sonnet-4-6": "Claude Sonnet 4.6 (cloud)",
    "claude-opus-4-5":   "Claude Opus 4.5 (cloud)",
    "claude-haiku-4":    "Claude Haiku 4 (cloud)",
}


def _get_anthropic_client():
    """Build an anthropic.Anthropic client using the Hermes OAuth token."""
    # Use append (not insert) to avoid shadowing stdlib/site-packages (CWE-426).
    # Validate against the exact resolved default path, not just any dir under ~.
    _expected = Path(os.path.expanduser("~/.hermes/hermes-agent")).resolve()
    _candidate = Path(HERMES_AGENT_PATH).resolve()
    if (os.path.isdir(_candidate)
            and _candidate == _expected
            and str(_candidate) not in sys.path):
        sys.path.append(str(_candidate))

    os.environ.setdefault("HERMES_HOME", HERMES_HOME)

    from hermes_cli.auth import read_credential_pool
    import anthropic

    pool = read_credential_pool("anthropic")
    if not pool:
        raise RuntimeError("No Anthropic credentials in Hermes auth store. Run: hermes auth")

    entry = pool[0]
    return anthropic.Anthropic(
        api_key=entry["access_token"],
        base_url=entry.get("base_url", "https://api.anthropic.com"),
        default_headers={"anthropic-beta": "oauth-2023-05-11"},
    )


class ClaudeHermesAdapter(ModelAdapter):

    def __init__(self, model: str = "claude-sonnet-4-6"):
        if model not in CLAUDE_MODELS:
            raise ValueError(f"Unknown model {model!r}. Available: {list(CLAUDE_MODELS)}")
        self.model = model
        self.model_id = model
        self.model_label = CLAUDE_MODELS[model]
        self._client = None

    async def setup(self) -> None:
        self._client = _get_anthropic_client()

    async def run(self, task_id: str, task_label: str, prompt: str, max_tokens: int) -> RunResult:
        result = self._make_result(task_id, task_label, prompt)
        result.metadata["api_model"] = self.model

        try:
            client = self._client or _get_anthropic_client()
            t0 = time.perf_counter()
            msg = client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            elapsed = time.perf_counter() - t0

            result.response = msg.content[0].text.strip()
            result.latency_s = round(elapsed, 2)
            result.tokens_out = msg.usage.output_tokens
            result.tok_per_sec = round(result.tokens_out / elapsed, 1) if elapsed > 0 else 0
        except Exception as e:
            result.error = str(e)

        return result
