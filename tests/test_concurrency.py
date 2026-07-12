from __future__ import annotations

import unittest
import os
import shlex
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory

from shardflow.core import (
    claim_shard,
    plan_shards,
    read_manifest,
    run_logged_process,
    run_shard,
    update_manifest_status,
)


def python_command(code: str) -> str:
    executable = subprocess.list2cmdline([sys.executable]) if os.name == "nt" else shlex.quote(sys.executable)
    return f'{executable} -c "{code}"'


def make_project(root: Path, count: int = 1) -> tuple[Path, list]:
    items = root / "items.tsv"
    rows = ["item_id\tsource\toutput\tqc\tnotes"]
    rows.extend(f"item_{index}\tin/{index}\tout/{index}\tqc/{index}\t" for index in range(count))
    items.write_text("\n".join(rows) + "\n", encoding="utf-8")
    manifest = plan_shards(items, root / "_batches", 1)
    shards = read_manifest(manifest)
    for shard in shards:
        prompt = root / shard.prompt_path
        prompt.parent.mkdir(parents=True, exist_ok=True)
        prompt.write_text("work\n", encoding="utf-8")
    return manifest, shards


class ConcurrencyTest(unittest.TestCase):
    def test_only_one_thread_claims_a_shard(self) -> None:
        with TemporaryDirectory() as tmp:
            manifest, _ = make_project(Path(tmp))
            with ThreadPoolExecutor(max_workers=8) as executor:
                claims = list(executor.map(lambda _: claim_shard(manifest, "shard_001", {"pending"}), range(8)))
            self.assertEqual(sum(claim is not None for claim in claims), 1)

    def test_parallel_status_updates_preserve_every_row(self) -> None:
        with TemporaryDirectory() as tmp:
            manifest, shards = make_project(Path(tmp), 12)
            with ThreadPoolExecutor(max_workers=6) as executor:
                list(executor.map(lambda shard: update_manifest_status(manifest, shard.shard_id, "skipped"), shards))
            self.assertEqual([shard.status for shard in read_manifest(manifest)], ["skipped"] * 12)

    def test_runner_timeout_marks_shard_failed(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest, shards = make_project(root)
            code = run_shard(
                manifest,
                shards[0],
                root,
                "shell",
                shell_command=python_command("import time; time.sleep(2)"),
                timeout=0.05,
            )
            self.assertEqual(code, 124)
            self.assertEqual(read_manifest(manifest)[0].status, "failed")
            self.assertIn("timed out", (root / shards[0].log_path).read_text(encoding="utf-8"))

    def test_timeout_terminates_child_process_tree(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            marker = root / "child-finished"
            child = f"import time,pathlib; time.sleep(0.3); pathlib.Path({str(marker)!r}).write_text('late')"
            parent = (
                "import subprocess,sys,time; "
                f"subprocess.Popen([sys.executable, '-c', {child!r}]); time.sleep(2)"
            )
            with (root / "log.txt").open("w", encoding="utf-8") as log:
                code = run_logged_process(
                    [sys.executable, "-c", parent],
                    subprocess.DEVNULL,
                    log,
                    root,
                    os.environ.copy(),
                    0.05,
                )
            time.sleep(0.5)
            self.assertEqual(124, code)
            self.assertFalse(marker.exists())


if __name__ == "__main__":
    unittest.main()
