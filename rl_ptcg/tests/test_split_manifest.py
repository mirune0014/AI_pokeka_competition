import copy
import json
import random
from pathlib import Path
import tempfile
import unittest

from rl_ptcg.split_manifest import (
    PROTECTED_FIELDS,
    SplitItem,
    _build_split_manifest,
    build_split_manifest,
    load_split_manifest,
    validate_split_manifest,
    write_split_manifest,
)


SOURCE_SHA = "ab" * 32


def item(name, *, episode=None, submission=None, style=None, period=None, seed=None, deck=None):
    return SplitItem(
        item_id=name,
        episode_id=episode or f"episode-{name}",
        submission_version=submission or f"submission-{name}",
        style_family=style or f"style-{name}",
        date_period=period or f"period-{name}",
        seed=seed or f"seed-{name}",
        deck_variant=deck or f"deck-{name}",
        archetype="archaludon",
    )


class SplitManifestTests(unittest.TestCase):
    def test_shared_protected_values_form_transitive_components(self):
        values = [
            item("a", submission="submission-shared"),
            item("b", submission="submission-shared", period="period-link"),
            item("c", period="period-link"),
            item("d"),
        ]
        manifest = build_split_manifest(
            values, source_dataset_sha256=SOURCE_SHA, seed="split-v1",
            component_fields=PROTECTED_FIELDS,
        )
        rows = {row["item_id"]: row for row in manifest["items"]}
        self.assertEqual(rows["a"]["component_id"], rows["b"]["component_id"])
        self.assertEqual(rows["b"]["component_id"], rows["c"]["component_id"])
        self.assertNotEqual(rows["a"]["component_id"], rows["d"]["component_id"])
        self.assertEqual(rows["a"]["split"], rows["c"]["split"])
        self.assertTrue(manifest["overlap_audit"]["passed"])

    def test_default_components_do_not_collapse_on_shared_style_or_date(self):
        values = [
            item("a", style="shared-style", period="shared-period"),
            item("b", style="shared-style", period="shared-period"),
        ]
        manifest = build_split_manifest(values, source_dataset_sha256=SOURCE_SHA, seed="split-v1")
        self.assertEqual(2, manifest["component_count"])
        self.assertEqual(
            ["episode_id", "submission_version", "seed", "deck_variant"],
            manifest["component_fields"],
        )
        self.assertGreaterEqual(manifest["overlap_audit"]["informational_overlap_counts"]["style_family"], 1)

    def test_episode_decisions_and_holdout_family_never_cross_splits(self):
        values = [
            item("e1-d0", episode="episode-1", submission="s1", style="regular", period="p1", seed="r1", deck="d1"),
            item("e1-d1", episode="episode-1", submission="s1", style="regular", period="p1", seed="r1", deck="d1"),
            item("h1", style="held-out"),
            item("h2", style="held-out"),
        ]
        manifest = build_split_manifest(
            values,
            source_dataset_sha256=SOURCE_SHA,
            seed="split-v1",
            development_fraction=0.0,
            blind_fraction=0.0,
            holdout_style_families=["held-out"],
        )
        rows = {row["item_id"]: row for row in manifest["items"]}
        self.assertEqual("train", rows["e1-d0"]["split"])
        self.assertEqual(rows["e1-d0"]["component_id"], rows["e1-d1"]["component_id"])
        self.assertEqual("policy_family_holdout", rows["h1"]["split"])
        self.assertEqual("policy_family_holdout", rows["h2"]["split"])

    def test_manifest_is_input_order_independent_and_hash_bound(self):
        values = [item(str(index)) for index in range(12)]
        first = build_split_manifest(values, source_dataset_sha256=SOURCE_SHA, seed="split-v1")
        shuffled = list(values)
        random.Random(88).shuffle(shuffled)
        second = build_split_manifest(shuffled, source_dataset_sha256=SOURCE_SHA, seed="split-v1")
        self.assertEqual(first, second)
        self.assertEqual(first, validate_split_manifest(first))

        tampered = copy.deepcopy(first)
        tampered["items"][0]["split"] = "blind"
        with self.assertRaisesRegex(ValueError, "SHA256"):
            validate_split_manifest(tampered)

    def test_explicit_time_and_style_holdouts_are_audited(self):
        values = [
            item("train", period="p-train"),
            item("blind", period="p-blind"),
            item("development", period="p-development"),
            item("style", style="held-out", period="p-train"),
        ]
        manifest = build_split_manifest(
            values,
            source_dataset_sha256=SOURCE_SHA,
            seed="split-v1",
            development_fraction=0.0,
            blind_fraction=0.0,
            holdout_style_families=["held-out"],
            blind_date_periods=["p-blind"],
            development_date_periods=["p-development"],
        )
        rows = {row["item_id"]: row["split"] for row in manifest["items"]}
        self.assertEqual("train", rows["train"])
        self.assertEqual("blind", rows["blind"])
        self.assertEqual("development", rows["development"])
        self.assertEqual("policy_family_holdout", rows["style"])
        self.assertTrue(manifest["overlap_audit"]["passed"])

    def test_legacy_all_field_manifest_remains_reproducible(self):
        legacy = _build_split_manifest(
            [item("a"), item("b")],
            source_dataset_sha256=SOURCE_SHA,
            seed="legacy-v1",
            development_fraction=0.15,
            blind_fraction=0.15,
            holdout_style_families=(),
            blind_date_periods=(),
            development_date_periods=(),
            component_fields=PROTECTED_FIELDS,
            legacy_format=True,
        )
        self.assertNotIn("component_fields", legacy)
        self.assertEqual(legacy, validate_split_manifest(legacy))

    def test_write_once_manifest_round_trip_and_replacement_guard(self):
        first = build_split_manifest([item("a"), item("b")], source_dataset_sha256=SOURCE_SHA, seed="split-v1")
        second = build_split_manifest([item("a"), item("b")], source_dataset_sha256=SOURCE_SHA, seed="split-v2")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "blind_split.json"
            write_split_manifest(path, first)
            write_split_manifest(path, first)
            self.assertEqual(first, load_split_manifest(path))
            with self.assertRaisesRegex(FileExistsError, "frozen"):
                write_split_manifest(path, second)

    def test_missing_group_metadata_duplicate_ids_and_bad_fractions_fail(self):
        bad = item("a").__dict__.copy()
        bad["date_period"] = ""
        with self.assertRaisesRegex(ValueError, "date_period"):
            build_split_manifest([bad], source_dataset_sha256=SOURCE_SHA, seed="split-v1")
        with self.assertRaisesRegex(ValueError, "unique"):
            build_split_manifest([item("a"), item("a")], source_dataset_sha256=SOURCE_SHA, seed="split-v1")
        with self.assertRaisesRegex(ValueError, "must not exceed"):
            build_split_manifest(
                [item("a")], source_dataset_sha256=SOURCE_SHA, seed="split-v1",
                development_fraction=0.6, blind_fraction=0.5,
            )

    def test_serialized_manifest_contains_no_implicit_random_state(self):
        manifest = build_split_manifest([item("a")], source_dataset_sha256=SOURCE_SHA, seed="split-v1")
        encoded = json.dumps(manifest, sort_keys=True)
        self.assertNotIn("timestamp", encoded)
        self.assertNotIn("python_hash", encoded)


if __name__ == "__main__":
    unittest.main()
