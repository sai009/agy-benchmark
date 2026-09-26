#!/usr/bin/env python3
"""
scripts/compare.py — Compare two or more benchmark result files side by side.

Useful for tracking regressions or improvements across model updates,
SDK version bumps, or hardware changes.

Usage:
  # Compare two runs
  python scripts/compare.py results/baseline_20260925.json results/run_20261015.json

  # Compare all files in results/
  python scripts/compare.py results/*.json

  # Output as markdown table
  python scripts/compare.py results/baseline_20260925.json results/run_20261015.json --md

  # Save comparison report
  python scripts/compare.py results/A.json results/B.json --out reports/comparison.md
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def load(path: str) -> dict:
    with open(path) as f:
        data = json.load(f)
    # Normalise: bare list → wrapped
    if isinstance(data, list):
        data = {"timestamp": os.path.basename(path), "results": data}
    data.setdefault("timestamp", os.path.basename(path))
    data["_file"] = os.path.basename(path)
    return data


def avg(values: list[float]) -> float:
    return round(sum(values) / len(values), 2) if values else 0.0


def delta_str(new: float, old: float, lower_is_better: bool = True) -> str:
    """Return a human-readable delta with direction arrow."""
    if old == 0:
        return "—"
    diff = new - old
    pct = diff / old * 100
    arrow = ("↓" if diff < 0 else "↑") if lower_is_better else ("↑" if diff > 0 else "↓")
    good = (diff < 0 and lower_is_better) or (diff > 0 and not lower_is_better)
    sign = "+" if diff > 0 else ""
    tag = "✓" if good else "✗"
    return f"{sign}{pct:.1f}% {arrow} {tag}"


def build_model_task_index(payload: dict) -> dict:
    """Returns {(model_id, task): result_dict}"""
    index = {}
    for r in payload.get("results", []):
        key = (r["model_id"], r["task"])
        index[key] = r
    return index


def compare(payloads: list[dict]) -> str:
    """Build a markdown comparison table across all payloads."""
    # Collect all unique (model_id, task) pairs preserving order
    all_keys: list[tuple] = []
    seen: set = set()
    for p in payloads:
        for r in p.get("results", []):
            k = (r["model_id"], r["task"])
            if k not in seen:
                all_keys.append(k)
                seen.add(k)

    indices = [build_model_task_index(p) for p in payloads]
    labels = [f"{p['_file']} ({p['timestamp'][:10]})" for p in payloads]

    lines = [
        "# Benchmark Comparison",
        "",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        "",
        "Files compared:",
    ]
    for i, lbl in enumerate(labels):
        lines.append(f"  {i+1}. `{lbl}`")
    lines += ["", "---", ""]

    # ── Per-task latency table ──
    lines.append("## Latency (seconds) by Model × Task")
    lines.append("")

    header = "| Model | Task |" + "".join(f" {lbl} |" for lbl in labels)
    if len(payloads) >= 2:
        header += " Δ (last vs first) |"
    sep = "|-------|------|" + " ---: |" * len(labels)
    if len(payloads) >= 2:
        sep += " --- |"
    lines += [header, sep]

    for model_id, task in all_keys:
        row_results = [idx.get((model_id, task)) for idx in indices]
        first = next((r for r in row_results if r and not r.get("error")), None)
        label = (first or row_results[0] or {}).get("model_label", model_id)
        task_label = (first or row_results[0] or {}).get("task_label", task)

        row = f"| {label} | {task_label} |"
        latencies = []
        for r in row_results:
            if r and not r.get("error"):
                row += f" {r['latency_s']}s |"
                latencies.append(r["latency_s"])
            else:
                row += " error |"
                latencies.append(None)

        if len(payloads) >= 2:
            valid = [l for l in latencies if l is not None]
            if len(valid) >= 2:
                row += f" {delta_str(valid[-1], valid[0], lower_is_better=True)} |"
            else:
                row += " — |"

        lines.append(row)

    lines += ["", "---", ""]

    # ── Throughput table ──
    lines.append("## Throughput (tokens/second) by Model × Task")
    lines.append("")
    header2 = "| Model | Task |" + "".join(f" {lbl} |" for lbl in labels)
    if len(payloads) >= 2:
        header2 += " Δ (last vs first) |"
    sep2 = "|-------|------|" + " ---: |" * len(labels)
    if len(payloads) >= 2:
        sep2 += " --- |"
    lines += [header2, sep2]

    for model_id, task in all_keys:
        row_results = [idx.get((model_id, task)) for idx in indices]
        first = next((r for r in row_results if r and not r.get("error")), None)
        label = (first or {}).get("model_label", model_id)
        task_label = (first or {}).get("task_label", task)

        row = f"| {label} | {task_label} |"
        tpss = []
        for r in row_results:
            if r and not r.get("error"):
                row += f" {r['tok_per_sec']} |"
                tpss.append(r["tok_per_sec"])
            else:
                row += " error |"
                tpss.append(None)

        if len(payloads) >= 2:
            valid = [t for t in tpss if t is not None]
            if len(valid) >= 2:
                row += f" {delta_str(valid[-1], valid[0], lower_is_better=False)} |"
            else:
                row += " — |"

        lines.append(row)

    lines += ["", "---", ""]

    # ── Aggregate summary ──
    lines.append("## Aggregate Summary (averages across all tasks)")
    lines.append("")
    lines.append("| Model | Run | Avg Latency (s) | Avg Tok/s | Tasks | Errors |")
    lines.append("|-------|-----|----------------:|----------:|------:|-------:|")

    model_ids = list(dict.fromkeys(m for m, _ in all_keys))
    for model_id in model_ids:
        for i, (payload, idx) in enumerate(zip(payloads, indices)):
            model_rs = [r for (mid, _), r in idx.items()
                        if mid == model_id and r and not r.get("error")]
            errs = sum(1 for (mid, _), r in idx.items()
                       if mid == model_id and r and r.get("error"))
            label = model_rs[0]["model_label"] if model_rs else model_id
            if model_rs:
                al = avg([r["latency_s"] for r in model_rs])
                at = avg([r["tok_per_sec"] for r in model_rs])
                lines.append(f"| {label} | {labels[i]} | {al} | {at} | {len(model_rs)} | {errs} |")

    lines += ["", "---", ""]
    lines.append("*Generated by agy-benchmark `scripts/compare.py`*")

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare two or more benchmark result JSON files")
    parser.add_argument("files", nargs="+", help="Result JSON files to compare (chronological order)")
    parser.add_argument("--md", action="store_true", help="Print markdown to stdout")
    parser.add_argument("--out", default=None, help="Save comparison markdown to this path")
    args = parser.parse_args()

    if args.out:
        args.out = str(Path(args.out).resolve())
        if not Path(args.out).is_relative_to(Path(ROOT).resolve()):
            print(f"Error: --out must be within the project directory: {args.out}", file=sys.stderr)
            sys.exit(1)

    if len(args.files) < 2:
        print("Provide at least 2 result files to compare.", file=sys.stderr)
        sys.exit(1)

    payloads = [load(f) for f in args.files]
    md = compare(payloads)

    if args.md or not args.out:
        print(md)

    if args.out:
        os.makedirs(os.path.dirname(args.out) or ".", exist_ok=True)
        with open(args.out, "w") as f:
            f.write(md)
        print(f"\nComparison saved → {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
