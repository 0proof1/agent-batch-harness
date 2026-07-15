from __future__ import annotations

import io
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from agent_batch_harness.cli import main
from agent_batch_harness.core import claim_shard, plan_shards, read_manifest, update_manifest_status


def make_manifest(root: Path) -> Path:
    items = root / "items.tsv"
    items.write_text("item_id\tsource\toutput\tqc\tnotes\na\tin\tout\tqc\t\n", encoding="utf-8")
    manifest = plan_shards(items, root / "_batches", 1)
    shard = read_manifest(manifest)[0]
    prompt = root / shard.prompt_path
    prompt.parent.mkdir(parents=True, exist_ok=True)
    prompt.write_text("work\n", encoding="utf-8")
    return manifest


class CliTest(unittest.TestCase):
    def test_jobs_must_be_positive(self) -> None:
        with self.assertRaises(SystemExit):
            with redirect_stderr(io.StringIO()):
                main(["run", "--manifest", "missing.tsv", "--jobs", "0"])

    def test_timeout_must_be_positive(self) -> None:
        with self.assertRaises(SystemExit):
            with redirect_stderr(io.StringIO()):
                main(["run", "--manifest", "missing.tsv", "--timeout", "0"])

    def test_shard_verification_requires_manifest(self) -> None:
        with self.assertRaises(SystemExit):
            with redirect_stderr(io.StringIO()):
                main(["verify", "--items", "items.tsv", "--shard", "shard_001"])

    def test_resume_reports_pending_shard(self) -> None:
        with TemporaryDirectory() as tmp:
            manifest = make_manifest(Path(tmp))
            output = io.StringIO()
            with redirect_stdout(output):
                code = main(["resume", "--manifest", str(manifest)])
            self.assertEqual(code, 0)
            self.assertIn("shard_001\tpending", output.getvalue())

    def test_mark_changes_status(self) -> None:
        with TemporaryDirectory() as tmp:
            manifest = make_manifest(Path(tmp))
            with redirect_stdout(io.StringIO()):
                code = main(["mark", "--manifest", str(manifest), "--shard", "shard_001", "--status", "skipped"])
            self.assertEqual(code, 0)
            self.assertEqual(read_manifest(manifest)[0].status, "skipped")

    def test_dry_run_does_not_change_status_by_default(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = make_manifest(root)
            with redirect_stdout(io.StringIO()):
                code = main(["run", "--manifest", str(manifest), "--workdir", str(root), "--runner", "dry-run"])
            self.assertEqual(code, 0)
            self.assertEqual(read_manifest(manifest)[0].status, "pending")

    def test_marked_dry_run_records_runner_success(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = make_manifest(root)
            with redirect_stdout(io.StringIO()):
                code = main(
                    [
                        "run",
                        "--manifest",
                        str(manifest),
                        "--workdir",
                        str(root),
                        "--runner",
                        "dry-run",
                        "--mark-dry-run",
                    ]
                )
            self.assertEqual(code, 0)
            self.assertEqual(read_manifest(manifest)[0].status, "succeeded")

    def test_marked_dry_run_does_not_finalize_replacement_attempt(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            manifest = make_manifest(root)

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
                self.assertIsNotNone(claim_shard(manifest, first_claim.shard_id, {"failed"}))
                return 0

            output = io.StringIO()
            with patch("agent_batch_harness.cli.run_shard", side_effect=replace_claim):
                with redirect_stdout(output):
                    code = main(
                        [
                            "run",
                            "--manifest",
                            str(manifest),
                            "--workdir",
                            str(root),
                            "--runner",
                            "dry-run",
                            "--mark-dry-run",
                        ]
                    )

            current = read_manifest(manifest)[0]
            self.assertEqual(code, 1)
            self.assertEqual(current.status, "running")
            self.assertEqual(current.attempt, 2)
            self.assertIn("ClaimLostError", output.getvalue())


if __name__ == "__main__":
    unittest.main()
