# Code Migration Recipe

This planning example shards a tiny legacy module by independent function. It
does not ship completed outputs; run `plan` and `build-prompts`, then use a shell
or agent runner that writes the declared output and QC paths.

```bash
shardflow plan --items items.tsv --batch-dir _batches --batch-size 1
shardflow build-prompts --items items.tsv --manifest _batches/manifest.tsv --template prompt-template.md --workdir .
```

Keep shared exports, formatting, and broad test changes in a parent closeout
step after every shard passes focused verification.
