#!/usr/bin/env python3
"""
bench.py — Extensible LLM benchmark runner.

Usage:
  python bench.py                                    # all tasks, all models
  python bench.py --tasks factual reasoning code     # subset of tasks
  python bench.py --models gemma claude              # subset of models
  python bench.py --out results/my_run.json          # custom output path
  python bench.py --no-report                        # skip report generation
"""
from __future__ import annotations

import argparse
import asyncio
import datetime
import json
import os
import sys
from pathlib import Path

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, ROOT)

from models.base import RunResult
from models.gemma_litert import GemmaLiteRTAdapter
from models.claude_hermes import ClaudeHermesAdapter
from models.openai_compat import OpenAICompatAdapter

# ── Task registry ─────────────────────────────────────────────────────────────
# Add new tasks here. scoring: "manual" means human review needed.

TASKS: dict[str, dict] = {
    "factual": {
        "label": "Factual Recall",
        "prompt": (
            "Answer concisely (1-2 sentences each):\n"
            "1. What is the time complexity of quicksort in the average case?\n"
            "2. What does HTTP status 429 mean?\n"
            "3. What year was Python first released?\n"
            "4. What is the capital of Kazakhstan?"
        ),
        "max_tokens": 200,
        "scoring": "manual",
    },
    "reasoning": {
        "label": "Logical Reasoning",
        "prompt": (
            "A bat and a ball cost $1.10 in total. The bat costs $1.00 more than the ball. "
            "How much does the ball cost? Show your reasoning step by step."
        ),
        "max_tokens": 300,
        "scoring": "contains",
        "expected": "0.05",
    },
    "code": {
        "label": "Code Generation",
        "prompt": (
            "Write a Python function `find_duplicates(lst)` that returns a list of all "
            "elements that appear more than once, in the order they first appear. "
            "Include a docstring and 3 assert statements that test it."
        ),
        "max_tokens": 400,
        "scoring": "contains",
        "expected": "find_duplicates",
    },
    "instruction": {
        "label": "Instruction Following",
        "prompt": (
            "List exactly 5 sorting algorithms. "
            "Format as a numbered list. "
            "For each: name only, no description. "
            "Do not include any other text before or after the list."
        ),
        "max_tokens": 100,
        "scoring": "manual",
    },
    "creative": {
        "label": "Creative Writing",
        "prompt": (
            "Write a haiku about running AI models locally on your own hardware. "
            "Follow the 5-7-5 syllable structure strictly."
        ),
        "max_tokens": 80,
        "scoring": "manual",
    },
    "math": {
        "label": "Math",
        "prompt": (
            "Solve step by step: "
            "A train travels 120 km at 60 km/h, then 180 km at 90 km/h. "
            "What is the average speed for the whole journey?"
        ),
        "max_tokens": 200,
        "scoring": "contains",
        "expected": "72",
    },
    "summarization": {
        "label": "Summarization",
        "prompt": (
            "Summarize the following in exactly 2 sentences:\n\n"
            "Large language models (LLMs) are neural networks trained on vast corpora of text "
            "using self-supervised objectives. They learn to predict the next token, which "
            "implicitly requires understanding syntax, semantics, world knowledge, and reasoning. "
            "Modern LLMs like GPT-4, Claude, and Gemini are deployed via APIs and power "
            "applications ranging from code completion to scientific research assistance. "
            "A key challenge is alignment — ensuring model outputs are helpful, harmless, and honest."
        ),
        "max_tokens": 120,
        "scoring": "manual",
    },
}

# ── Model registry ─────────────────────────────────────────────────────────────
# Add new model adapters here.

def build_model_registry() -> dict:
    registry = {}

    # Gemma 4 26B via LiteRT (local, offline)
    registry["gemma"] = GemmaLiteRTAdapter()

    # Claude Sonnet 4.6 via Hermes OAuth
    try:
        registry["claude"] = ClaudeHermesAdapter(model="claude-sonnet-4-6")
    except Exception:
        pass  # No Hermes credentials — skipped, not fatal

    # Ollama (uncomment and configure to enable)
    # registry["ollama-llama3"] = OpenAICompatAdapter(
    #     model="llama3.2:latest",
    #     base_url="http://localhost:11434/v1",
    #     label="Llama 3.2 (Ollama/local)",
    # )

    return registry


# ── Scoring ────────────────────────────────────────────────────────────────────

