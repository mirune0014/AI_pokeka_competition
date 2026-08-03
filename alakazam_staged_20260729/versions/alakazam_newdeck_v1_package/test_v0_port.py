from collections import Counter
import hashlib
import importlib.util
from pathlib import Path
import unittest

from cg.api import CardType, OptionType, SelectContext

import _cumulative_parent as policy
import main as entrypoint


HERE = Path(__file__).resolve().parent
EXPECTED_HASH = '4414e8995e50c7a00d4b6aa7d9229f63c1dff5261643ec7cd86c4e329113ed69'
EXPECTED_COUNTS = {
    741: 4, 742: 4, 743: 4, 305: 3, 66: 2, 140: 1, 343: 1,
    1152: 4, 1086: 4, 1079: 3, 1097: 1, 1129: 1, 1081: 4,
    1182: 3, 1184: 1, 1197: 3, 1231: 4, 1225: 4, 1266: 2,
    5: 2, 19: 4, 13: 1,
}


class V0PortTests(unittest.TestCase):
    def delegated_trace(self, obs, delegated_action):
        original = entrypoint._final_policy.agent
        calls = []

        def delegate(parent, parent_agent, raw):
            calls.append((parent, parent_agent, raw))
            return delegated_action

        entrypoint._final_policy.agent = delegate
        try:
            returned = entrypoint.agent(obs)
        finally:
            entrypoint._final_policy.agent = original
        self.assertIs(returned, delegated_action)
        self.assertEqual(calls, [(policy, policy.agent, obs)])
        return entrypoint.LAST_V0_PORT_TRACE

    def test_exact_normalized_deck(self):
        deck = [int(row) for row in (HERE / 'deck.csv').read_text().split()]
        payload = ' '.join(str(card_id) for card_id in sorted(deck)) + '\n'
        self.assertEqual(len(deck), 60)
        self.assertEqual(Counter(deck), Counter(EXPECTED_COUNTS))
        self.assertEqual(hashlib.sha256(payload.encode('ascii')).hexdigest(), EXPECTED_HASH)
        self.assertEqual((HERE / 'runtime' / 'deck.csv').read_bytes(),
                         (HERE / 'deck.csv').read_bytes())

    def test_deck_metadata_and_legality(self):
        self.assertTrue(all(card_id in policy.card_table for card_id in EXPECTED_COUNTS))
        self.assertTrue(all(count <= 4 for count in EXPECTED_COUNTS.values()))
        ace_count = sum(
            count for card_id, count in EXPECTED_COUNTS.items()
            if policy.card_table[card_id].aceSpec
        )
        self.assertEqual(ace_count, 1)
        self.assertEqual(policy.card_table[1184].cardType, CardType.SUPPORTER)
        self.assertEqual(policy.card_table[1197].cardType, CardType.SUPPORTER)
        self.assertEqual(policy.card_table[1266].cardType, CardType.STADIUM)

    def test_explicit_hold_and_forced_discard(self):
        self.assertEqual(policy.V0_GENERIC_HOLD, frozenset({1184, 1197, 1266}))
        for card_id in policy.V0_GENERIC_HOLD:
            self.assertEqual(
                policy._v0_generic_port_score(
                    OptionType.PLAY, SelectContext.MAIN, card_id
                ),
                (-1, 'V0_GENERIC_HOLD'),
            )
            self.assertEqual(
                policy._v0_generic_port_score(
                    OptionType.CARD, SelectContext.DISCARD, card_id
                ),
                (1, 'V0_GENERIC_FORCED_DISCARD'),
            )
        self.assertIsNone(
            policy._v0_generic_port_score(
                OptionType.PLAY, SelectContext.MAIN, policy.Boss_Orders
            )
        )

    def test_callback_trace_tags_main_hold_without_changing_action(self):
        obs = {
            'current': {
                'yourIndex': 0,
                'players': [
                    {'hand': [{'id': 1184}, {'id': 1197}, {'id': 1182}]},
                    {'hand': []},
                ],
            },
            'select': {
                'context': int(SelectContext.MAIN),
                'option': [
                    {'type': int(OptionType.PLAY), 'index': 0, 'playerIndex': -1, 'cardId': 0},
                    {'type': int(OptionType.PLAY), 'index': 1, 'playerIndex': -1, 'cardId': 0},
                    {'type': int(OptionType.END)},
                ],
            },
        }
        trace = self.delegated_trace(obs, [2])
        self.assertEqual(trace['selected_action'], [2])
        self.assertEqual(trace['reason_tags'], ['V0_GENERIC_HOLD'])
        self.assertEqual(trace['main_play_hold_card_ids'], [1184, 1197])
        self.assertEqual(trace['forced_discard_selected_card_ids'], [])
        self.assertEqual(trace['relevant_added_card_ids'], [1184, 1197])

    def test_callback_trace_tags_selected_forced_discard_only(self):
        obs = {
            'current': {
                'yourIndex': 0,
                'players': [
                    {'hand': [{'id': 1197}, {'id': 1182}, {'id': 1266}]},
                    {'hand': []},
                ],
            },
            'select': {
                'context': int(SelectContext.DISCARD),
                'option': [
                    {
                        'type': int(OptionType.CARD),
                        'area': int(policy.AreaType.HAND),
                        'index': 0,
                        'playerIndex': -1,
                        'cardId': 0,
                    },
                    {
                        'type': int(OptionType.CARD),
                        'area': int(policy.AreaType.HAND),
                        'index': 2,
                        'playerIndex': -1,
                        'cardId': 0,
                    },
                ],
            },
        }
        trace = self.delegated_trace(obs, [0])
        self.assertEqual(trace['selected_action'], [0])
        self.assertEqual(trace['reason_tags'], ['V0_GENERIC_FORCED_DISCARD'])
        self.assertEqual(trace['main_play_hold_card_ids'], [])
        self.assertEqual(trace['forced_discard_selected_card_ids'], [1197])
        self.assertEqual(trace['relevant_added_card_ids'], [1197])

    def test_runtime_exposes_dynamic_trace(self):
        runtime_path = HERE / 'runtime' / 'main.py'
        spec = importlib.util.spec_from_file_location('v0_runtime_trace_test', runtime_path)
        self.assertIsNotNone(spec)
        self.assertIsNotNone(spec.loader)
        runtime_entry = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(runtime_entry)
        sentinel = {'reason_tags': ['V0_GENERIC_HOLD']}
        runtime_entry._source_module.LAST_V0_PORT_TRACE = sentinel
        self.assertIs(runtime_entry.get_last_v0_port_trace(), sentinel)
        self.assertIs(runtime_entry.LAST_V0_PORT_TRACE, sentinel)

    def test_unrelated_python_is_byte_identical(self):
        baseline = (
            HERE.parents[2] / 'autonomous_gold_20260715' / 'candidates'
            / 'alakazam_active_dudunsparce_run_away_ko_transaction_v4'
        )
        for source in baseline.rglob('*.py'):
            relative = source.relative_to(baseline)
            if relative in {
                Path('_cumulative_parent.py'),
                Path('main.py'),
                Path('runtime/main.py'),
            }:
                continue
            self.assertEqual((HERE / relative).read_bytes(), source.read_bytes())


if __name__ == '__main__':
    unittest.main()
