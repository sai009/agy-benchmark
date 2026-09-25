"""
tests/test_scoring.py — Tests for report generation logic (no model calls).
"""
import sys, os, json, tempfile
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from scripts.generate_report import render_markdown


SAMPLE_PAYLOAD = {
    "timestamp": "2026-09-25T10:00:00",
    "results": [
        {
            "model_id": "gemma4-26b-litert",
            "model_label": "Gemma 4 26B (LiteRT/local)",
            "task": "factual",
            "task_label": "Factual Recall",
            "prompt": "What is 2+2?",
            "response": "4",
            "latency_s": 10.0,
            "tokens_out": 1,
            "tok_per_sec": 0.1,
            "error": None,
            "metadata": {"verdict": "manual"},
        },
        {
            "model_id": "claude-sonnet-4-6",
            "model_label": "Claude Sonnet 4.6 (cloud)",
            "task": "factual",
            "task_label": "Factual Recall",
            "prompt": "What is 2+2?",
            "response": "4",
            "latency_s": 1.5,
            "tokens_out": 1,
            "tok_per_sec": 0.67,
            "error": None,
            "metadata": {"verdict": "manual"},
        },
    ],
}


class TestMarkdownReport:
    def test_renders_without_error(self):
        md = render_markdown(SAMPLE_PAYLOAD)
        assert isinstance(md, str) and len(md) > 100

    def test_contains_title(self):
        md = render_markdown(SAMPLE_PAYLOAD)
        assert "LLM Benchmark Report" in md

    def test_contains_timestamp(self):
        md = render_markdown(SAMPLE_PAYLOAD)
        assert "2026-09-25" in md

    def test_contains_both_model_labels(self):
        md = render_markdown(SAMPLE_PAYLOAD)
        assert "Gemma 4 26B" in md
        assert "Claude Sonnet 4.6" in md

    def test_contains_task_label(self):
        md = render_markdown(SAMPLE_PAYLOAD)
        assert "Factual Recall" in md

    def test_contains_responses(self):
        md = render_markdown(SAMPLE_PAYLOAD)
        assert "4" in md  # both models responded "4"

    def test_aggregate_stats_section_present(self):
        md = render_markdown(SAMPLE_PAYLOAD)
        assert "Aggregate Statistics" in md

    def test_error_result_handled(self):
        payload = dict(SAMPLE_PAYLOAD)
        payload["results"] = [
            {**SAMPLE_PAYLOAD["results"][0], "error": "Connection refused", "response": ""},
        ]
        md = render_markdown(payload)
        assert "Connection refused" in md or "error" in md.lower()

    def test_multiple_tasks(self):
        payload = {
            "timestamp": "2026-09-25T10:00:00",
            "results": SAMPLE_PAYLOAD["results"] + [
                {
                    **SAMPLE_PAYLOAD["results"][0],
                    "task": "reasoning",
                    "task_label": "Logical Reasoning",
                    "response": "0.05",
                    "metadata": {"verdict": "pass"},
                }
            ],
        }
        md = render_markdown(payload)
        assert "Factual Recall" in md
        assert "Logical Reasoning" in md
