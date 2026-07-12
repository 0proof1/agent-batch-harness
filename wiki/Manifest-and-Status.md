# Manifest and Status

`_batches/manifest.tsv` is the durable coordination record. It is intentionally
editable with ordinary text tools, but concurrent mutations should go through
the CLI so the advisory lock and atomic replacement are preserved.

## Fields

| Field | Meaning |
|---|---|
| `shard_id` | Stable generated identifier such as `shard_001` |
| `prompt_path` | Prompt supplied to the runner |
| `item_count` | Number of contiguous item rows in the shard |
| `first_item`, `last_item` | Inclusive item range |
| `status` | Current lifecycle state |
| `log_path` | Combined runner and verifier log |
| `started_at` | UTC time of the active claim, empty otherwise |
| `attempt` | Claim counter, incremented before each real run |

## State meanings

| Status | Meaning |
|---|---|
| `pending` | Eligible for its first run |
| `running` | Atomically claimed by a runner |
| `succeeded` | Runner exited zero; no verifier accepted the output |
| `verified` | Runner and configured verifier both exited zero |
| `failed` | Runner, verifier, timeout, or execution setup failed |
| `skipped` | Intentionally excluded by an operator |

The normal transitions are:

```text
pending ──claim──▶ running ──runner only──▶ succeeded
                         └──runner + verifier──▶ verified
                         └──error/timeout──▶ failed
failed ──retry claim──▶ running
```

`succeeded` is not an alias for `verified`. If an output matters, attach a
deterministic verifier or review it and mark it explicitly.

## Manual changes

```bash
agent-batch mark \
  --manifest _batches/manifest.tsv \
  --shard shard_003 \
  --status failed
```

Manual `running` is intentionally unavailable: a running state must have a
claim timestamp and attempt number created atomically by the runner.
