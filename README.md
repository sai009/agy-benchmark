# agy-benchmark

A reusable benchmark framework for comparing local LLM agents (via the **Google Antigravity SDK + LiteRT-LM**) against cloud models (Claude, GPT, Gemini). Designed to track quality and performance across model updates and new model additions.

## Structure

```
agy-benchmark/
├── bench.py              # Main benchmark runner (CLI)
├── models/               # Model adapter plugins
│   ├── base.py           # ModelAdapter ABC
│   ├── gemma_litert.py   # Gemma 4 via LiteRT + Antigravity SDK
│   └── claude_hermes.py  # Claude via Hermes OAuth
├── tests/                # Pytest unit tests for the framework
│   ├── test_tasks.py
│   └── test_scoring.py
├── scripts/
│   └── generate_report.py  # MD + PDF report generator
├── results/              # JSON result files (auto-saved, git-tracked)
└── reports/              # Generated MD + PDF reports
```

## Quick Start

```bash
# Install deps
pip install google-antigravity litert-lm reportlab pypdf

# Run full benchmark (all tasks, all configured models)
python bench.py

# Subset of tasks
python bench.py --tasks factual reasoning code

# Specific models only
python bench.py --models gemma claude

# Generate report from existing results
python scripts/generate_report.py results/latest.json

# Run tests
pytest tests/ -v
```

## Adding a New Model

1. Create `models/your_model.py` subclassing `ModelAdapter` from `models/base.py`
2. Implement `async def run(prompt, max_tokens) -> RunResult`
3. Register it in `bench.py`'s `MODEL_REGISTRY`

## Adding a New Task

Add an entry to the `TASKS` dict in `bench.py`:

```python
"my_task": {
    "label": "My Task",
    "prompt": "...",
    "max_tokens": 300,
    "scoring": "exact"   # exact | contains | manual
}
```

## Results

Results are saved as timestamped JSON in `results/` and as MD + PDF reports in `reports/`. Each run appends to `results/history.jsonl` for trend tracking.

## Requirements

- Python 3.10+
- `google-antigravity >= 0.1.16`
- `litert-lm >= 0.17.0`
- `reportlab >= 4.0`
- `pypdf >= 4.0`
- Model: `~/.litert-lm/models/gemma4-26b/model.litertlm` (Gemma 4 26B, ~15.8GB)
- Hardware: ≥24GB VRAM or unified memory recommended for 26B model
