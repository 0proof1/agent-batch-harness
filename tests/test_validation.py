from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from shardflow.core import (
    Shard,
    chunk,
    items_for_shard,
    plan_shards,
    read_items,
    read_manifest,
    update_manifest_status,
)


class ValidationTest(unittest.TestCase):
    def test_batch_size_must_be_positive(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least 1"):
            chunk([], 0)

    def test_items_require_output_fields(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.tsv"
            path.write_text("item_id\tsource\na\tin.txt\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing required item fields"):
                read_items(path)

    def test_duplicate_item_ids_are_rejected(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.tsv"
            path.write_text(
                "item_id\tsource\toutput\tqc\n"
                "a\tin/a\tout/a\tqc/a\n"
                "a\tin/b\tout/b\tqc/b\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "duplicate item_id"):
                read_items(path)

    def test_manifest_requires_all_fields(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "manifest.tsv"
            path.write_text("shard_id\tstatus\nshard_001\tpending\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "missing manifest fields"):
                read_manifest(path)

    def test_duplicate_shard_ids_are_rejected(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            items = root / "items.tsv"
            items.write_text(
                "item_id\tsource\toutput\tqc\tnotes\n"
                "a\tin/a\tout/a\tqc/a\t\n"
                "b\tin/b\tout/b\tqc/b\t\n",
                encoding="utf-8",
            )
            manifest = plan_shards(items, root / "_batches", 1)
            lines = manifest.read_text(encoding="utf-8").splitlines()
            manifest.write_text("\n".join([lines[0], lines[1], lines[1]]) + "\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate shard_id"):
                read_manifest(manifest)

    def test_invalid_manifest_status_is_rejected(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            items = root / "items.tsv"
            items.write_text("item_id\tsource\toutput\tqc\tnotes\na\tin\tout\tqc\t\n", encoding="utf-8")
            manifest = plan_shards(items, root / "_batches", 1)
            manifest.write_text(manifest.read_text(encoding="utf-8").replace("pending", "unknown"), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid statuses"):
                read_manifest(manifest)

    def test_status_update_rejects_unknown_status(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            items = root / "items.tsv"
            items.write_text("item_id\tsource\toutput\tqc\tnotes\na\tin\tout\tqc\t\n", encoding="utf-8")
            manifest = plan_shards(items, root / "_batches", 1)
            with self.assertRaisesRegex(ValueError, "invalid shard status"):
                update_manifest_status(manifest, "shard_001", "unknown")

    def test_item_range_must_exist(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.tsv"
            path.write_text("item_id\tsource\toutput\tqc\tnotes\na\tin\tout\tqc\t\n", encoding="utf-8")
            shard = Shard("shard_001", "prompt", 1, "missing", "missing", "pending", "log")
            with self.assertRaisesRegex(ValueError, "not present"):
                items_for_shard(read_items(path), shard)

    def test_item_count_must_match_manifest(self) -> None:
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "items.tsv"
            path.write_text("item_id\tsource\toutput\tqc\tnotes\na\tin\tout\tqc\t\n", encoding="utf-8")
            shard = Shard("shard_001", "prompt", 2, "a", "a", "pending", "log")
            with self.assertRaisesRegex(ValueError, "item count mismatch"):
                items_for_shard(read_items(path), shard)


if __name__ == "__main__":
    unittest.main()
