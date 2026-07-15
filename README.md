# Agent Batch Harness

<p align="center"><strong>Split long agent work. Record every run. Verify before trust.</strong></p>

<p align="center">
  <strong>English</strong> · <a href="README.ko.md">한국어</a>
</p>

<p align="center"><code>Python 3.11+</code> · <code>Linux</code> · <code>macOS</code> · <code>Windows</code> · <code>MIT</code></p>

Agent Batch Harness is a small, file-first harness for sharded, resumable agent workflows.

It helps you take work that is too large, too long, or too context-heavy for a
single agent run and turn it into scoped shards with prompts, logs, expected
outputs, verification, and a clear resume path.

Agent Batch Harness does not try to replace an agent runtime. It sits one layer above one:
you keep using Codex, Claude Code, Gemini CLI, a custom agent runner, or a human
review loop. Agent Batch Harness gives those runs a durable shape.

```text
large goal
   |
   v
items.tsv  ->  _batches/manifest.tsv  ->  shard prompts
                                             |
                                             v
                                      agent runner logs
                                             |
                                             v
                                  outputs + qc + resume
```

## Why Agent Batch Harness Exists

Long agent workflows fail in predictable ways:

- The task is bigger than one context window.
- The agent makes progress but stops before the whole job is done.
- Parallel workers collide over shared files.
- A later run cannot tell what is complete, partial, stale, or unsafe.
- Logs exist, but there is no machine-readable manifest.
- Parent status files get edited by workers before their output is verified.

Agent Batch Harness turns those failure modes into a simple operating model:

- **Shard the work** into independent item ranges.
- **Render exact prompts** for each shard.
- **Run one shard at a time** or fan out deliberately.
- **Keep logs** beside the prompt that produced them.
- **Verify outputs locally** before trusting a shard.
- **Resume from the manifest** instead of reading the whole project history.

The core idea is intentionally boring: TSV files, Markdown prompts, JSON QC,
plain logs, and explicit status transitions.

## What It Is

Agent Batch Harness is:

- a Python CLI;
- a project layout convention;
- a prompt generation harness;
- a runner wrapper for agent CLIs;
- a verification layer for expected files and QC JSON;
- a continuity pattern for long-running work.

Agent Batch Harness is not:

- a model provider;
- an autonomous planner;
- a queue service;
- a replacement for tests, review, or security boundaries;
- tied forever to one agent product.

The first runner is `codex`, implemented as:

```bash
codex exec --cd <workdir> --skip-git-repo-check - < <prompt>
```

The included `dry-run` runner exists for demos, tests, and planning. The
generic `shell` runner accepts a command and provides each shard's prompt on
standard input, so an existing CLI does not need a dedicated adapter first.

## Current Status

This is an early open-source scaffold. It already supports:

- `plan`: create `_batches/manifest.tsv` from an item list;
- `build-prompts`: render one prompt per shard;
- `resume`: print the next `pending` or `failed` shard;
- `run`: execute selected shards with bounded parallelism using `dry-run`,
  `codex`, or `shell`, with an optional post-run verifier hook;
- `verify`: check all outputs or one shard's outputs and QC JSON files;
- `mark`: manually update shard status.

The design is intentionally small so it can be audited, copied into existing
projects, or extended without adopting a full orchestration platform.

## Repository Layout

```text
agent-batch-harness/
  src/agent_batch_harness/
    cli.py                  # command-line interface
    core.py                 # manifest, prompt, runner, verification logic

  skills/
    generic-shard/
      SKILL.md              # reusable skill instructions for shard workers

  agents/
    parent-orchestrator.md  # parent-run role prompt
    shard-worker.md         # worker role prompt
    reviewer.md             # verifier/reviewer role prompt

  examples/
    tiny-edit/
      items.tsv
      prompt-template.md
      inputs/
      outputs/
      qc/
      _batches/
        manifest.tsv
        shard_001.prompt.md
        shard_002.prompt.md
        run-logs/

  docs/
    design.md
    workflow.md

  tests/
    test_core.py
```

## Install

Create an isolated environment and install the project:

```bash
python3 -m venv .venv
. .venv/bin/activate
python3 -m pip install -e .
agent-batch --help
```

