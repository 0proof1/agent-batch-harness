# Agent Batch Harness Wiki

Agent Batch Harness is a small, file-first CLI for splitting long agent work
into bounded shards, recording each attempt, and resuming without reconstructing
state from chat history.

Use it when work is too large for one agent session and the units can be given
explicit inputs, outputs, and quality-control files. It coordinates trusted
local processes; it is not a sandbox, queue service, or replacement for tests.

## Start here

- [[Getting Started]] — install the CLI and run the synthetic example.
- [[Manifest and Status]] — understand the durable state contract.
- [[Runners and Verification]] — distinguish execution success from verified output.
- [[Recovery and Concurrency]] — retry safely and reclaim abandoned claims.
- [[Troubleshooting]] — diagnose common failures.

## Core promise

The manifest records what may run next. A runner exit code records whether the
process succeeded. Only a configured verifier may move a shard to `verified`.
Those facts are deliberately separate.

## Current maturity

The project is a `0.1.0a1` reference harness. Its plain TSV, Markdown, JSON, and
log files are designed to remain inspectable and replaceable. Treat external
agent CLIs, prompts, manifests, and shell commands as trusted input.