def score_result(result: RunResult, task: dict) -> str:
    """Returns 'pass', 'fail', or 'manual'."""
    if result.error:
        return "error"
    strategy = task.get("scoring", "manual")
    if strategy == "manual":
        return "manual"
    if strategy == "contains":
        expected = task.get("expected", "")
        return "pass" if expected.lower() in result.response.lower() else "fail"
    if strategy == "exact":
        return "pass" if result.response.strip() == task.get("expected", "").strip() else "fail"
    return "manual"


# ── Runner ────────────────────────────────────────────────────────────────────

async def run_benchmark(
    task_ids: list[str],
    model_ids: list[str],
    model_registry: dict,
) -> list[RunResult]:
    results: list[RunResult] = []

    for task_id in task_ids:
        task = TASKS[task_id]
        print(f"\n{'='*62}")
        print(f"  Task: {task['label']}")
        print(f"{'='*62}")

        for model_id in model_ids:
            adapter = model_registry[model_id]
            print(f"  [{adapter.model_label}] ...", flush=True)
            await adapter.setup()
            r = await adapter.run(
                task_id=task_id,
                task_label=task["label"],
                prompt=task["prompt"],
                max_tokens=task["max_tokens"],
            )
            verdict = score_result(r, task)
            if r.error:
                print(f"  ✗ Error: {r.error}")
            else:
                flag = {"pass": "✓", "fail": "✗", "manual": "~", "error": "✗"}[verdict]
                print(f"  {flag} {r.latency_s}s · {r.tokens_out} tok · {r.tok_per_sec} tok/s  [{verdict}]")
                print(f"    {r.response[:110].replace(chr(10),' ')}{'…' if len(r.response)>110 else ''}")
            r.metadata["verdict"] = verdict
            results.append(r)

    return results


# ── Persistence ────────────────────────────────────────────────────────────────

def save_results(results: list[RunResult], out_path: str) -> None:
    ts = datetime.datetime.now().isoformat(timespec="seconds")
    payload = {
        "timestamp": ts,
        "results": [r.to_dict() for r in results],
    }
    os.makedirs(os.path.dirname(out_path) or ".", exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)

    # Append to rolling history
    history_path = os.path.join(ROOT, "results", "history.jsonl")
    os.makedirs(os.path.dirname(history_path), exist_ok=True)
    with open(history_path, "a") as f:
        f.write(json.dumps({"timestamp": ts, "file": out_path, "n": len(results)}) + "\n")

    print(f"\nResults saved → {out_path}")


# ── Main ───────────────────────────────────────────────────────────────────────

async def main() -> None:
    parser = argparse.ArgumentParser(description="agy-benchmark: LLM benchmark runner")
    parser.add_argument("--tasks", nargs="+", choices=list(TASKS), default=list(TASKS))
    parser.add_argument("--models", nargs="+", default=None)
    parser.add_argument("--out", default=None, help="Output JSON path (default: results/<timestamp>.json)")
    parser.add_argument("--no-report", action="store_true", help="Skip report generation")
    args = parser.parse_args()

    model_registry = build_model_registry()
    available = list(model_registry)
    model_ids = args.models or available
    unknown = [m for m in model_ids if m not in model_registry]
    if unknown:
        print(f"Unknown models: {unknown}. Available: {available}")
        sys.exit(1)

    ts_str = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = args.out or os.path.join(ROOT, "results", f"{ts_str}.json")
    # Resolve and restrict to within project root only (CWE-22: path traversal fix).
    # startswith() is vulnerable to prefix confusion (/home/user vs /home/user_evil).
    # Path.is_relative_to() does an exact ancestry check.
    out_path = str(Path(out_path).resolve())
    if not Path(out_path).is_relative_to(Path(ROOT).resolve()):
        print(f"Error: --out path must be within the project directory: {out_path}")
        sys.exit(1)

    print(f"Models : {[model_registry[m].model_label for m in model_ids]}")
    print(f"Tasks  : {args.tasks}")
    print(f"Output : {out_path}")

    results = await run_benchmark(args.tasks, model_ids, model_registry)
    save_results(results, out_path)

    if not args.no_report:
        report_script = os.path.join(ROOT, "scripts", "generate_report.py")
        import subprocess
        result = subprocess.run([sys.executable, report_script, out_path], check=True)


if __name__ == "__main__":
    asyncio.run(main())