On Windows PowerShell, activate with `.venv\Scripts\Activate.ps1`; commands
after activation are otherwise the same. To install a built wheel instead of a
checkout, run `python -m pip install path/to/agent-batch-harness-*.whl`.

Without installing:

```bash
PYTHONPATH=src python3 -m agent_batch_harness --help
```

Agent Batch Harness currently has no runtime dependency outside the Python standard
library. It targets Python 3.11+ on Linux, macOS, and Windows. Manifest locking
uses `flock` on POSIX and `msvcrt` byte-range locking on Windows.

See `docs/platforms.md` for shell, locking, timeout, and external-runner
differences across operating systems.

| Environment | Installation | Validation level |
|---|---|---|
| Linux, Python 3.11-3.13 | Editable install or wheel | Unit, package, and local process tests |
| macOS, Python 3.12 | Editable install or wheel | CI matrix configured |
| Windows, Python 3.12 | Editable install or wheel | CI matrix configured |
| Containers and CI workers | Install the same pure-Python wheel | Depends on the external runner image |

Agent Batch Harness itself is pure Python, but the agent CLI selected by `--runner` is an
external prerequisite. Air-gapped environments must preload both the wheel and
the chosen agent runner.

## Quick Start

Run the bundled tiny example:

```bash
cd examples/tiny-edit

PYTHONPATH=../../src python3 -m agent_batch_harness plan \
  --items items.tsv \
  --batch-dir _batches \
  --batch-size 2

PYTHONPATH=../../src python3 -m agent_batch_harness build-prompts \
  --items items.tsv \
  --manifest _batches/manifest.tsv \
  --template prompt-template.md \
  --workdir .

PYTHONPATH=../../src python3 -m agent_batch_harness resume \
  --manifest _batches/manifest.tsv

PYTHONPATH=../../src python3 -m agent_batch_harness verify \
  --items items.tsv \
  --workdir .
```

Expected `resume` output:

```text
shard_001    pending    _batches/shard_001.prompt.md    _batches/run-logs/shard_001.log
```

Use a dry run to exercise the runner path without invoking an agent:

```bash
PYTHONPATH=../../src python3 -m agent_batch_harness run \
  --manifest _batches/manifest.tsv \
  --runner dry-run \
  --workdir . \
  --limit 1
```

Run bounded parallel work when every selected shard has disjoint output paths:

```bash
PYTHONPATH=../../src python3 -m agent_batch_harness run \
  --manifest _batches/manifest.tsv \
  --runner codex \
  --workdir . \
  --jobs 3
```

Bound a runner and its verifier with a timeout. A timeout exits with code `124`
and marks the claimed shard `failed`:

```bash
agent-batch run --manifest _batches/manifest.tsv --runner codex --timeout 900
```

Run a verifier after every successful shard. The verifier runs in the work
directory and receives the same `AGENT_BATCH_*` environment variables as the
runner. A non-zero verifier result marks that shard `failed` and appends its
output to the shard log.

```bash
PYTHONPATH=../../src python3 -m agent_batch_harness run \
  --manifest _batches/manifest.tsv \
  --runner shell \
  --shell-command 'your-agent-cli run --stdin' \
  --verify-command 'python3 -m agent_batch_harness verify --items items.tsv --manifest _batches/manifest.tsv --shard "$AGENT_BATCH_SHARD_ID" --workdir .' \
  --workdir . \
  --jobs 3
```

Run a shard with Codex:

```bash
PYTHONPATH=../../src python3 -m agent_batch_harness run \
  --manifest _batches/manifest.tsv \
  --runner codex \
  --workdir . \
  --limit 1
```

Run a shard through another CLI with the generic shell runner. The command
receives the rendered prompt on standard input. It also receives
`AGENT_BATCH_SHARD_ID`, `AGENT_BATCH_PROMPT`, `AGENT_BATCH_WORKDIR`, and
`AGENT_BATCH_LOG` in its environment.

```bash
PYTHONPATH=../../src python3 -m agent_batch_harness run \
  --manifest _batches/manifest.tsv \
  --runner shell \
  --shell-command 'your-agent-cli run --stdin' \
  --workdir . \
  --limit 1
```

## The Item File

`items.tsv` is the source of truth for real work units. It must contain the
required header and at least one item row.

Required columns:

```text
item_id    source    output    qc    notes
```

Example:

