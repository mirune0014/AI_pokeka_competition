import importlib.util
from pathlib import Path
import sys


MODULE_PATH = Path(__file__).resolve().parents[3] / "infrastructure" / "tools" / "extract_episode_decks.py"
if str(MODULE_PATH.parent) not in sys.path:
    sys.path.insert(0, str(MODULE_PATH.parent))
SPEC = importlib.util.spec_from_file_location("extract_episode_decks", MODULE_PATH)
module = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(module)


def test_specific_control_shells_beat_generic_ogerpon_marker():
    assert module.classify([112, 117, 344, 345]) == "crustle_munkidori_control"
    assert module.classify([117, 414, 506, 521]) == "cubchoo_articuno_control"
    assert (
        module.classify([96, 272, 344, 345])
        == "teal_ogerpon_clefairy_crustle"
    )


def test_generic_ogerpon_remains_generic_without_specific_shell():
    assert module.classify([95, 96, 99]) == "ogerpon_toolbox"


def test_partial_specific_markers_do_not_create_false_positive():
    assert module.classify([272, 335, 55]) == "unknown"
    assert module.classify([344, 345, 343]) == "crustle_control"
    assert module.classify([344, 345, 756]) == "kangaskhan_crustle"
    assert module.classify([58, 344, 345]) == "great_tusk_crustle"
