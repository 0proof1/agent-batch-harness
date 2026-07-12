# Workflow Recipes

Agent Batch Harness's file contract stays the same across domains. Only item fields,
prompt instructions, and verifier commands change.

## Code Migration

Use one item per module or independent symbol group. Write migrated files to
disjoint paths, and make the verifier run focused tests for the current shard.
Keep shared registries and global formatting in a parent closeout step.

## Translation

Use one item per stable source range. Store translation and QC JSON separately.
Forbid source-language residue and placeholders, then run a parent terminology
and continuity pass after every shard is accepted.

## Documentation Audit

Use one item per document or bounded section. Emit the revised document plus a
machine-readable finding summary. Verify links and forbidden markers per shard.

## Data Cleanup

Use immutable source snapshots and disjoint outputs. The worker must never
mutate the source dataset. Verify schema, row counts, identifiers, and rejection
reports before aggregation.