```tsv
item_id	source	output	qc	notes
alpha	inputs/alpha.txt	outputs/alpha.md	qc/alpha.json	Rewrite as a clear two-sentence note.
beta	inputs/beta.txt	outputs/beta.md	qc/beta.json	Rewrite as a clear two-sentence note.
```

Field meanings:

- `item_id`: stable identifier used in manifests and prompts.
- `source`: path the worker should read.
- `output`: path the worker should write.
- `qc`: path for structured QC/status JSON.
- `notes`: item-specific instruction or context.

Keep `item_id` stable. If the content changes materially, prefer adding a new
item or rebuilding the manifest intentionally.

## The Manifest

`agent-batch plan` writes `_batches/manifest.tsv`.

```tsv
shard_id	prompt_path	item_count	first_item	last_item	status	log_path	started_at	attempt
shard_001	_batches/shard_001.prompt.md	2	alpha	beta	pending	_batches/run-logs/shard_001.log		0
shard_002	_batches/shard_002.prompt.md	1	gamma	gamma	pending	_batches/run-logs/shard_002.log		0
```

Shard status values:

- `pending`: ready to run.
- `running`: currently being executed.
- `succeeded`: the runner exited successfully without a verifier.
- `verified`: the runner and configured verifier both exited successfully.
- `failed`: runner or verification failed.
- `skipped`: intentionally not run.

The manifest is deliberately editable. Humans should be able to inspect and
repair it without a database, service, or special UI.

`started_at` records an active claim in UTC and `attempt` increments on every
claim. Recover an abandoned run after a chosen safety window with:

```bash
agent-batch reclaim --manifest _batches/manifest.tsv --older-than 3600
```

## Prompt Templates

Prompt templates are normal Markdown files rendered with Python
`string.Template`.

Available variables:

- `$shard_id`
- `$item_count`
- `$first_item`
- `$last_item`
- `$items`

Example:

```md
# Work on $shard_id

Complete only the listed items. Do not edit shared aggregate files.

## Items

$items
```

Rendered item blocks look like this:

```md
- item_id: `alpha`
  source: `inputs/alpha.txt`
  output: `outputs/alpha.md`
  qc: `qc/alpha.json`
  notes: Rewrite as a clear two-sentence note.
```

## Recommended Workflow

1. Create `items.tsv`.
2. Create `prompt-template.md`.
3. Run `agent-batch plan`.
4. Run `agent-batch build-prompts`.
5. Run `agent-batch resume` to confirm the next shard.
6. Run one shard.
7. Verify outputs.
8. Mark or rerun as needed.
9. Update parent memory or handoff notes outside the worker run.

For long projects, keep parent state in files such as:

```text
PROJECT_MEMORY.md
HANDOFF.md
STATUS.json
decision-ledger.tsv
qc/report.md
```

Shard workers should generally avoid those files. The parent orchestrator should
update them after verification.

## Parent/Worker Contract

Agent Batch Harness works best when responsibilities are separated.

Parent orchestrator:

- owns the manifest;
- decides what shard runs next;
- starts or supervises runners;
- verifies outputs;
- updates aggregate memory;
- writes handoff notes.

Shard worker:

- reads only the listed source/context files;
- writes only the listed output/QC files;
- does not edit aggregate status unless explicitly instructed;
- reports changed files and validation results;
- exits cleanly after its shard.

Reviewer:

- checks that expected files exist;
- parses QC JSON;
- scans for TODOs or process residue;
- confirms the shard stayed within scope;
- decides whether the manifest status should change.

## Verification

Basic verification:

```bash
agent-batch verify --items items.tsv --workdir .
```

By default, verification checks:

- every `output` file exists;
- every `output` file is non-empty UTF-8 text;
- every `qc` file exists;
- every `qc` file is a JSON object containing `"pass": true`;
- output files do not contain `TODO`, `TBD`, `placeholder`, or `FIXME`.

Add more forbidden patterns:

```bash
agent-batch verify \
  --items items.tsv \
  --workdir . \
  --forbid 'DO NOT COMMIT' \
  --forbid 'SOURCE_TEXT_LEFT_HERE'
```

Skip JSON checks when your workflow has no QC files:

```bash
agent-batch verify --items items.tsv --workdir . --no-json
```

Verify exactly one shard before accepting or retrying it:

