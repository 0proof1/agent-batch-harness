# Changelog

All notable changes are documented here. The project follows semantic
versioning.

## 0.1.0a2 - 2026-07-15

- Bound runner, verifier, and marked dry-run finalization to the exact manifest
  attempt that was claimed, preventing stale processes from overwriting a newer
  retry after reclaim.
- Resolved runner work directories before constructing commands and exported
  paths, keeping relative `--workdir` values valid inside child processes.
- Flushed the verifier log marker before launching the verifier so combined log
  output remains in execution order.
- Rejected item files with missing headers or no data rows instead of treating
  an empty work set as successfully verified.

## 0.1.0a1 - 2026-07-13

- Renamed the project and package from Shardflow to Agent Batch Harness.
- Split runner-only `succeeded` from verifier-backed `verified` status.
- Added claim timestamps, attempt counters, and stale-running recovery.
- Made runner startup and interruption failures return claimed shards to `failed`.
- Rejected colliding output/QC destinations and strengthened structural verification.

- Fixed Windows shell-runner quoting and ensured timed-out process handles are
  reaped after process-tree termination.
- Added complete English and Korean README editions with platform-specific
  installation guidance and language navigation.

- Added bounded parallel runners and post-run verification hooks.
- Added advisory manifest locking and atomic state transitions.
- Added runner and verifier timeouts.
- Added per-shard verification and generic shell runner support.
- Added publication, security, community, CI, packaging, and release gates.
- Added Windows-compatible manifest locking, platform shell selection, and
  process-tree timeout cleanup with Linux/macOS/Windows CI.

- Added planning, prompt generation, resume, execution, verification, and manual
  status commands.
