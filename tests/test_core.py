from __future__ import annotations

import json
import os
import shlex
import subprocess
import sys
import unittest
from unittest.mock import patch
from pathlib import Path
from tempfile import TemporaryDirectory

from agent_batch_harness.core import (
    build_prompts,
    claim_shard,
    plan_shards,
    read_manifest,
    run_shard,
    shell_invocation,
    verify_outputs,
    verify_shard_outputs,
)
from agent_batch_harness.cli import main


def python_command(code: str) -> str:
    executable = subprocess.list2cmdline([sys.executable]) if os.name == "nt" else shlex.quote(sys.executable)
    return f'{executable} -c "{code}"'


class AgentBatchHarnessCoreTest(unittest.TestCase):
    def test_shell_invocation_avoids_windows_double_quoting(self) -> None:
        command = '"C:\\Program Files\\Python\\python.exe" -c "print(1)"'
        self.assertEqual((command, True), shell_invocation(command, "nt"))
        self.assertEqual((["sh", "-c", command], False), shell_invocation(command, "posix"))

    def test_plan_and_build_prompts(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            items = root / "items.tsv"
            items.write_text(
                "\n".join(
                    [
                        "item_id\tsource\toutput\tqc\tnotes",
                        "a\tinputs/a.txt\toutputs/a.md\tqc/a.json\tfirst",
                        "b\tinputs/b.txt\toutputs/b.md\tqc/b.json\tsecond",
                        "c\tinputs/c.txt\toutputs/c.md\tqc/c.json\tthird",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            template = root / "template.md"
            template.write_text("# $shard_id\n\n$items\n", encoding="utf-8")

            manifest = plan_shards(items, root / "_batches", 2)
            shards = read_manifest(manifest)
            self.assertEqual(len(shards), 2)
            self.assertEqual(shards[0].first_item, "a")
            self.assertEqual(shards[0].last_item, "b")

            written = build_prompts(items, manifest, template, root)
            self.assertEqual(len(written), 2)
            self.assertIn("item_id: `a`", written[0].read_text(encoding="utf-8"))

    def test_verify_outputs(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "outputs").mkdir()
            (root / "qc").mkdir()
            items = root / "items.tsv"
            items.write_text(
                "item_id\tsource\toutput\tqc\tnotes\n"
                "a\tinputs/a.txt\toutputs/a.md\tqc/a.json\t\n",
                encoding="utf-8",
            )
            (root / "outputs/a.md").write_text("done\n", encoding="utf-8")
            (root / "qc/a.json").write_text(json.dumps({"pass": True}), encoding="utf-8")

            ok, errors = verify_outputs(items, root, ["TODO"])
            self.assertTrue(ok)
            self.assertEqual(errors, [])

            (root / "outputs/a.md").write_text("\n", encoding="utf-8")
            (root / "qc/a.json").write_text(json.dumps({"pass": False}), encoding="utf-8")
            ok, errors = verify_outputs(items, root, ["TODO"])
            self.assertFalse(ok)
            self.assertTrue(any("empty output" in error for error in errors))
            self.assertTrue(any("pass=true" in error for error in errors))

    def test_claim_and_verify_one_shard(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "outputs").mkdir()
            (root / "qc").mkdir()
            items = root / "items.tsv"
            items.write_text(
                "item_id\tsource\toutput\tqc\tnotes\n"
                "a\tinputs/a.txt\toutputs/a.md\tqc/a.json\t\n"
                "b\tinputs/b.txt\toutputs/b.md\tqc/b.json\t\n",
                encoding="utf-8",
            )
            manifest = plan_shards(items, root / "_batches", 1)
            (root / "outputs/a.md").write_text("done\n", encoding="utf-8")
            (root / "qc/a.json").write_text(json.dumps({"pass": True}), encoding="utf-8")

            claimed = claim_shard(manifest, "shard_001", {"pending"})
            self.assertIsNotNone(claimed)
            self.assertIsNone(claim_shard(manifest, "shard_001", {"pending"}))
            self.assertEqual(read_manifest(manifest)[0].status, "running")

            ok, errors = verify_shard_outputs(items, manifest, "shard_001", root, ["TODO"])
            self.assertTrue(ok)
            self.assertEqual(errors, [])

    def test_shell_runner_receives_shard_environment(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            items = root / "items.tsv"
            items.write_text(
                "item_id\tsource\toutput\tqc\tnotes\n"
                "a\tinputs/a.txt\toutputs/a.md\tqc/a.json\t\n",
                encoding="utf-8",
            )
            manifest = plan_shards(items, root / "_batches", 1)
            shard = read_manifest(manifest)[0]
            prompt = root / shard.prompt_path
            prompt.parent.mkdir(parents=True, exist_ok=True)
            prompt.write_text("hello\n", encoding="utf-8")

            code = run_shard(
                manifest,
                shard,
                root,
                "shell",
                shell_command=python_command("import os; assert os.environ['AGENT_BATCH_SHARD_ID'] == 'shard_001'"),
                verify_command=python_command("import os; assert os.environ['AGENT_BATCH_SHARD_ID'] == 'shard_001'"),
            )
            self.assertEqual(code, 0)
            self.assertEqual(read_manifest(manifest)[0].status, "verified")
            log = (root / shard.log_path).read_text(encoding="utf-8")
            self.assertIn("--- agent-batch-harness verifier ---", log)

    def test_failed_verifier_marks_shard_failed(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            items = root / "items.tsv"
            items.write_text(
                "item_id\tsource\toutput\tqc\tnotes\n"
                "a\tinputs/a.txt\toutputs/a.md\tqc/a.json\t\n",
                encoding="utf-8",
            )
            manifest = plan_shards(items, root / "_batches", 1)
            shard = read_manifest(manifest)[0]
            prompt = root / shard.prompt_path
            prompt.parent.mkdir(parents=True, exist_ok=True)
            prompt.write_text("hello\n", encoding="utf-8")

            code = run_shard(
                manifest,
                shard,
                root,
                "shell",
                shell_command=python_command("pass"),
                verify_command=python_command("import sys; sys.exit(1)"),
            )
            self.assertNotEqual(code, 0)
            self.assertEqual(read_manifest(manifest)[0].status, "failed")

    def test_runner_start_exception_marks_claimed_shard_failed(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            items = root / "items.tsv"
            items.write_text(
                "item_id\tsource\toutput\tqc\tnotes\n"
                "a\tinputs/a.txt\toutputs/a.md\tqc/a.json\t\n",
                encoding="utf-8",
            )
            manifest = plan_shards(items, root / "_batches", 1)
            shard = read_manifest(manifest)[0]
            prompt = root / shard.prompt_path
            prompt.parent.mkdir(parents=True, exist_ok=True)
            prompt.write_text("hello\n", encoding="utf-8")

            with patch("agent_batch_harness.core.subprocess.Popen", side_effect=OSError("runner missing")):
                with self.assertRaisesRegex(OSError, "runner missing"):
                    run_shard(manifest, shard, root, "shell", shell_command="agent")

            current = read_manifest(manifest)[0]
            self.assertEqual(current.status, "failed")
            self.assertEqual(current.started_at, "")
            self.assertIn("runner missing", (root / shard.log_path).read_text(encoding="utf-8"))

    def test_missing_prompt_does_not_claim_shard(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            items = root / "items.tsv"
            items.write_text(
                "item_id\tsource\toutput\tqc\tnotes\n"
                "a\tinputs/a.txt\toutputs/a.md\tqc/a.json\t\n",
                encoding="utf-8",
            )
            manifest = plan_shards(items, root / "_batches", 1)
            shard = read_manifest(manifest)[0]
            with self.assertRaisesRegex(FileNotFoundError, "missing shard prompt"):
                run_shard(manifest, shard, root, "shell", shell_command="agent")
            self.assertEqual(read_manifest(manifest)[0].status, "pending")

    def test_cli_runs_shards_with_bounded_parallelism(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            items = root / "items.tsv"
            items.write_text(
                "item_id\tsource\toutput\tqc\tnotes\n"
                "a\tinputs/a.txt\toutputs/a.md\tqc/a.json\t\n"
                "b\tinputs/b.txt\toutputs/b.md\tqc/b.json\t\n",
                encoding="utf-8",
            )
            manifest = plan_shards(items, root / "_batches", 1)
            for shard in read_manifest(manifest):
                prompt = root / shard.prompt_path
                prompt.parent.mkdir(parents=True, exist_ok=True)
                prompt.write_text("hello\n", encoding="utf-8")

            code = main(
                [
                    "run",
                    "--manifest",
                    str(manifest),
                    "--workdir",
                    str(root),
                    "--runner",
                    "shell",
                    "--shell-command",
                    python_command("import os; assert os.environ.get('AGENT_BATCH_SHARD_ID')"),
                    "--jobs",
                    "2",
                ]
            )
            self.assertEqual(code, 0)
            self.assertEqual([shard.status for shard in read_manifest(manifest)], ["succeeded", "succeeded"])


if __name__ == "__main__":
    unittest.main()