```bash
agent-batch verify \
  --items items.tsv \
  --manifest _batches/manifest.tsv \
  --shard shard_002 \
  --workdir .
```

## Resume And Recovery

Find the next shard:

```bash
agent-batch resume --manifest _batches/manifest.tsv
```

Mark a shard manually:

```bash
agent-batch mark \
  --manifest _batches/manifest.tsv \
  --shard shard_003 \
  --status failed
```

Common recovery patterns:

- If a runner exits non-zero, inspect its log and leave the shard `failed`.
- If a run stalls before writing files, preserve the log but rerun the shard.
- If a shard is too large, split its items into smaller shards and rebuild.
- If output exists but fails verification, keep the shard `failed` until fixed.
- If output is valid but the runner status was not updated, use `mark`.

## Parallel Work

Agent Batch Harness is compatible with parallel work, but it does not hide the risk.

Parallelism is appropriate when:

- shards write to disjoint output paths;
- workers do not edit parent aggregate files;
- verification happens after each shard;
- each state update holds a per-manifest advisory lock.

Parallelism is risky when:

- workers share mutable files;
- shards depend on each other in order;
- outputs need a single global style pass;
- external services impose rate or concurrency limits.

`agent-batch run --jobs N` starts up to `N` selected shard processes at once.
With the default `--jobs 1`, it stops after the first failure; add
`--continue-on-failure` to keep processing later shards. Parallel mode starts
the selected work set immediately, so one failure cannot cancel already-running
siblings.

Multiple CLI processes may safely target the same manifest: a worker atomically
claims a shard by changing it from an eligible status to `running`; another
worker will skip that claim. The lock protects manifest writes, not your output
files, so disjoint output paths remain a required workflow invariant.

## Skills And Agents

This repository includes lightweight role prompts:

- `skills/generic-shard/SKILL.md`
- `agents/parent-orchestrator.md`
- `agents/shard-worker.md`
- `agents/reviewer.md`

These are intentionally plain Markdown. They can be copied into projects,
adapted for Codex Skills, embedded in a plugin, or used as direct prompt
partials for another agent runtime.

## Why This Is Useful In 2026

Agent tools increasingly support:

- long-running work;
- skills or reusable process bundles;
- CLI and cloud agent surfaces;
- background execution;
- multi-agent delegation;
- local shell and file operations.

That makes the missing piece less about "can an agent do work?" and more about
"can we make long work auditable, resumable, and safe to parallelize?"

Agent Batch Harness focuses on that missing layer.

## Open-Source Positioning

Agent Batch Harness is a good open-source candidate because it is:

- **small**: the initial implementation is standard-library Python;
- **portable**: TSV, Markdown, JSON, and logs work everywhere;
- **auditable**: no hidden service state;
- **agent-neutral**: runner adapters can target different CLIs;
- **useful immediately**: existing projects can adopt only the folder pattern;
- **safe by convention**: parent files are separated from worker outputs.

The best public framing is:

> Agent Batch Harness is a continuity harness for agentic work: split large tasks into
> verifiable shards, run them through your agent CLI, and resume from a manifest.

## Roadmap

Near-term:

- Add configurable output schemas.
- Add richer handoff generation.
- Add examples for translation, code migration, documentation audits, and data
  cleanup.

Later:

- Add runner adapters for other agent CLIs.
- Add plugin packaging.
- Add a small TUI for manifest inspection.
- Add provenance metadata for each output.
- Add signed or hashed manifests for high-trust workflows.

## Development

Run tests:

```bash
PYTHONPATH=src python3 -m unittest discover -s tests
```

Run CLI help:

```bash
PYTHONPATH=src python3 -m agent_batch_harness --help
```

Run the local publication gate:

```bash
python3 tools/release_check.py
```

See `SECURITY.md`, `PUBLICATION_POLICY.md`, and `docs/release.md` before using a
shell runner on sensitive work or preparing a release.

The current local release score and its evidence are documented in
`docs/readiness.md`; practical domain patterns are collected in
`docs/recipes.md`.

The latest local dependency and artifact review is recorded in
`docs/security-audit.md`.

Check the example:

```bash
cd examples/tiny-edit
PYTHONPATH=../../src python3 -m agent_batch_harness verify --items items.tsv --workdir .
```

## License

MIT. See `LICENSE`.
