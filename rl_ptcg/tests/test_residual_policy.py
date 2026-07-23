import random
import unittest

from rl_ptcg.residual_policy import choose_residual, detect_public_matchup, option_features


class Item:
    def __init__(self, **values):
        self.__dict__.update(values)


def observation():
    mine = Item(deckCount=30, handCount=5, prize=[1, 2], bench=[Item(id=10)], active=[Item(id=30)])
    opp = Item(deckCount=28, handCount=4, prize=[3], bench=[Item(id=20)], active=[Item(id=40)])
    options = [Item(type="PLAY", cardId=100, attackId=None), Item(type="ATTACK", cardId=101, attackId=7), Item(type="PLAY", cardId=102, attackId=None)]
    return Item(current=Item(yourIndex=0, turn=5, players=[mine, opp]), select=Item(context="MAIN", option=options, maxCount=2))


class PolicyTests(unittest.TestCase):
    def test_public_matchup_detects_marnie_from_visible_board(self):
        observation = {
            "current": {"yourIndex": 0, "players": [
                {}, {"active": [{"id": 647}], "bench": [], "discard": []},
            ]}
        }
        self.assertEqual("marnie", detect_public_matchup(observation, "generic"))

    def test_public_matchup_detects_alakazam_from_basic(self):
        observation = {
            "current": {"yourIndex": 0, "players": [
                {}, {"active": [{"id": 741}], "bench": [], "discard": []},
            ]}
        }
        self.assertEqual("alakazam", detect_public_matchup(observation, "generic"))

    def callbacks(self):
        return (lambda obs, opt: ({100: 9, 101: 5, 102: 1}[opt.cardId], "rule"),
                lambda obs, opt: Item(id=opt.cardId, hp=120, damage=20, energy=[1]),
                lambda obs, opt: Item(id=200, hp=90, damage=10, energy=[1, 2]),
                lambda obs: "visible")

    def test_zero_weights_reproduce_rule_and_count(self):
        obs = observation()
        selected, gradient = choose_residual(obs, *self.callbacks(), [0, 1], {}, random.Random(3), top_n=2, training=False)
        self.assertEqual([0, 1], selected)
        self.assertEqual({}, gradient)

    def test_zero_weights_preserve_custom_rule_order_over_score_order(self):
        obs = observation()
        selected, gradient = choose_residual(
            obs, *self.callbacks(), [1], {}, random.Random(3), top_n=2, training=False)

        self.assertEqual([1], selected)
        self.assertEqual({}, gradient)

    def test_training_is_unique_and_has_gradient(self):
        obs = observation()
        selected, gradient = choose_residual(obs, *self.callbacks(), [0, 1], {}, random.Random(2), top_n=3, training=True)
        self.assertEqual(2, len(selected))
        self.assertEqual(2, len(set(selected)))
        self.assertTrue(gradient)

    def test_negative_unselected_option_cannot_be_discovered(self):
        obs = observation()
        obs.select.option[2].cardId = 999
        callbacks = (
            lambda obs, opt: ({100: 9, 101: 5, 999: -999999}[opt.cardId], "rule"),
            lambda obs, opt: Item(id=opt.cardId, hp=120, damage=20, energy=[1]),
            lambda obs, opt: Item(id=200, hp=90, damage=10, energy=[1, 2]),
            lambda obs: "visible",
        )
        selected, _ = choose_residual(
            obs, *callbacks, [0, 1], {"card_id=999": 3.0}, random.Random(4),
            top_n=3, training=False,
        )
        self.assertEqual([0, 1], selected)

    def test_features_are_visible_and_complete(self):
        obs = observation()
        feature = option_features(obs, obs.select.option[1], 5, 1, 3, *self.callbacks()[1:])
        for key in ("option_type=ATTACK", "select_context=MAIN", "matchup=visible", "card_id=101", "target_card_id=200", "attack_id=7", "own_hand=5", "opp_prize=1", "target_hp=100", "baseline_normalized", "matchup_card=visible:101", "matchup_target=visible:200", "matchup_context=visible:MAIN", "turn=6", "own_active=30", "opp_active=40", "matchup_context_card=visible:MAIN:101", "matchup_opp_active_card=visible:40:101", "matchup_context_type=visible:MAIN:ATTACK"):
            self.assertIn(key, feature)
        self.assertIn("public_matchup_turn_type=visible:6:ATTACK", feature)


if __name__ == "__main__":
    unittest.main()
