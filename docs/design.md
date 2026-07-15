# Design

Agent Batch Harness is built around a small continuity model:

1. A work item list describes the real units of work.
2. A manifest groups those items into shards and records status.
3. Prompt files give workers exact scope and output paths.
4. Run logs preserve execution history.
5. Verification checks decide whether a shard can be trusted.
6. Handoff notes explain what to do next when a run stops.

## Status Model

- `pending`: ready to run.
- `running`: currently being executed by a runner.
- `succeeded`: runner exited successfully without a verifier.
- `verified`: runner and configured verifier both exited successfully.
- `failed`: runner exited unsuccessfully or verification failed.
- `skipped`: intentionally not run.

## Runner Model

The first runner is `codex`, implemented as:

```bash
codex exec --cd <workdir> --skip-git-repo-check - < <prompt>
```

The `dry-run` runner is included for tests, demos, and planning. The generic
`shell` runner passes the prompt on standard input and exports shard metadata
through `AGENT_BATCH_SHARD_ID`, `AGENT_BATCH_PROMPT`, `AGENT_BATCH_WORKDIR`, and
`AGENT_BATCH_LOG`. `AGENT_BATCH_ATTEMPT` identifies the current claim attempt.
The work directory is resolved before invocation, so the runner working
directory, command arguments, and exported paths share one absolute base.

Future runners should implement the same contract: read one prompt, write one
log, return an exit code, and leave shard status to the harness.

An optional verifier command runs only after a successful runner. It uses the
same working directory and `AGENT_BATCH_*` environment values. Its output is
appended to the shard log, and a non-zero exit code changes the final status to
`failed`.

## Concurrency Model

Every manifest mutation takes an advisory lock on `manifest.tsv.lock` and
replaces the TSV atomically. Before a real runner starts, it claims the shard
inside that lock by transitioning an eligible status to `running`. This makes
separate Agent Batch Harness processes safe to use against one manifest, provided their
shards write to disjoint project paths.

Each claim records `started_at` and increments `attempt`. The `reclaim` command
changes sufficiently old `running` claims to `failed`; it does not guess whether
a recent process is alive. A runner may finalize only the same `attempt` that it
claimed. If reclaim and retry create a newer attempt while an older process is
still alive, the older process reports a lost claim instead of changing the
newer attempt's status.

The CLI can launch a bounded number of those processes with `run --jobs N`.
The lock provides the cross-process coordination; the bounded executor only
controls local process concurrency.

## Why Parent Files Are Separate

Shard workers should not update aggregate state while executing. That keeps
parallel work safer and makes failed or partial shards easier to discard. The
parent run verifies outputs and then updates memory, reports, and handoff notes.
