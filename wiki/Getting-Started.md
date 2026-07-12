# Getting Started

## Install from a checkout

Agent Batch Harness requires Python 3.11 or newer.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
agent-batch --help
```

On PowerShell, activate with `.venv\Scripts\Activate.ps1`.

## Define work items

Create `items.tsv` with one stable row per work item:

```tsv
item_id	source	output	qc	notes
alpha	inputs/alpha.txt	outputs/alpha.md	qc/alpha.json	Write a concise summary.
beta	inputs/beta.txt	outputs/beta.md	qc/beta.json	Preserve code examples.
```

Output and QC destinations must be unique. This prevents two shards from being
planned against the same writable path.

## Create a prompt template

```markdown
# Work on $shard_id

Complete only the listed items. Write every output and QC file.

$items
```

Available substitutions are `$shard_id`, `$item_count`, `$first_item`,
`$last_item`, and `$items`.

## Plan and render

```bash
agent-batch plan --items items.tsv --batch-dir _batches --batch-size 2
agent-batch build-prompts \
  --items items.tsv \
  --manifest _batches/manifest.tsv \
  --template prompt-template.md \
  --workdir .
agent-batch resume --manifest _batches/manifest.tsv
```

## Exercise the workflow safely

```bash
agent-batch run \
  --manifest _batches/manifest.tsv \
  --runner dry-run \
  --workdir .
```

A dry run writes the proposed invocation to the shard log and does not change
status unless `--mark-dry-run` is explicitly supplied.

Continue with [[Runners and Verification]] before invoking a real agent.
