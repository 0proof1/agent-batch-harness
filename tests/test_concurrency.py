from __future__ import annotations

import unittest
import os
import shlex
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from agent_batch_harness.core import (
    ClaimLostError,
    claim_shard,
    plan_shards,
    read_manifest,
    reclaim_stale_shards,
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
            claimed = next(claim for claim in claims if claim is not None)
            self.assertEqual(claimed.attempt, 1)
            self.assertTrue(claimed.started_at)

    def test_stale_attempt_cannot_update_a_new_claim(self) -> None:
        with TemporaryDirectory() as tmp:
            manifest, shards = make_project(Path(tmp))
            first_claim = claim_shard(manifest, shards[0].shard_id, {"pending"})
            self.assertIsNotNone(first_claim)
            assert first_claim is not None
            self.assertTrue(
                update_manifest_status(
                    manifest,
                    shards[0].shard_id,
                    "failed",
                    expected_statuses={"running"},
                    expected_attempt=first_claim.attempt,
                )
            )
            second_claim = claim_shard(manifest, shards[0].shard_id, {"failed"})
            self.assertIsNotNone(second_claim)
            assert second_claim is not None

            stale_update = update_manifest_status(
                manifest,
                shards[0].shard_id,
                "succeeded",
                expected_statuses={"running"},
                expected_attempt=first_claim.attempt,
            )

            self.assertFalse(stale_update)
            current = read_manifest(manifest)[0]
            self.assertEqual(current.status, "running")
            self.assertEqual(current.attempt, second_claim.attempt)
            self.assertEqual(current.started_at, second_claim.started_at)

    def test_runner_reports_lost_claim_without_finalizing_replacement(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest, shards = make_project(root)
            replacement = {}

            def replace_claim(*_args, **_kwargs) -> int:
                first_claim = read_manifest(manifest)[0]
                self.assertTrue(
                    update_manifest_status(
                        manifest,
                        first_claim.shard_id,
                        "failed",
                        expected_statuses={"running"},
                        expected_attempt=first_claim.attempt,
                    )
                )
                replacement["claim"] = claim_shard(manifest, first_claim.shard_id, {"failed"})
                return 0

            with patch("agent_batch_harness.core.run_logged_process", side_effect=replace_claim):
                with self.assertRaisesRegex(ClaimLostError, "attempt 1 is no longer current"):
                    run_shard(manifest, shards[0], root, "shell", shell_command="agent")

            current = read_manifest(manifest)[0]
            second_claim = replacement["claim"]
            self.assertIsNotNone(second_claim)
            self.assertEqual(current.status, "running")
            self.assertEqual(current.attempt, second_claim.attempt)
            self.assertEqual(current.started_at, second_claim.started_at)

    def test_stale_runner_exception_does_not_fail_replacement(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest, shards = make_project(root)
            replacement = {}

            def replace_claim_and_fail(*_args, **_kwargs) -> int:
                first_claim = read_manifest(manifest)[0]
                self.assertTrue(
                    update_manifest_status(
                        manifest,
                        first_claim.shard_id,
                        "failed",
                        expected_statuses={"running"},
                        expected_attempt=first_claim.attempt,
                    )
                )
                replacement["claim"] = claim_shard(manifest, first_claim.shard_id, {"failed"})
                raise OSError("stale runner failed")

            with patch("agent_batch_harness.core.run_logged_process", side_effect=replace_claim_and_fail):
                with self.assertRaisesRegex(OSError, "stale runner failed"):
                    run_shard(manifest, shards[0], root, "shell", shell_command="agent")

            current = read_manifest(manifest)[0]
            second_claim = replacement["claim"]
            self.assertIsNotNone(second_claim)
            self.assertEqual(current.status, "running")
            self.assertEqual(current.attempt, second_claim.attempt)
            self.assertEqual(current.started_at, second_claim.started_at)

    def test_reclaim_marks_only_stale_running_shards_failed(self) -> None:
        with TemporaryDirectory() as tmp:
            manifest, shards = make_project(Path(tmp), 2)
            claim_shard(manifest, shards[0].shard_id, {"pending"})
            claim_shard(manifest, shards[1].shard_id, {"pending"})
            rows = manifest.read_text(encoding="utf-8").splitlines()
            stale = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
            fields = rows[1].split("\t")
            fields[-2] = stale
            rows[1] = "\t".join(fields)
            manifest.write_text("\n".join(rows) + "\n", encoding="utf-8")

            reclaimed = reclaim_stale_shards(manifest, 3600)

            self.assertEqual(reclaimed, ["shard_001"])
            current = read_manifest(manifest)
            self.assertEqual([shard.status for shard in current], ["failed", "running"])
            self.assertEqual(current[0].started_at, "")

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
