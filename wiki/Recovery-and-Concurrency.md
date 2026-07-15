# Recovery and Concurrency

## Retry failed work

`resume` selects the next `pending` or `failed` shard:

```bash
agent-batch resume --manifest _batches/manifest.tsv
agent-batch run --manifest _batches/manifest.tsv --status failed --workdir .
```

Every real claim increments `attempt`. Logs are rewritten for the new attempt,
so preserve a log separately first if historical diagnostics are required.

## Reclaim abandoned running work

An interrupted parent process can leave a claim marked `running`. Reclaim it
only after a safety interval longer than legitimate runs:

```bash
agent-batch reclaim \
  --manifest _batches/manifest.tsv \
  --older-than 3600
```

Reclaim changes stale `running` rows to `failed`. It does not inspect remote
workers or prove that a detached process has stopped. If an older process later
finishes after a replacement attempt has started, its final status update is
rejected because its attempt number is no longer current.

## Parallel execution

```bash
agent-batch run \
  --manifest _batches/manifest.tsv \
  --runner shell \
  --shell-command 'your-agent-cli run --stdin' \
  --jobs 3 \
  --workdir .
```

Manifest claims and status writes are serialized. Output files are not locked.
Parallelism is safe only when shards do not mutate shared files, generated
indexes, caches, databases, or external records.

The item validator rejects duplicate normalized output and QC paths. It cannot
detect undeclared writes made by a prompt or agent, so worker instructions must
still prohibit shared aggregate edits.
