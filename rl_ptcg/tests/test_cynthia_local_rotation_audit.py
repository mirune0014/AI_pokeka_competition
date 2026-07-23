import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TOOLS_DIR = ROOT / "tools"
if str(TOOLS_DIR) not in sys.path:
    sys.path.insert(0, str(TOOLS_DIR))


def load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class LocalRotationAuditTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.battle = load_module(ROOT / "tools" / "run_local_battle.py", "run_local_battle_snapshot_test")
        cls.audit = load_module(ROOT / "tools" / "audit_cynthia_local_rotation.py", "local_rotation_audit_test")

    def test_player_snapshot_keeps_attachment_telemetry(self):
        obs = {
            "current": {
                "turn": 7,
                "result": -1,
                "players": [{
                    "deckCount": 12,
                    "handCount": 4,
                    "prize": [None, None],
                    "active": [{
                        "id": 381,
                        "hp": 110,
                        "maxHp": 400,
                        "energyCards": [{"id": 6}, {"id": 20}],
                        "tools": [{"id": 1173}],
                    }],
                    "bench": [{
                        "id": 381,
                        "hp": 330,
                        "maxHp": 330,
                        "energies": [6, 6],
                        "tools": [],
                    }],
                }],
            }
        }
        snapshot = self.battle.player_snapshot(obs)
        self.assertEqual(snapshot["p0_active_max_hp"], 400)
        self.assertEqual(snapshot["p0_active_energy_ids"], [6, 20])
        self.assertEqual(snapshot["p0_active_tool_ids"], [1173])
        self.assertEqual(snapshot["p0_bench_energy"], [2])
        self.assertEqual(snapshot["p0_bench_energy_ids"], [[6, 6]])

    def test_audit_extracts_only_legal_ready_rotation(self):
        qualifying = {
            "game": 2,
            "step": 30,
            "player": 1,
            "action": [1],
            "options": [{"type": 14}, {"type": 9}],
            "snapshot": {
                "turn": 12,
                "p1_prizes": 3,
                "p1_active": 381,
                "p1_active_hp": 100,
                "p1_active_max_hp": 400,
                "p1_active_energy": 2,
                "p1_active_energy_ids": [6, 20],
                "p1_active_tool_ids": [1173],
                "p1_bench": [381, 342],
                "p1_bench_hp": [330, 180],
                "p1_bench_energy": [2, 0],
            },
        }
        no_ready_backup = json.loads(json.dumps(qualifying))
        no_ready_backup["step"] = 31
        no_ready_backup["snapshot"]["p1_bench_energy"] = [1, 0]

        with tempfile.TemporaryDirectory() as tmp:
            trace = Path(tmp) / "game.jsonl"
            trace.write_text(
                "\n".join(json.dumps(row) for row in (qualifying, no_ready_backup)) + "\n",
                encoding="utf-8",
            )
            rows = self.audit.audit_trace(trace, 9)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["active_damage"], 300)
        self.assertEqual(rows[0]["ready_bench_energy"], "2")
        self.assertTrue(rows[0]["selected_retreat"])


if __name__ == "__main__":
    unittest.main()
