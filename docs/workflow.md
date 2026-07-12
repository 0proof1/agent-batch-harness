# Workflow

From a project directory:

```bash
shardflow plan --items items.tsv --batch-dir _batches --batch-size 2
shardflow build-prompts --items items.tsv --manifest _batches/manifest.tsv --template prompt-template.md --workdir .
shardflow resume --manifest _batches/manifest.tsv
shardflow run --manifest _batches/manifest.tsv --runner codex --workdir . --limit 1
shardflow verify --items items.tsv --workdir .
```

For local checks without invoking an agent:

```bash
shardflow run --manifest _batches/manifest.tsv --runner dry-run --workdir . --limit 1
```

To use another agent CLI without writing an adapter:

```bash
shardflow run --manifest _batches/manifest.tsv --runner shell --shell-command 'your-agent-cli run --stdin' --workdir . --limit 1
```

For bounded parallel execution and automatic per-shard verification:

```bash
shardflow run --manifest _batches/manifest.tsv --runner codex --verify-command 'shardflow verify --items items.tsv --manifest _batches/manifest.tsv --shard "$SHARDFLOW_SHARD_ID" --workdir .' --workdir . --jobs 3
```

To verify one shard only:

```bash
shardflow verify --items items.tsv --manifest _batches/manifest.tsv --shard shard_001 --workdir .
```

Use `shardflow mark` when a human or external verifier has decided a shard
status should change.
