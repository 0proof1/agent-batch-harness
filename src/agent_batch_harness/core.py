from __future__ import annotations

import csv
import json
import os
import re
import signal
import subprocess
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from string import Template
from typing import Iterable


ITEM_FIELDS = ["item_id", "source", "output", "qc", "notes"]
MANIFEST_FIELDS = [
    "shard_id",
    "prompt_path",
    "item_count",
    "first_item",
    "last_item",
    "status",
    "log_path",
    "started_at",
    "attempt",
]
VALID_STATUSES = {"pending", "running", "succeeded", "verified", "failed", "skipped"}


class ClaimLostError(RuntimeError):
    """Raised when a runner tries to finalize a claim that is no longer current."""


@dataclass(frozen=True)
class Item:
    item_id: str
    source: str
    output: str
    qc: str
    notes: str = ""


@dataclass(frozen=True)
class Shard:
    shard_id: str
    prompt_path: str
    item_count: int
    first_item: str
    last_item: str
    status: str
    log_path: str
    started_at: str = ""
    attempt: int = 0


def read_tsv_document(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def read_tsv(path: Path) -> list[dict[str, str]]:
    return read_tsv_document(path)[1]


def write_tsv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, delimiter="\t", fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


@contextmanager
def manifest_lock(manifest_path: Path):
    """Serialize manifest mutations with an advisory lock beside the manifest."""
    lock_path = manifest_path.with_name(f"{manifest_path.name}.lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("a+b") as handle:
        if os.name == "nt":
            import msvcrt

            if handle.tell() == 0:
                handle.write(b"0")
                handle.flush()
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if os.name == "nt":
                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def write_manifest(manifest_path: Path, rows: Iterable[dict[str, str]]) -> None:
    """Atomically replace a manifest while its lock is held by the caller."""
    temporary_path = manifest_path.with_name(f".{manifest_path.name}.tmp-{os.getpid()}")
    write_tsv(temporary_path, MANIFEST_FIELDS, rows)
    os.replace(temporary_path, manifest_path)


def read_items(path: Path) -> list[Item]:
    fieldnames, rows = read_tsv_document(path)
    missing = [field for field in ITEM_FIELDS[:4] if field not in fieldnames]
    if missing:
        raise ValueError(f"{path} is missing required item fields: {', '.join(missing)}")
    if not rows:
        raise ValueError(f"{path} contains no items")
    items = [
        Item(
            item_id=row["item_id"],
            source=row["source"],
            output=row["output"],
            qc=row["qc"],
            notes=row.get("notes", ""),
        )
        for row in rows
    ]
    identifiers = [item.item_id for item in items]
    if any(not identifier for identifier in identifiers):
        raise ValueError(f"{path} contains an empty item_id")
    if len(identifiers) != len(set(identifiers)):
        raise ValueError(f"{path} contains duplicate item_id values")
    destinations: dict[str, tuple[str, str]] = {}
    for item in items:
        for kind, value in (("output", item.output), ("qc", item.qc)):
            if not value:
                raise ValueError(f"{path} contains an empty {kind} path for {item.item_id}")
            destination_key = os.path.normcase(os.path.normpath(value))
            previous = destinations.get(destination_key)
            if previous is not None:
                previous_item, previous_kind = previous
                raise ValueError(
                    f"{path} contains conflicting destination path {value!r}: "
                    f"{previous_item}.{previous_kind} and {item.item_id}.{kind}"
                )
            destinations[destination_key] = (item.item_id, kind)
    return items


def chunk(items: list[Item], size: int) -> list[list[Item]]:
    if size < 1:
        raise ValueError("batch size must be at least 1")
    return [items[index : index + size] for index in range(0, len(items), size)]


def plan_shards(items_path: Path, batch_dir: Path, batch_size: int) -> Path:
    items = read_items(items_path)
    rows = []
    for index, group in enumerate(chunk(items, batch_size), start=1):
        shard_id = f"shard_{index:03d}"
        rows.append(
            {
                "shard_id": shard_id,
                "prompt_path": str(batch_dir / f"{shard_id}.prompt.md"),
                "item_count": str(len(group)),
                "first_item": group[0].item_id,
                "last_item": group[-1].item_id,
                "status": "pending",
                "log_path": str(batch_dir / "run-logs" / f"{shard_id}.log"),
                "started_at": "",
                "attempt": "0",
            }
        )
    manifest_path = batch_dir / "manifest.tsv"
    with manifest_lock(manifest_path):
        write_manifest(manifest_path, rows)
    return manifest_path


def read_manifest(manifest_path: Path) -> list[Shard]:
    rows = read_tsv(manifest_path)
    if not rows:
        return []
    missing = [field for field in MANIFEST_FIELDS if field not in rows[0]]
    if missing:
        raise ValueError(f"{manifest_path} is missing manifest fields: {', '.join(missing)}")
    shards = [
        Shard(
            shard_id=row["shard_id"],
            prompt_path=row["prompt_path"],
            item_count=int(row["item_count"]),
            first_item=row["first_item"],
            last_item=row["last_item"],
            status=row["status"],
            log_path=row["log_path"],
            started_at=row["started_at"],
            attempt=int(row["attempt"]),
        )
        for row in rows
    ]
    identifiers = [shard.shard_id for shard in shards]
    if len(identifiers) != len(set(identifiers)):
        raise ValueError(f"{manifest_path} contains duplicate shard_id values")
    invalid = sorted({shard.status for shard in shards} - VALID_STATUSES)
    if invalid:
        raise ValueError(f"{manifest_path} contains invalid statuses: {', '.join(invalid)}")
    return shards


def update_manifest_status(
    manifest_path: Path,
    shard_id: str,
    status: str,
    expected_statuses: set[str] | None = None,
    expected_attempt: int | None = None,
) -> bool:
    if status not in VALID_STATUSES:
        raise ValueError(f"invalid shard status: {status}")
    with manifest_lock(manifest_path):
        rows = read_tsv(manifest_path)
        for row in rows:
            if row["shard_id"] == shard_id:
                if expected_statuses is not None and row["status"] not in expected_statuses:
                    return False
                if expected_attempt is not None and int(row["attempt"]) != expected_attempt:
                    return False
                row["status"] = status
                if status != "running":
                    row["started_at"] = ""
                write_manifest(manifest_path, rows)
                return True
    raise ValueError(f"unknown shard id: {shard_id}")


def claim_shard(manifest_path: Path, shard_id: str, allowed_statuses: set[str]) -> Shard | None:
    """Atomically move an eligible shard to running and return its current row."""
    with manifest_lock(manifest_path):
        rows = read_tsv(manifest_path)
        for row in rows:
            if row["shard_id"] != shard_id:
                continue
            if row["status"] not in allowed_statuses:
                return None
            row["status"] = "running"
            row["started_at"] = datetime.now(timezone.utc).isoformat()
            row["attempt"] = str(int(row["attempt"]) + 1)
            write_manifest(manifest_path, rows)
            return Shard(
                shard_id=row["shard_id"],
                prompt_path=row["prompt_path"],
                item_count=int(row["item_count"]),
                first_item=row["first_item"],
                last_item=row["last_item"],
                status="running",
                log_path=row["log_path"],
                started_at=row["started_at"],
                attempt=int(row["attempt"]),
            )
    raise ValueError(f"unknown shard id: {shard_id}")


def reclaim_stale_shards(manifest_path: Path, older_than_seconds: float) -> list[str]:
    """Mark running shards older than the threshold failed so they can be resumed."""
    if older_than_seconds <= 0:
        raise ValueError("reclaim threshold must be greater than 0")
    now = datetime.now(timezone.utc)
    reclaimed: list[str] = []
    with manifest_lock(manifest_path):
        rows = read_tsv(manifest_path)
        for row in rows:
            if row["status"] != "running" or not row["started_at"]:
                continue
            try:
                started_at = datetime.fromisoformat(row["started_at"])
            except ValueError as exc:
                raise ValueError(f"invalid started_at for {row['shard_id']}: {row['started_at']}") from exc
            if started_at.tzinfo is None:
                started_at = started_at.replace(tzinfo=timezone.utc)
            if (now - started_at).total_seconds() >= older_than_seconds:
                row["status"] = "failed"
                row["started_at"] = ""
                reclaimed.append(row["shard_id"])
        if reclaimed:
            write_manifest(manifest_path, rows)
    return reclaimed


def items_for_shard(items: list[Item], shard: Shard) -> list[Item]:
    selected: list[Item] = []
    active = False
    for item in items:
        if item.item_id == shard.first_item:
            active = True
        if active:
            selected.append(item)
        if item.item_id == shard.last_item:
            break
    if not selected or selected[0].item_id != shard.first_item or selected[-1].item_id != shard.last_item:
        raise ValueError(f"item range for {shard.shard_id} is not present in items.tsv")
    if len(selected) != shard.item_count:
        raise ValueError(
            f"item count mismatch for {shard.shard_id}: manifest={shard.item_count}, selected={len(selected)}"
        )
    return selected


def render_item_block(items: list[Item]) -> str:
    blocks = []
    for item in items:
        blocks.append(
            "\n".join(
                [
                    f"- item_id: `{item.item_id}`",
                    f"  source: `{item.source}`",
                    f"  output: `{item.output}`",
                    f"  qc: `{item.qc}`",
                    f"  notes: {item.notes or '-'}",
                ]
            )
        )
    return "\n".join(blocks)


def build_prompts(items_path: Path, manifest_path: Path, template_path: Path, workdir: Path) -> list[Path]:
    items = read_items(items_path)
    shards = read_manifest(manifest_path)
    template = Template(template_path.read_text(encoding="utf-8"))
    written = []
    for shard in shards:
        shard_items = items_for_shard(items, shard)
        prompt_path = workdir / shard.prompt_path
        prompt_path.parent.mkdir(parents=True, exist_ok=True)
        prompt = template.safe_substitute(
            shard_id=shard.shard_id,
            item_count=str(shard.item_count),
            first_item=shard.first_item,
            last_item=shard.last_item,
            items=render_item_block(shard_items),
        )
        prompt_path.write_text(prompt, encoding="utf-8")
        written.append(prompt_path)
    return written


def next_shard(manifest_path: Path, statuses: set[str] | None = None) -> Shard | None:
    wanted = statuses or {"pending", "failed"}
    for shard in read_manifest(manifest_path):
        if shard.status in wanted:
            return shard
    return None


def run_shard(
    manifest_path: Path,
    shard: Shard,
    workdir: Path,
    runner: str,
    dry_run: bool = False,
    shell_command: str | None = None,
    verify_command: str | None = None,
    allowed_statuses: set[str] | None = None,
    timeout: float | None = None,
) -> int:
    workdir = workdir.resolve()
    prompt_path = workdir / shard.prompt_path
    log_path = workdir / shard.log_path
    log_path.parent.mkdir(parents=True, exist_ok=True)
    if dry_run or runner == "dry-run":
        log_path.write_text(f"dry-run: would execute {prompt_path}\n", encoding="utf-8")
        return 0
    if runner not in {"codex", "shell"}:
        raise ValueError(f"unsupported runner: {runner}")
    if runner == "shell" and not shell_command:
        raise ValueError("--shell-command is required when runner is shell")
    if not prompt_path.is_file():
        raise FileNotFoundError(f"missing shard prompt: {prompt_path}")
    claimed = claim_shard(manifest_path, shard.shard_id, allowed_statuses or {"pending", "failed"})
    if claimed is None:
        return 0
    try:
        with prompt_path.open("r", encoding="utf-8") as prompt, log_path.open("w", encoding="utf-8") as log:
            command: list[str] | str = ["codex", "exec", "--cd", str(workdir), "--skip-git-repo-check", "-"]
            use_shell = False
            if runner == "shell":
                command, use_shell = shell_invocation(shell_command)
            environment = os.environ.copy()
            environment.update(
                {
                    "AGENT_BATCH_SHARD_ID": claimed.shard_id,
                    "AGENT_BATCH_PROMPT": str(prompt_path),
                    "AGENT_BATCH_WORKDIR": str(workdir),
                    "AGENT_BATCH_LOG": str(log_path),
                    "AGENT_BATCH_ATTEMPT": str(claimed.attempt),
                }
            )
            return_code = run_logged_process(command, prompt, log, workdir, environment, timeout, use_shell)
            if return_code == 124:
                log.write(f"\nagent-batch-harness: runner timed out after {timeout} seconds\n")
            if return_code == 0 and verify_command:
                log.write("\n\n--- agent-batch-harness verifier ---\n")
                log.flush()
                shell, verifier_uses_shell = shell_invocation(verify_command)
                return_code = run_logged_process(
                    shell,
                    subprocess.DEVNULL,
                    log,
                    workdir,
                    environment,
                    timeout,
                    verifier_uses_shell,
                )
                if return_code == 124:
                    log.write(f"\nagent-batch-harness: verifier timed out after {timeout} seconds\n")
    except BaseException as exc:
        claim_failed = update_manifest_status(
            manifest_path,
            shard.shard_id,
            "failed",
            expected_statuses={"running"},
            expected_attempt=claimed.attempt,
        )
        if claim_failed:
            try:
                with log_path.open("a", encoding="utf-8") as log:
                    log.write(f"\nagent-batch-harness: execution error: {type(exc).__name__}: {exc}\n")
            except OSError:
                pass
        raise
    final_status = "verified" if return_code == 0 and verify_command else "succeeded" if return_code == 0 else "failed"
    finalized = update_manifest_status(
        manifest_path,
        shard.shard_id,
        final_status,
        expected_statuses={"running"},
        expected_attempt=claimed.attempt,
    )
    if not finalized:
        raise ClaimLostError(
            f"claim for {shard.shard_id} attempt {claimed.attempt} is no longer current; "
            "refusing to overwrite the current manifest state"
        )
    return return_code


def shell_invocation(command: str, platform: str | None = None) -> tuple[list[str] | str, bool]:
    """Return a shell invocation without applying a second layer of Windows quoting."""
    if (platform or os.name) == "nt":
        return command, True
    return ["sh", "-c", command], False


def run_logged_process(
    command: list[str] | str,
    stdin: object,
    log: object,
    workdir: Path,
    environment: dict[str, str],
    timeout: float | None,
    use_shell: bool = False,
) -> int:
    options: dict[str, object] = {}
    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        options["start_new_session"] = True
    process = subprocess.Popen(
        command,
        stdin=stdin,
        stdout=log,
        stderr=subprocess.STDOUT,
        cwd=workdir,
        env=environment,
        shell=use_shell,
        **options,
    )
    try:
        return process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        terminate_process_tree(process)
        return 124
    except BaseException:
        terminate_process_tree(process)
        raise


def terminate_process_tree(process: subprocess.Popen) -> None:
    if process.poll() is not None:
        return
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=2)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        process.wait()


def count_paragraphs(path: Path) -> int:
    text = path.read_text(encoding="utf-8")
    return len([part for part in re.split(r"\n\s*\n", text.strip()) if part.strip()])


def verify_outputs(
    items_path: Path,
    workdir: Path,
    forbidden_patterns: list[str],
    require_json: bool = True,
) -> tuple[bool, list[str]]:
    return verify_items(read_items(items_path), workdir, forbidden_patterns, require_json)


def verify_items(
    items: list[Item],
    workdir: Path,
    forbidden_patterns: list[str],
    require_json: bool = True,
) -> tuple[bool, list[str]]:
    errors: list[str] = []
    patterns = [re.compile(pattern) for pattern in forbidden_patterns]
    for item in items:
        output_path = workdir / item.output
        qc_path = workdir / item.qc
        if not output_path.exists():
            errors.append(f"missing output: {item.output}")
        else:
            try:
                text = output_path.read_text(encoding="utf-8")
            except (OSError, UnicodeError) as exc:
                errors.append(f"unreadable output: {item.output}: {exc}")
            else:
                if not text.strip():
                    errors.append(f"empty output: {item.output}")
                for pattern in patterns:
                    if pattern.search(text):
                        errors.append(f"forbidden pattern {pattern.pattern!r} in {item.output}")
        if require_json:
            if not qc_path.exists():
                errors.append(f"missing qc json: {item.qc}")
            else:
                try:
                    qc = json.loads(qc_path.read_text(encoding="utf-8"))
                    if not isinstance(qc, dict) or qc.get("pass") is not True:
                        errors.append(f"qc json must be an object with pass=true: {item.qc}")
                except (json.JSONDecodeError, OSError, UnicodeError) as exc:
                    errors.append(f"invalid qc json: {item.qc}: {exc}")
    return not errors, errors


def verify_shard_outputs(
    items_path: Path,
    manifest_path: Path,
    shard_id: str,
    workdir: Path,
    forbidden_patterns: list[str],
    require_json: bool = True,
) -> tuple[bool, list[str]]:
    shards = read_manifest(manifest_path)
    shard = next((candidate for candidate in shards if candidate.shard_id == shard_id), None)
    if shard is None:
        raise ValueError(f"unknown shard id: {shard_id}")
    items = items_for_shard(read_items(items_path), shard)
    return verify_items(items, workdir, forbidden_patterns, require_json)
