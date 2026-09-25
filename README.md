# agy-benchmark

**An open benchmark framework for evaluating local LLM agents via the Google Antigravity SDK against cloud models.**

This project was created by **Sai Kesavamatham** to explore two areas of active personal interest: the practical viability of hybrid agentic architectures — where cloud and local models collaborate within a single workflow — and the security implications of running agentic workloads on-device vs. in the cloud. The benchmark is a starting point for understanding where local execution genuinely holds up, where it falls short, and what the privacy and security tradeoffs look like in practice.

Developed and run entirely using [Claude Sonnet 4.6](https://www.anthropic.com/claude) via the [Hermes Agent](https://github.com/NousResearch/hermes-agent) platform. Licensed under [Apache 2.0](LICENSE). See LICENSE for full disclaimer and no-liability terms.

---

## What Google Released This Week

On **September 23, 2026**, Google announced that the [Antigravity SDK](https://antigravity.google/product/antigravity-sdk/) now supports **fully offline, local agentic workflows** — a significant step toward on-device AI that needs no API key, no cloud connectivity, and sends zero data off your machine.

> *"Today, we're announcing that the Antigravity SDK supports local workflows across a wide range of local models and execution options, featuring initial support for Gemma 4 26B A4B using Google AI Edge's LiteRT."*
>
> — [Google Developers Blog, Sept 23 2026](https://developers.googleblog.com/introducing-support-for-local-ai-models-in-the-antigravity-sdk/)

### Why this matters — in Google's own words

> **Cost efficiency:** Execute local agentic workflows without API costs or rate limits.
>
> **Privacy:** Keep your code and requests entirely on your local machine, ideal for developers navigating strict data privacy requirements or compliance-restricted corporate environments.
>
> **Offline resiliency:** Execute your agentic workflows seamlessly, even in environments where a consistent or stable internet connection is unavailable.
>
> **Hybrid workflows:** Combine token-efficient local processes with cloud-based ones to maximize efficiency while retaining access to larger, more powerful models when needed.

### The hybrid pattern Google demonstrated

In the featured demo, a cloud architect model (Gemini 3.8 Flash) plans and decomposes a task using only filenames and descriptions — spending just **95 cloud tokens** — while a local swarm of Gemma 4 26B instances handles all execution on-device. In a recorded run auditing three vulnerable code modules:

- **97.2% of all tokens (3,322)** ran locally and offline
- Zero source code was ever sent to a cloud endpoint
- Fully verified, green patches were produced entirely on-device

### Key links

| Resource | URL |
|---|---|
| Google Developers Blog announcement | https://developers.googleblog.com/introducing-support-for-local-ai-models-in-the-antigravity-sdk/ |
| Official local models documentation | https://antigravity.google/docs/sdk/local-models/ |
| Antigravity SDK GitHub | https://github.com/google-antigravity/antigravity-sdk-python |
| Antigravity SDK on PyPI | https://pypi.org/project/google-antigravity/ |
| Gemma 4 on HuggingFace (LiteRT format) | https://huggingface.co/litert-community/gemma-4-26B-A4B-it-litert-lm |
| LiteRT-LM on PyPI | https://pypi.org/project/litert-lm/ |
| LiteRT overview | https://developers.google.com/edge/litert-lm/overview |
| Hybrid Gauntlet example project | https://goo.gle/47cKYyV |

---

## Architecture: Two Distinct Layers

A common point of confusion worth stating explicitly: **the Hermes `agy-sdk` profile uses Claude Sonnet 4.6 as its chat model, not Gemma 4.** This is intentional.

| Layer | Model | Role |
|-------|-------|------|
| Hermes chat (`agy-sdk` profile) | Claude Sonnet 4.6 | Research, tooling, scripting, repo management |
| Benchmark inference | Gemma 4 26B A4B via LiteRT | Called directly inside `bench.py` / `agy_sample.py` |

Gemma 4 runs when the benchmark scripts invoke `LiteRTAgentConfig` \u2014 not through Hermes's model routing. If you want Hermes chat itself to run on Gemma 4, start `litert-lm serve --port 9379` and point the profile at `http://localhost:9379/v1` (see the README in the Hermes `agy-sdk` profile for the exact commands).

---

## What This Benchmark Does

`agy-benchmark` was built the same week as the Google release to put these claims to the test. It runs **identical prompts** through:

- **Gemma 4 26B A4B** — running 100% locally via `LiteRTAgentConfig` on-device (no network, no API key)
- **Claude Sonnet 4.6** — running via the Anthropic API as the cloud baseline

...and captures latency, throughput, and response quality side by side.

The framework is designed to be **picked up by anyone** — on any machine, with any model — to rerun, extend, and compare results over time as models and runtimes evolve.

---

## Install from Scratch

Tested on macOS (Apple Silicon). Linux with NVIDIA GPU is also supported by LiteRT-LM.

**Hardware requirement:** ≥ 24 GB VRAM or unified memory for the Gemma 4 26B model.
**Disk requirement:** ~17 GB free for the model checkpoint.

### 1. Clone the repo

```bash
git clone https://github.com/agy-benchmark/agy-benchmark.git
cd agy-benchmark
```

### 2. Create a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
```

### 3. Install Python dependencies

```bash
pip install google-antigravity litert-lm reportlab pypdf pytest
```

> **macOS SSL note:** If `litert-lm import` fails with an SSL certificate error:
> ```bash
> pip install certifi
> export SSL_CERT_FILE=$(python3 -c "import certifi; print(certifi.where())")
> ```

### 4. Download the Gemma 4 26B model (~16.8 GB, one-time)

```bash
litert-lm import \
  --from-huggingface-repo=litert-community/gemma-4-26B-A4B-it-litert-lm \
  gemma-4-26B-A4B-it-gpu.litertlm \
  gemma4-26b
```

This registers the model at `~/.litert-lm/models/gemma4-26b/model.litertlm` automatically.

### 5. (Optional) Configure a cloud model

To benchmark against Claude, export your Anthropic API key:

```bash
export ANTHROPIC_API_KEY="<your-anthropic-api-key-here>"
```

To use Ollama, vLLM, or LM Studio instead, see [Adding a New Model](#adding-a-new-model).

---

## Run the Benchmark

```bash
# Run all 7 tasks across all configured models
python bench.py

# Subset of tasks
python bench.py --tasks factual reasoning code

# Gemma only (no cloud API needed)
python bench.py --models gemma

# Custom output path
python bench.py --out results/my_run_$(date +%Y%m%d).json
```

Results are saved as timestamped JSON in `results/` and a markdown + PDF report is auto-generated in `reports/`.

---

## What v1 Tests (Baseline: September 25, 2026)

The baseline run in `results/baseline_20260925.json` covers **5 tasks** across **2 models**:

| Task ID | Category | Prompt summary | Scoring |
|---------|----------|---------------|---------|
| `factual` | Factual Recall | 4 short-answer CS/geography questions | Manual |
| `reasoning` | Logical Reasoning | Bat-and-ball CRT problem (step-by-step) | Contains `"0.05"` |
| `code` | Code Generation | `find_duplicates(lst)` with docstring + 3 asserts | Contains `"find_duplicates"` |
| `instruction` | Instruction Following | List exactly 5 sort algorithms, names only, no extras | Manual |
| `creative` | Creative Writing | Haiku about local AI, strict 5-7-5 | Manual |

**Models in v1:**

| Model | Runtime | API key needed | Network needed |
|-------|---------|---------------|----------------|
| Gemma 4 26B A4B | LiteRT-LM 0.17.1 + google-antigravity 0.1.18 | No | No |
| Claude Sonnet 4.6 | Anthropic API | Yes | Yes |

**Hardware used for baseline:**
Apple M4 Max · 128 GB unified memory · Metal GPU backend (auto-detected by LiteRT-LM)

**Researcher:** Sai Kesavamatham

**Key findings from v1:**
- Gemma 4 26B tied or nearly tied Claude on factual recall, logical reasoning, and instruction following
- Latency: Gemma averaged ~39s/response vs ~5s for Claude — primarily cold-start per `Agent()` context; a persistent session could be significantly faster. We have not tested this theory.
- Claude had a marginal edge on code generation and creative writing (syllable compliance)
- Full results and per-response analysis: [`reports/baseline_20260925.md`](reports/baseline_20260925.md) · [`reports/baseline_20260925.pdf`](reports/baseline_20260925.pdf)

---

## Compare Runs Over Time

When a new SDK version ships or a new model becomes available, run the benchmark again and compare:

```bash
# Run a new benchmark
python bench.py --out results/run_20261015.json

# Compare baseline vs new run
python scripts/compare.py \
  results/baseline_20260925.json \
  results/run_20261015.json \
  --out reports/comparison_sept_oct.md

# Print to terminal
python scripts/compare.py results/baseline_20260925.json results/run_20261015.json --md

# Compare three or more runs
python scripts/compare.py results/A.json results/B.json results/C.json --md
```

The comparison script produces side-by-side latency and throughput tables with delta percentages and direction indicators (↑/↓ with ✓/✗ for better/worse).

---

## Generate Reports

```bash
# Generate MD + PDF from any result file
python scripts/generate_report.py results/baseline_20260925.json

# Custom output directory
python scripts/generate_report.py results/baseline_20260925.json --out-dir reports/
```

---

## Run Tests

```bash
pytest tests/ -v
```

23 tests covering task registry validation, scoring logic, and report rendering.

---

## Adding a New Model

1. Create `models/your_model.py` subclassing `ModelAdapter` from `models/base.py`
2. Implement `async def run(task_id, task_label, prompt, max_tokens) -> RunResult`
3. Register it in `bench.py`'s `build_model_registry()`

**Ollama (already scaffolded in `models/openai_compat.py`):**

```python
from models.openai_compat import OpenAICompatAdapter

registry["llama3"] = OpenAICompatAdapter(
    model="llama3.2:latest",
    base_url="http://localhost:11434/v1",
    label="Llama 3.2 (Ollama/local)",
)
```

**OpenAI:**

```python
registry["gpt4o"] = OpenAICompatAdapter(
    model="gpt-4o",
    base_url="https://api.openai.com/v1",
    api_key=os.environ["OPENAI_API_KEY"],
    label="GPT-4o (cloud)",
)
```

---

## Adding a New Task

Add an entry to the `TASKS` dict in `bench.py`:

```python
"my_task": {
    "label": "My Task Label",
    "prompt": "Your prompt here...",
    "max_tokens": 300,
    "scoring": "contains",   # "contains" | "exact" | "manual"
    "expected": "keyword",   # required for "contains" and "exact"
},
```

---

## Repository Structure

```
agy-benchmark/
├── bench.py                     # Main runner — task registry, model registry, scoring, CLI
├── models/
│   ├── base.py                  # ModelAdapter ABC + RunResult dataclass
│   ├── gemma_litert.py          # Gemma 4 via LiteRT + Antigravity SDK (local/offline)
│   ├── claude_hermes.py         # Claude via Hermes OAuth
│   └── openai_compat.py         # Any OpenAI-compatible endpoint (Ollama, vLLM, LM Studio, OpenAI)
├── scripts/
│   ├── generate_report.py       # MD + styled PDF report generator
│   └── compare.py               # Side-by-side comparison of two or more result files
├── results/
│   ├── baseline_20260925.json   # v1 baseline: Gemma 4 26B vs Claude Sonnet 4.6
│   └── history.jsonl            # Rolling index of all runs (auto-appended)
├── reports/
│   ├── baseline_20260925.md     # Generated markdown report
│   └── baseline_20260925.pdf    # Generated PDF report
├── tests/
│   ├── test_tasks.py            # Task registry + scoring logic tests
│   └── test_scoring.py          # Report rendering tests
├── .github/workflows/ci.yml     # GitHub Actions: runs tests on every push
└── LICENSE                      # Apache 2.0 + no-liability disclaimer + AI development disclosure
```

---

## What's Left for Future Versions

- **More tasks:** multi-turn conversation, tool use, structured JSON output, long-context retrieval
- **Automated scoring:** LLM-as-judge for manual tasks
- **Persistent warm sessions:** benchmark Gemma throughput with model loaded once (eliminates cold-start penalty)
- **More models:** Ollama (Llama 3.2, Phi-4, Qwen), vLLM, LM Studio, Gemini API, GPT-4o
- **Hardware matrix:** NVIDIA CUDA, M1/M2/M3/M4 Metal comparison
- **Trend dashboard:** HTML chart from `results/history.jsonl`
- **LiteRT speculative decoding:** enable `enable_speculative_decoding=True` and measure speedup

---

## License

Apache 2.0 — see [LICENSE](LICENSE).

**This software is provided "as is" with no warranties. The authors accept no liability for benchmark results, decisions made based on them, or any outcomes from use of this software. Benchmark results are point-in-time measurements and should not be used to draw general conclusions about model quality.**

This project is not affiliated with, endorsed by, or acting on behalf of Google LLC, Anthropic PBC, or any other third-party model provider referenced herein. All third-party trademarks belong to their respective owners.

---

## Development Disclosure

Created by **Sai Kesavamatham** as part of personal research into hybrid agentic architectures, local model security, and the practical boundaries between cloud and on-device AI execution. All source code, scripts, tests, reports, and documentation were developed with the assistance of **Claude Sonnet 4.6** (Anthropic) via the **Hermes Agent** platform. All outputs were reviewed before publication.
