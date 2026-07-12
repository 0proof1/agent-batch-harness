# Contributing to Shardflow

Shardflow accepts focused changes that preserve its file-first, agent-neutral
design. Discuss broad changes in an issue before implementing them.

## Development

```bash
python3 -m venv .venv
.venv/bin/pip install -e .
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/python tools/release_check.py
```

Add tests for status transitions, concurrency, recovery, runner behavior, and
CLI contracts. Keep new runtime dependencies exceptional and justified.

Pull requests should describe the behavior changed, risks, validation run, and
any compatibility impact. Never commit prompts, logs, credentials, or project
content that you do not have permission to redistribute.
