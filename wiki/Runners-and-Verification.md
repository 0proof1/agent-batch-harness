# Runners and Verification

## Built-in runner choices

- `dry-run` records what would be executed.
- `codex` passes the prompt to `codex exec`.
- `shell` passes the prompt on standard input to an operator-supplied command.

```bash
agent-batch run \
  --manifest _batches/manifest.tsv \
  --runner shell \
  --shell-command 'your-agent-cli run --stdin' \
  --workdir .
```

The process receives `AGENT_BATCH_SHARD_ID`, `AGENT_BATCH_PROMPT`,
`AGENT_BATCH_WORKDIR`, `AGENT_BATCH_LOG`, and `AGENT_BATCH_ATTEMPT`.

## Structural verification

```bash
agent-batch verify --items items.tsv --workdir .
```

The built-in check requires every output to be non-empty UTF-8 text, every QC
file to be a JSON object containing `"pass": true`, and no output to match the
configured forbidden patterns. This is structural verification, not proof that
the work is semantically correct.

## Verified runs

Attach the check that actually represents acceptance:

```bash
agent-batch run \
  --manifest _batches/manifest.tsv \
  --runner shell \
  --shell-command 'your-agent-cli run --stdin' \
  --verify-command 'agent-batch verify --items items.tsv --manifest _batches/manifest.tsv --shard "$AGENT_BATCH_SHARD_ID" --workdir .' \
  --workdir .
```

The final status is `verified` only when both commands exit zero. Add project
tests, schema checks, compilation, or domain-specific review to the verifier
command when file-shape checks are insufficient.

## Trust boundary

Shell commands and agent processes run with the current user's permissions.
Use a separate OS/container sandbox when commands, prompts, or project content
are not fully trusted.
