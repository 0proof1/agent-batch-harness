# Workflow

From a project directory:

```bash
agent-batch plan --items items.tsv --batch-dir _batches --batch-size 2
agent-batch build-prompts --items items.tsv --manifest _batches/manifest.tsv --template prompt-template.md --workdir .
agent-batch resume --manifest _batches/manifest.tsv
agent-batch run --manifest _batches/manifest.tsv --runner codex --workdir . --limit 1
agent-batch verify --items items.tsv --workdir .
```

For local checks without invoking an agent:

```bash
agent-batch run --manifest _batches/manifest.tsv --runner dry-run --workdir . --limit 1
```

To use another agent CLI without writing an adapter:

```bash
agent-batch run --manifest _batches/manifest.tsv --runner shell --shell-command 'your-agent-cli run --stdin' --workdir . --limit 1
```

For bounded parallel execution and automatic per-shard verification:

```bash
agent-batch run --manifest _batches/manifest.tsv --runner codex --verify-command 'agent-batch verify --items items.tsv --manifest _batches/manifest.tsv --shard "$AGENT_BATCH_SHARD_ID" --workdir .' --workdir . --jobs 3
```

To verify one shard only:

```bash
agent-batch verify --items items.tsv --manifest _batches/manifest.tsv --shard shard_001 --workdir .
```

Use `agent-batch mark` when a human or external verifier has decided a shard
status should change.

Recover claims left `running` by an interrupted process only after a suitable
safety window:

```bash
agent-batch reclaim --manifest _batches/manifest.tsv --older-than 3600
```
