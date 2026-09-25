# Security Policy

## Scope

`agy-benchmark` is a local research and benchmarking tool. It does not run as a server, does not accept network connections, and does not process untrusted input in normal use. The attack surface is limited to:

- CLI arguments (`--out`, `--tasks`, `--models`)
- Environment variables (`HERMES_AGENT_PATH`, `HERMES_HOME`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`)
- Local file paths passed to report and comparison scripts

## Reporting a Vulnerability

If you discover a security issue in this project, please report it responsibly rather than opening a public GitHub issue.

**Contact:** Open a [GitHub Security Advisory](https://github.com/sai009/agy-benchmark/security/advisories/new) (private disclosure via GitHub's built-in mechanism).

Please include:
- A description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested fix (optional)

Expect an acknowledgement within 7 days and a fix or response within 30 days.

## Known Limitations

This tool is intended for **local use only**. The following are acknowledged design decisions, not vulnerabilities:

- **`--out` / `--out-dir` path validation** restricts writes to within the project root or home directory. Do not run this tool as root or in environments where arbitrary home-directory writes would be dangerous.
- **`HERMES_AGENT_PATH`** is validated to be a real directory under `~` before being inserted into `sys.path`. Do not set this to a path you do not trust.
- **Benchmark result JSON files** may contain verbatim LLM responses. Review `results/` before committing or sharing if responses may contain sensitive content.
- **API keys** are never stored in this repo. They are consumed via environment variables or a credential manager (Hermes OAuth). Never commit `.env` files.

## Disclosure Policy

This project follows coordinated disclosure. Vulnerabilities will be patched before public disclosure where feasible. Credit will be given to researchers who report issues responsibly.
