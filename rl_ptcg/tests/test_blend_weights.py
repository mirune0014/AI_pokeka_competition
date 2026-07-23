import unittest

from rl_ptcg.blend_weights import blend_weights


class BlendWeightTests(unittest.TestCase):
    def test_blends_union_and_prunes_small_values(self):
        blended = blend_weights([
            (0.75, {"a": 2.0, "b": 1.0}),
            (0.25, {"a": -2.0, "c": 4.0}),
        ], min_abs=0.8)
        self.assertEqual({"a": 1.0, "c": 1.0}, blended)


if __name__ == "__main__":
    unittest.main()
