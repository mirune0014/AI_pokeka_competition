import unittest

try:
    import torch
except ImportError:
    torch = None


@unittest.skipIf(torch is None, "PyTorch is optional for stdlib tests")
class PolicyValueTests(unittest.TestCase):
    def test_shapes_and_selection_loss(self):
        from research.rl_ptcg.encoding import SCHEMA
        from research.rl_ptcg.policy_value import ModelConfig, PolicyValueNet, selection_nll

        config = ModelConfig(
            tuple(SCHEMA.state_feature_names), tuple(SCHEMA.option_feature_names),
            hidden_dim=32, option_hidden_dim=16, card_embedding_dim=4,
        )
        model = PolicyValueNet(config)
        state = torch.zeros(2, len(SCHEMA.state_feature_names))
        options = torch.zeros(2, 3, len(SCHEMA.option_feature_names))
        mask = torch.tensor([[True, True, False], [True, True, True]])
        rules = torch.zeros(2, 3, 2)
        matchup_ids = torch.tensor([0, 2])
        opponent_deck = torch.tensor([[1] * 60, [2] * 60])
        logits, value = model(state, options, mask, rules, matchup_ids, opponent_deck)
        self.assertEqual((2, 3), tuple(logits.shape))
        self.assertEqual((2,), tuple(value.shape))
        loss = selection_nll(logits, mask, [[0], [1, 2]])
        self.assertTrue(torch.isfinite(loss))
        weighted = selection_nll(logits, mask, [[0], [1, 2]], torch.tensor([3.0, 1.0]))
        self.assertTrue(torch.isfinite(weighted))


if __name__ == "__main__":
    unittest.main()
