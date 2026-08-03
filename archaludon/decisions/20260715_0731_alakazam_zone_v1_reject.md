# Decision: reject Alakazam Neutralization Zone v1

- Decision time: `2026-07-15 07:31:18 +09:00`
- Decision: `REJECT`
- Kaggle submission: `NO`
- Daily submission slots consumed by this candidate: `0`

## Frozen comparison

- Hypothesis: replace Enriching Energy (`13`) with Neutralization Zone
  (`1247`) and play the stadium only against public, ready-or-one-attachment
  Pokemon ex pressure while preserving an immediate Powerful Hand knockout.
- Immutable specification:
  `autonomous_gold_20260715/evaluations/alakazam_zone_v1_seed2026071501/EVALUATION_SPEC.md`
  - SHA256 `B9465E7DDB8A3816F558434EF82CE784D3D0553FD66E54D56B456506B0FB5408`
- Checked paired output:
  `autonomous_gold_20260715/evaluations/alakazam_zone_v1_seed2026071501/full_run/paired_results.csv`
  - SHA256 `027EBDC971EAF7D482224352D90DE1626A1FA704FE6E7A55E35E651EEBA20511`
- Runner report:
  `autonomous_gold_20260715/evaluations/alakazam_zone_v1_seed2026071501/full_run/report.json`
  - SHA256 `655739AA7D8D458BB2D0A358333FA249DB77C6267EF4F777403F4B598778B3BF`
- Manifest:
  `autonomous_gold_20260715/evaluations/alakazam_zone_v1_seed2026071501/full_run/manifest.jsonl`
  - SHA256 `C1C536425CB91AD2D96A58F75C8BA9194DA18D6481A39F3BF7456FF6B4F033D3`
- Independent numerical audit:
  `autonomous_gold_20260715/evaluations/alakazam_zone_v1_seed2026071501/numerical_audit/numerical_audit.json`
  - SHA256 `27E0D777DF100CCC498DE770FD3CA6337EF016D4F07972EB2A544AE5C6D26485`

## Root-verified evidence

- Integrity: 640 unique paired keys, 48/48 processes exited zero, 1,920
  raw records, and zero action errors, max-step hits, duplicate-control
  mismatches, schedule mismatches, or runner/audit discrepancies.
- Total: `369 -> 403`, `+34/640`; 82 gains and 48 losses.
- Seats: `+13/320` and `+21/320`.
- Paired normal 95% confidence interval: `[0.0184234, 0.0878266]`.
- Target panel: `257 -> 300`, `+43/400`.
- Historical-Silver anchor: `32 -> 54`, `+22/80`.
- Adjacent panel: `112 -> 103`, `-9/240`.
- Great Tusk: `16 -> 11`, `-5/80`.
- Alakazam Rmy: `60 -> 55`, `-5/80`.

## Gate result

Gates 1, 2, 3, and 5 passed. Gate 4 was predeclared to require the adjacent
panel to be no worse than `-4/240` and every adjacent opponent to be no worse
than `-4/80`. The candidate failed both parts: adjacent was `-9/240`, while
Great Tusk and Alakazam Rmy were each `-5/80`. The conditional trace gate was
therefore not reached and was not run.

The Sol-Ultra strategy judge issued an unambiguous `REJECT` and prohibited
using a Kaggle slot. The target-side gain is retained as research evidence;
it does not override the frozen safety gate. No causal mechanism beyond the
observed matchup asymmetry is asserted from this outcome-only comparison.
