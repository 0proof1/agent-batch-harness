from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from .core import (
    build_prompts,
    claim_shard,
    next_shard,
    plan_shards,
    read_manifest,
    run_shard,
    update_manifest_status,
    verify_outputs,
    verify_shard_outputs,
)


DEFAULT_FORBIDDEN = [
    r"TODO",
    r"TBD",
    r"placeholder",
    r"FIXME",
]


def cmd_plan(args: argparse.Namespace) -> int:
    manifest = plan_shards(args.items, args.batch_dir, args.batch_size)
    print(f"wrote {manifest}")
    return 0


def cmd_build_prompts(args: argparse.Namespace) -> int:
    written = build_prompts(args.items, args.manifest, args.template, args.workdir)
    for path in written:
        print(f"wrote {path}")
    return 0


def cmd_resume(args: argparse.Namespace) -> int:
    shard = next_shard(args.manifest, set(args.status))
    if shard is None:
        print("no resumable shard found")
        return 0
    print(f"{shard.shard_id}\t{shard.status}\t{shard.prompt_path}\t{shard.log_path}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    shards = read_manifest(args.manifest)
    selected = [shard for shard in shards if shard.status in set(args.status)]
    if args.shard:
        selected = [shard for shard in shards if shard.shard_id == args.shard]
    if args.limit is not None:
        selected = selected[: args.limit]
    if not selected:
        print("no shards selected")
        return 0
    allowed_statuses = set(args.status)
    def run_one(shard) -> int:
        print(f"running {shard.shard_id} with {args.runner}")
        if (args.dry_run or args.runner == "dry-run") and args.mark_dry_run:
            claimed = claim_shard(args.manifest, shard.shard_id, allowed_statuses)
            if claimed is None:
                print(f"skipping {shard.shard_id}; it is no longer eligible")
                return 0
        code = run_shard(
            args.manifest,
            shard,
            args.workdir,
            args.runner,
            dry_run=args.dry_run,
            shell_command=args.shell_command,
            verify_command=args.verify_command,
            allowed_statuses=allowed_statuses,
            timeout=args.timeout,
        )
        if args.dry_run or args.runner == "dry-run":
            if args.mark_dry_run:
                update_manifest_status(args.manifest, shard.shard_id, "completed")
        return code

    if args.jobs == 1:
        exit_code = 0
        for shard in selected:
            code = run_one(shard)
            if code != 0:
                exit_code = code
                if not args.continue_on_failure:
                    break
        return exit_code

    exit_code = 0
    with ThreadPoolExecutor(max_workers=args.jobs) as executor:
        futures = {executor.submit(run_one, shard): shard for shard in selected}
        for future in as_completed(futures):
            shard = futures[future]
            code = future.result()
            if code != 0:
                print(f"failed {shard.shard_id} with exit code {code}")
                exit_code = code
    return exit_code


def cmd_verify(args: argparse.Namespace) -> int:
    patterns = args.forbid or DEFAULT_FORBIDDEN
    if args.shard:
        ok, errors = verify_shard_outputs(
            args.items,
            args.manifest,
            args.shard,
            args.workdir,
            patterns,
            require_json=not args.no_json,
        )
    else:
        ok, errors = verify_outputs(args.items, args.workdir, patterns, require_json=not args.no_json)
    if ok:
        print("verification passed")
        return 0
    for error in errors:
        print(error)
    return 1


def cmd_mark(args: argparse.Namespace) -> int:
    update_manifest_status(args.manifest, args.shard, args.status)
    print(f"marked {args.shard} {args.status}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="shardflow")
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan", help="create _batches/manifest.tsv from an items TSV")
    plan.add_argument("--items", type=Path, required=True)
    plan.add_argument("--batch-dir", type=Path, default=Path("_batches"))
    plan.add_argument("--batch-size", type=int, default=4)
    plan.set_defaults(func=cmd_plan)

    prompts = sub.add_parser("build-prompts", help="render shard prompts from a manifest and template")
    prompts.add_argument("--items", type=Path, required=True)
    prompts.add_argument("--manifest", type=Path, required=True)
    prompts.add_argument("--template", type=Path, required=True)
    prompts.add_argument("--workdir", type=Path, default=Path("."))
    prompts.set_defaults(func=cmd_build_prompts)

    resume = sub.add_parser("resume", help="print the next pending or failed shard")
    resume.add_argument("--manifest", type=Path, required=True)
    resume.add_argument("--status", nargs="+", default=["pending", "failed"])
    resume.set_defaults(func=cmd_resume)

    run = sub.add_parser("run", help="run selected shards")
    run.add_argument("--manifest", type=Path, required=True)
    run.add_argument("--workdir", type=Path, default=Path("."))
    run.add_argument("--runner", choices=["dry-run", "codex", "shell"], default="dry-run")
    run.add_argument("--shell-command", help="platform shell command for the shell runner; receives the prompt on stdin")
    run.add_argument("--verify-command", help="shell command run after a successful shard; non-zero marks it failed")
    run.add_argument("--status", nargs="+", default=["pending"])
    run.add_argument("--shard")
    run.add_argument("--limit", type=int)
    run.add_argument("--jobs", type=int, default=1, help="maximum concurrent shard processes")
    run.add_argument("--timeout", type=float, help="runner and verifier timeout in seconds")
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--mark-dry-run", action="store_true")
    run.add_argument("--continue-on-failure", action="store_true")
    run.set_defaults(func=cmd_run)

    verify = sub.add_parser("verify", help="verify expected outputs and QC JSON files")
    verify.add_argument("--items", type=Path, required=True)
    verify.add_argument("--manifest", type=Path)
    verify.add_argument("--shard", help="verify only this shard; requires --manifest")
    verify.add_argument("--workdir", type=Path, default=Path("."))
    verify.add_argument("--forbid", action="append")
    verify.add_argument("--no-json", action="store_true")
    verify.set_defaults(func=cmd_verify)

    mark = sub.add_parser("mark", help="manually update a shard status")
    mark.add_argument("--manifest", type=Path, required=True)
    mark.add_argument("--shard", required=True)
    mark.add_argument("--status", choices=["pending", "running", "completed", "failed", "skipped"], required=True)
    mark.set_defaults(func=cmd_mark)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.command == "verify" and args.shard and args.manifest is None:
        parser.error("verify --shard requires --manifest")
    if args.command == "run" and args.jobs < 1:
        parser.error("run --jobs must be at least 1")
    if args.command == "run" and args.timeout is not None and args.timeout <= 0:
        parser.error("run --timeout must be greater than 0")
    return args.func(args)
