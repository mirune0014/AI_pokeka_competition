from __future__ import annotations

from copy import deepcopy
import unittest

from archaludon_rl.public_state import (
    canonical_public_bytes,
    project_public_state,
)
from archaludon_rl.encoders import encode_state
from archaludon_rl.effect_features import EffectCatalog, extract_effect_features
from archaludon_rl.encoders import encode_action
from archaludon_rl.semantic_action import semantic_options

from .helpers import observation


class PublicSemanticTests(unittest.TestCase):
    def test_hidden_state_noninterference(self):
        first = observation()
        second = deepcopy(first)
        second["search_begin_input"] = "different opaque bytes"
        second["rng_state"] = [999]
        second["unknown_future_hidden_field"] = {"leak": "changed"}
        second["select"]["deck"].reverse()
        second["current"]["players"][0]["prize"] = [{"id": 9999}] * 6
        second["current"]["players"][1]["prize"] = [{"id": 8888}] * 6
        second["current"]["players"][1]["hand"] = [{"id": 4321, "serial": 1}]
        self.assertEqual(canonical_public_bytes(first), canonical_public_bytes(second))
        self.assertEqual(
            encode_state(project_public_state(first)),
            encode_state(project_public_state(second)),
        )
        first_projection = project_public_state(first)
        second_projection = project_public_state(second)
        first_options = semantic_options(first)
        second_options = semantic_options(second)
        self.assertEqual(
            [
                encode_action(
                    option,
                    extract_effect_features(
                        first_projection, option, EffectCatalog()
                    ),
                )
                for option in first_options
            ],
            [
                encode_action(
                    option,
                    extract_effect_features(
                        second_projection, option, EffectCatalog()
                    ),
                )
                for option in second_options
            ],
        )
        projection = project_public_state(first)
        encoded = str(projection)
        self.assertNotIn("opaque", encoded)
        self.assertNotIn("777", encoded)
        self.assertNotIn("600", encoded)

    def test_state_encoder_uses_visible_card_context_but_not_serials(self):
        first = observation()
        visible_change = deepcopy(first)
        visible_change["current"]["players"][0]["hand"][1]["id"] = 999
        serial_only = deepcopy(first)
        serial_only["current"]["players"][0]["hand"][0]["serial"] = 999999
        first_vector = encode_state(project_public_state(first))
        self.assertNotEqual(
            first_vector,
            encode_state(project_public_state(visible_change)),
        )
        self.assertEqual(
            first_vector,
            encode_state(project_public_state(serial_only)),
        )

    def test_seat_mirror_canonicalization(self):
        first = observation(your_index=0)
        mirrored = deepcopy(first)
        mirrored["current"]["yourIndex"] = 1
        mirrored["current"]["firstPlayer"] = 1
        mirrored["current"]["players"] = [
            deepcopy(first["current"]["players"][1]),
            deepcopy(first["current"]["players"][0]),
        ]
        # Remap physical owners while keeping relative roles identical.
        for physical, player in enumerate(mirrored["current"]["players"]):
            for zone in ("active", "bench", "discard", "hand"):
                for item in player.get(zone) or ():
                    item["playerIndex"] = physical
            for item in player.get("active") or ():
                for child_zone in ("energyCards", "tools", "preEvolution"):
                    for child in item.get(child_zone) or ():
                        child["playerIndex"] = physical
        mirrored["current"]["stadium"][0]["playerIndex"] = 1
        mirrored["logs"][0]["playerIndex"] = 1
        self.assertEqual(canonical_public_bytes(first), canonical_public_bytes(mirrored))

    def test_option_reorder_identity_equivariance_and_card_resolution(self):
        first = observation()
        second = deepcopy(first)
        second["select"]["option"].reverse()
        left = semantic_options(first)
        right = semantic_options(second)
        self.assertEqual({item.identity for item in left}, {item.identity for item in right})
        left_play = next(item for item in left if item.option_type == 7)
        right_play = next(item for item in right if item.option_type == 7)
        self.assertEqual(left_play.source_card_id, 100)
        self.assertNotEqual(left_play.engine_index, right_play.engine_index)

    def test_distinct_same_card_targets_receive_distinct_action_vectors(self):
        obs = observation(
            options=[
                {
                    "type": 8,
                    "area": 2,
                    "index": 0,
                    "inPlayArea": 5,
                    "inPlayIndex": 0,
                },
                {
                    "type": 8,
                    "area": 2,
                    "index": 0,
                    "inPlayArea": 5,
                    "inPlayIndex": 1,
                },
            ]
        )
        duplicate = deepcopy(obs["current"]["players"][0]["bench"][0])
        duplicate["serial"] = 999
        duplicate["hp"] = 40
        duplicate["energies"] = []
        obs["current"]["players"][0]["bench"].append(duplicate)
        projection = project_public_state(obs)
        options = semantic_options(obs)
        vectors = [
            encode_action(
                option,
                extract_effect_features(projection, option, EffectCatalog()),
            )
            for option in options
        ]
        self.assertNotEqual(options[0].identity, options[1].identity)
        self.assertNotEqual(vectors[0], vectors[1])


if __name__ == "__main__":
    unittest.main()
