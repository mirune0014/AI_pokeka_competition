import unittest

from research.rl_ptcg.seeded_engine_linux import (
    _replace_once,
    patch_api_header,
    patch_api_py,
    patch_export_cpp,
    patch_game_py,
    patch_sim_py,
)


class SeededEngineLinuxTests(unittest.TestCase):
    def test_replace_once_is_fail_closed(self):
        self.assertEqual("left new right", _replace_once("left old right", "old", "new", "x"))
        with self.assertRaisesRegex(ValueError, "found 0"):
            _replace_once("none", "old", "new", "x")
        with self.assertRaisesRegex(ValueError, "found 2"):
            _replace_once("old old", "old", "new", "x")

    def test_api_header_patch_adds_seeded_entry_points(self):
        source = (
            "inline StartData ApiBattleStart(int* cards) {\n"
            "\tstd::random_device rd;\n\tGameConfig config = {};\n\tconfig.seed = rd();\n"
            "\tconfig.recordLog = true;\n\tconfig.deviceRand = true;\n"
            "\tdata->init(config);\n\tstd::seed_seq seq{ rd(), rd(), rd(), rd() };\n"
            "\tdata->game.rng = std::mt19937(seq);\n\treturn data;\n}\n\n"
            "inline ApiData* ApiAgentStart() {\n\treturn data;\n}\n\n"
            "inline void ApiBattleFinish(ApiData* data) {\n"
        )
        patched = patch_api_header(source)
        self.assertIn("ApiBattleStartSeeded", patched)
        self.assertIn("ApiAgentSeed", patched)
        self.assertNotIn("std::seed_seq", patched)

    def test_export_patch_adds_both_symbols(self):
        source = (
            "  GAME_API StartData BattleStart(int* cards) {\n"
            "    return ApiBattleStart(cards);\n  }\n\n"
            "  GAME_API ApiData* AgentStart() {\n"
            "    return ApiAgentStart();\n  }\n\n"
            "  GAME_API void BattleFinish(ApiData* data) {\n"
        )
        patched = patch_export_cpp(source)
        self.assertIn("BattleStartSeeded", patched)
        self.assertIn("AgentSeed", patched)

    def test_python_wrapper_patches_are_minimal(self):
        api = patch_api_py(
            "    return to_dataclass(obs, Observation)\n\n"
            "def search_begin(agent_observation: Observation,\n"
        )
        sim = patch_sim_py(
            "lib.BattleStart.restype = StartData\n"
            "lib.BattleStart.argtypes = [ctypes.POINTER(ctypes.c_int)]\n\n"
            "lib.AgentStart.restype = ctypes.c_void_p\n\n"
            "lib.BattleFinish.argtypes = [ctypes.c_void_p]\n"
        )
        game = patch_game_py(
            "def battle_start(deck0: list[int], deck1: list[int]) -> tuple[dict, StartData]:\n"
            "    start_data = lib.BattleStart(arg)\n"
        )
        self.assertIn("def search_seed", api)
        self.assertIn("lib.AgentSeed.argtypes", sim)
        self.assertIn("seed: int | None", game)


if __name__ == "__main__":
    unittest.main()
