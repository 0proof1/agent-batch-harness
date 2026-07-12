# Generic Shard Skill

Use this skill when a large task should be split into independent shards that an
agent can complete, verify, and hand back to a parent run.

## Rules

- Work only on the items listed in the current shard prompt.
- Write outputs to the exact paths listed for each item.
- Keep process notes out of final deliverables unless the item explicitly asks
  for them.
- Write machine-checkable QC or status files when the shard prompt asks for
  them.
- Report changed files and validation results at the end.

## Parent Run Responsibilities

- Build the shard manifest.
- Run shard prompts in sequence or parallel.
- Verify outputs after each shard.
- Update project memory, handoff notes, and aggregate status outside the shard
  worker.

