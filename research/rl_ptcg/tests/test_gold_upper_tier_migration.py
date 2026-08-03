import copy
import unittest

from research.rl_ptcg.gold_upper_tier_migration import normalize_migrated_state


class UpperTierMigrationTests(unittest.TestCase):
    def state(self):
        return {
            "schema_version": "old",
            "own_deck": {"inventory_source": {
                "source_path": "C:\\workspace\\inventory.csv",
                "source_row_id": "row",
                "source_sha256": "a" * 64,
            }},
            "candidates": [{"semantic_id": "one"}],
        }

    def test_only_declared_provenance_fields_are_normalized(self):
        old = self.state()
        new = copy.deepcopy(old)
        new["schema_version"] = "new"
        new["own_deck"]["inventory_source"]["source_path"] = "inventory.csv"
        self.assertEqual(normalize_migrated_state(old), normalize_migrated_state(new))
        new["candidates"][0]["semantic_id"] = "changed"
        self.assertNotEqual(normalize_migrated_state(old), normalize_migrated_state(new))

    def test_missing_inventory_provenance_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "inventory provenance"):
            normalize_migrated_state({"schema_version": "old"})


if __name__ == "__main__":
    unittest.main()
