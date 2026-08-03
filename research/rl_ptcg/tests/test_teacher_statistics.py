import unittest

from research.rl_ptcg.teacher_statistics import TeacherStatisticsError, summarize_teacher_batches


def rows(values, state="s", batch=0, episode="e", baseline="a", policy=0, world="w"):
    return [{"state_id": state, "batch_id": batch, "episode_id": episode, "baseline_action": baseline,
             "particle_index": 0, "opponent_policy_index": policy, "hypothesis_signature": "h",
             "hidden_world_id": world, "action": action, "terminal_utility": value}
            for action, value in values.items()]


class TeacherStatisticsTests(unittest.TestCase):
    def test_rejects_exact_state_set_mismatch(self):
        data = rows({"a": 0, "b": 1}, state="one", batch=0) + rows({"a": 0, "b": 1}, state="two", batch=1)
        with self.assertRaisesRegex(TeacherStatisticsError, "state-set"):
            summarize_teacher_batches(data)

    def test_rejects_missing_paired_baseline(self):
        with self.assertRaisesRegex(TeacherStatisticsError, "baseline"):
            summarize_teacher_batches(rows({"b": 1}))

    def test_top1_and_sign_agreement_with_baseline_tie(self):
        data = rows({"a": 1, "b": 1}, batch=0) + rows({"a": 0, "b": 1}, batch=1)
        report = summarize_teacher_batches(data, 5, 9)
        self.assertEqual(0.0, report["batch_top1_agreement"])
        self.assertEqual(0.0, report["advantage_sign_agreement"])
        self.assertEqual(0, report["high_margin_state_pairs"])
        self.assertIsNone(report["high_margin_batch_top1_agreement"])

    def test_high_margin_top1_requires_margin_in_both_batches(self):
        data = rows({"a": 0, "b": 1}, state="high", batch=0)
        data += rows({"a": 0, "b": 1}, state="high", batch=1)
        data += rows({"a": 0, "b": 0.1}, state="low", batch=0)
        data += rows({"a": 0, "b": 1}, state="low", batch=1)
        report = summarize_teacher_batches(data, 3)
        self.assertEqual(1, report["high_margin_state_pairs"])
        self.assertEqual(1.0, report["high_margin_batch_top1_agreement"])

    def test_outside_top3_positive_lcb_must_hold_in_both_batches(self):
        data = rows({"a": 0, "b": 1}, batch=0) + rows({"a": 0, "b": 1}, batch=1)
        for item in data:
            item["outside_rule_top3"] = item["action"] == "b"
        report = summarize_teacher_batches(data, 3)
        self.assertEqual(1, report["positive_lcb_outside_top3_states"])
        self.assertEqual(1.0, report["positive_lcb_outside_top3_rate"])

    def test_vpi_zero_and_positive_reversal(self):
        zero = summarize_teacher_batches(rows({"a": 0, "b": 1}), 3)
        reversal = rows({"a": 1, "b": 0}, world="w1") + rows({"a": 0, "b": 1}, world="w2")
        positive = summarize_teacher_batches(reversal, 3)
        self.assertEqual(0.0, zero["mean_vpi"])
        self.assertGreater(positive["mean_vpi"], 0.0)

    def test_variance_zero_and_nonzero(self):
        zero = summarize_teacher_batches(rows({"a": 0, "b": 1}), 3)
        varying = rows({"a": 0, "b": 1}, policy=0, world="w1") + rows({"a": 0, "b": 3}, policy=1, world="w1")
        report = summarize_teacher_batches(varying, 3)
        self.assertEqual(0.0, zero["between_policy_variance"])
        self.assertEqual(0.0, zero["within_policy_hidden_world_variance"])
        self.assertGreater(report["between_policy_variance"], 0.0)

    def test_accepts_balanced_policies_with_distinct_particle_and_world_ids(self):
        data = []
        for policy, particle, world in ((0, 0, "w0"), (1, 1, "w1")):
            batch = rows({"a": 0, "b": 1}, policy=policy, world=world)
            for row in batch:
                row["particle_index"] = particle
            data += batch
        report = summarize_teacher_batches(data, 3)
        self.assertEqual(1, report["state_count"])

    def test_rejects_unbalanced_policy_particle_counts(self):
        data = rows({"a": 0, "b": 1}, policy=0, world="w0")
        data += rows({"a": 0, "b": 1}, policy=1, world="w1")
        extra = rows({"a": 0, "b": 1}, policy=1, world="w2")
        for row in extra:
            row["particle_index"] = 2
        with self.assertRaisesRegex(TeacherStatisticsError, "unbalanced"):
            summarize_teacher_batches(data + extra)

    def test_bootstrap_reproducible_and_resamples_clusters(self):
        data = []
        for state, batch, episode, advantage in (
            ("s1", 0, "e1", 0), ("s1", 1, "e1", 2),
            ("s2", 0, "e2", 4), ("s2", 1, "e2", 4),
        ):
            data += rows({"a": 0, "b": advantage}, state=state, batch=batch, episode=episode)
        one = summarize_teacher_batches(data, 25, 17)["bootstrap"]
        two = summarize_teacher_batches(data, 25, 17)["bootstrap"]
        self.assertEqual(one, two)
        self.assertGreater(len(set(one["draws"])), 1)


if __name__ == "__main__":
    unittest.main()
