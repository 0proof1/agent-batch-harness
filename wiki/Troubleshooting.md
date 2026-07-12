# Troubleshooting

## A shard stays `running`

Confirm the original runner is no longer active, then use `reclaim` with a
conservative age threshold. Do not immediately reclaim a process that may still
be writing outputs.

## A run says `succeeded`, not `verified`

No verifier was configured. Rerun with `--verify-command`, run verification
separately and review it, or leave the honest runner-only status unchanged.

## Verification rejects valid JSON

QC must be a JSON object containing the boolean value `true`:

```json
{"item_id": "alpha", "pass": true, "notes": "checks passed"}
```

Strings such as `"true"`, numeric `1`, arrays, and `{ "pass": false }` fail.

## Planning reports a destination conflict

Two `output`/`qc` fields normalize to the same path. Give each item distinct
destinations. This includes equivalent spellings such as `out/a` and
`out/./a`.

## A missing runner or prompt leaves work failed

Missing prompts are detected before a claim and leave the shard pending.
Failures after claiming are logged and return it to `failed`, making it eligible
for retry after the configuration is corrected.

## Timeout behavior differs by platform

POSIX runners use a separate process group; Windows uses a new process group and
`taskkill /T /F`. Detached processes and external services are outside this
cleanup guarantee.
