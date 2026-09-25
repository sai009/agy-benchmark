"""
tests/test_tasks.py — Unit tests for task definitions and scoring logic.
Run: pytest tests/ -v
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from bench import TASKS, score_result
from models.base import RunResult


def make_result(response: str, error=None, model_id="test", task="factual") -> RunResult:
    return RunResult(
        model_id=model_id,
        model_label="Test Model",
        task=task,
        task_label="Test Task",
        prompt="test prompt",
        response=response,
        error=error,
    )


class TestTaskRegistry:
    def test_all_tasks_have_required_keys(self):
        for tid, task in TASKS.items():
            assert "label" in task,      f"{tid}: missing 'label'"
            assert "prompt" in task,     f"{tid}: missing 'prompt'"
            assert "max_tokens" in task, f"{tid}: missing 'max_tokens'"
            assert "scoring" in task,    f"{tid}: missing 'scoring'"

    def test_scoring_values_valid(self):
        valid = {"manual", "contains", "exact"}
        for tid, task in TASKS.items():
            assert task["scoring"] in valid, f"{tid}: invalid scoring '{task['scoring']}'"

    def test_contains_tasks_have_expected(self):
        for tid, task in TASKS.items():
            if task["scoring"] == "contains":
                assert "expected" in task, f"{tid}: 'contains' scoring requires 'expected'"

    def test_prompts_are_nonempty_strings(self):
        for tid, task in TASKS.items():
            assert isinstance(task["prompt"], str) and task["prompt"].strip(), \
                f"{tid}: prompt must be a non-empty string"

    def test_max_tokens_positive(self):
        for tid, task in TASKS.items():
            assert isinstance(task["max_tokens"], int) and task["max_tokens"] > 0, \
                f"{tid}: max_tokens must be a positive int"


class TestScoring:
    def test_manual_always_returns_manual(self):
        task = {"scoring": "manual"}
        r = make_result("anything")
        assert score_result(r, task) == "manual"

    def test_contains_pass(self):
        task = {"scoring": "contains", "expected": "0.05"}
        r = make_result("The ball costs $0.05.")
        assert score_result(r, task) == "pass"

    def test_contains_fail(self):
        task = {"scoring": "contains", "expected": "0.05"}
        r = make_result("The ball costs $0.10.")
        assert score_result(r, task) == "fail"

    def test_contains_case_insensitive(self):
        task = {"scoring": "contains", "expected": "find_duplicates"}
        r = make_result("def Find_Duplicates(lst):")
        assert score_result(r, task) == "pass"

    def test_exact_pass(self):
        task = {"scoring": "exact", "expected": "42"}
        r = make_result("42")
        assert score_result(r, task) == "pass"

    def test_exact_fail(self):
        task = {"scoring": "exact", "expected": "42"}
        r = make_result("43")
        assert score_result(r, task) == "fail"

    def test_error_result_always_error(self):
        for scoring in ("manual", "contains", "exact"):
            task = {"scoring": scoring, "expected": "x"}
            r = make_result("", error="Connection refused")
            assert score_result(r, task) == "error"

    def test_reasoning_task_scoring(self):
        task = TASKS["reasoning"]
        assert score_result(make_result("The ball costs $0.05"), task) == "pass"
        assert score_result(make_result("The ball costs $0.10"), task) == "fail"

    def test_code_task_scoring(self):
        task = TASKS["code"]
        assert score_result(make_result("def find_duplicates(lst): pass"), task) == "pass"
        assert score_result(make_result("def wrong_name(lst): pass"), task) == "fail"
