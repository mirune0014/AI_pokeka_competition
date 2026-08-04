import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace


MODULE_PATH = Path(__file__).resolve().parents[3] / "infrastructure" / "tools" / "run_local_battle.py"
SPEC = importlib.util.spec_from_file_location("run_local_battle", MODULE_PATH)
run_local_battle = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(run_local_battle)


def test_compact_option_keeps_attachment_target_coordinates():
    option = {
        "type": 8,
        "area": 2,
        "index": 4,
        "inPlayArea": 5,
        "inPlayIndex": 2,
        "inPlayPlayerIndex": 0,
        "energyIndex": 1,
        "serial": 999,
        "private": "drop",
    }

    compact = run_local_battle.compact_option(option)

    assert compact == {
        "type": 8,
        "area": 2,
        "index": 4,
        "inPlayArea": 5,
        "inPlayIndex": 2,
        "inPlayPlayerIndex": 0,
        "energyIndex": 1,
    }


def test_acting_hand_ids_keeps_only_current_players_known_hand():
    obs = {
        "current": {
            "yourIndex": 1,
            "players": [
                {"hand": None},
                {"hand": [{"id": 380}, {"id": 387}]},
            ],
        }
    }

    assert run_local_battle.acting_hand_ids(obs) == [380, 387]


def test_card_id_handles_missing_selection_source():
    assert run_local_battle.card_id({"id": 380}) == 380
    assert run_local_battle.card_id(None) is None
    assert run_local_battle.card_id({}) is None


def test_visible_card_ids_preserves_hidden_positions():
    assert run_local_battle.visible_card_ids([{"id": 381}, None, {"id": 383}]) == [381, None, 383]


def test_validation_records_are_canonical_persisted_and_hashed(tmp_path):
    class ValidationModule:
        def __init__(self):
            self.batches = [
                [
                    {"schema_version": "test_v1", "sequence": 0, "route": "A"},
                    {"schema_version": "test_v1", "sequence": 1, "route": "B"},
                ],
                [{"schema_version": "test_v1", "sequence": 2, "route": "C"}],
            ]

        @staticmethod
        def validation_status():
            return {
                "telemetry_enabled": True,
                "telemetry_health": {"healthy": True},
                "run_failed": False,
            }

        def drain_validation_telemetry(self):
            records = self.batches.pop(0) if self.batches else []
            return {
                "status": self.validation_status(),
                "telemetry": {
                    "records": records,
                    "lifetime_health": {"healthy": True},
                },
            }

        def finalize_validation_game(self, _reason):
            return self.validation_status()

    monitor = run_local_battle.AgentValidationMonitor(
        [SimpleNamespace(module=ValidationModule())]
    )
    monitor.after_callback(0)
    monitor.finalize_all("GAME_END")

    records = monitor.records
    assert [record["sequence"] for record in records] == [0, 1, 2]
    assert [record["agent_index"] for record in records] == [0, 0, 0]
    assert [record["drain_sequence"] for record in records] == [0, 0, 1]
    assert [record["drain_record_index"] for record in records] == [0, 1, 0]
    assert "records" not in monitor.summary()

    metadata = run_local_battle.write_validation_trace(tmp_path, 7, records)
    path = Path(metadata["validation_trace"])
    payload = path.read_bytes()
    lines = payload.decode("utf-8").splitlines()
    assert path.name == "game_0007.validation.jsonl"
    assert metadata["validation_trace_record_count"] == 3
    assert metadata["validation_trace_sha256"] == hashlib.sha256(payload).hexdigest()
    assert [json.loads(line)["sequence"] for line in lines] == [0, 1, 2]
    assert lines[0] == run_local_battle.canonical_json_line(records[0]).rstrip("\n")


def test_compact_logs_keeps_public_serial_receipt_fields_only():
    compact = run_local_battle.compact_logs(
        [
            {
                "type": 6,
                "playerIndex": 0,
                "serial": 10,
                "serialTarget": 20,
                "serialBench": 30,
                "serialBefore": 40,
                "serialAfter": 50,
                "private": "drop",
            }
        ]
    )

    assert compact == [
        {
            "type": 6,
            "playerIndex": 0,
            "serial": 10,
            "serialTarget": 20,
            "serialBench": 30,
            "serialBefore": 40,
            "serialAfter": 50,
        }
    ]
