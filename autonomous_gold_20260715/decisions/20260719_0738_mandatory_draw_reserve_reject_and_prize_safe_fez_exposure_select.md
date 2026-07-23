# Reject mandatory-draw reserve v1; select prize-safe Fez exposure guard

Date: 2026-07-19 07:38 JST  
Owner: root

## Frozen disposition

Reject `alakazam_mandatory_draw_reserve_kadabra_resource_first_v1` for
promotion, mirroring, packaging, and Kaggle submission.  Retain it only as the
fully evaluated experimental parent for one isolated successor.

The exact 144-key Phase-0 comparison produced exact-v3 `86/144` and reserve-v1
`87/144`, with `1 gain / 0 regressions / 143 ties`.  The child therefore failed
the frozen total (`87 < 88`), paired-gain (`1 < 2`), and Historical-Silver
(`8 < 9`) gates.  All 576 executions and duplicate controls were valid.  The
sole gain preserved hand-size lethal; it did not convert a mandatory-draw
reserve.  No Hammer resource-first transaction activated.

Submission-critical evidence:

- root verification:
  `evaluations/alakazam_mandatory_draw_reserve_kadabra_resource_first_v1/fixed_phase0_20260719/ROOT_FIXED_PHASE0_VERIFICATION.md`
  (`CCB19E05BFEB59355A8265086D535FE13F73CCA3CE8666574D455F8548D88CCC`);
- final Sol-Ultra audit report:
  `evaluations/alakazam_mandatory_draw_reserve_kadabra_resource_first_v1/fixed_phase0_20260719/numerical_audit_sol_ultra_20260719/AUDIT_REPORT.md`
  (`14C653029A61D81728462E6171DD983137C3FDF2DF3B1E64DBD24DEC4488EA9C`);
- final audit calculator/result/manifest hashes:
  `E0ED998BF8DCC607E366C55E7A33CFC273C9C3AFFA79154034E4083930CE85CD`,
  `60B30BE5AC17B5851F5BBBFE04D12AF2D9C38EE87328F0025B3626E498645A68`,
  and `65CB1B0B7775143A8580CE46C5AC85985F5CE02EEA930788FD26FB1280502EFE`.

The audit records the stale-calculator-manifest discrepancy and the exact
rerun that corrected it; it must remain part of the evidence chain.

## Exact successor hypothesis

Implement exactly one public-state rule in a new isolated child:
`alakazam_prize_safe_fez_ex_exposure_guard_v1`.

Its parent is the evaluated reserve-v1 child, not exact-v3:

- parent source SHA-256:
  `3EFFE5520F6B1C2F8283B25ED4A76564BCB3305E213FFA87612BA4A7A2CF606B`;
- parent runtime SHA-256:
  `1E41868984188606AA879305CD5F66F59C8FE5235E94BC1B7CFB3B2013A1D04E`;
- legal 60-row deck SHA-256:
  `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`.

Behavioral claim: a saved deck card helps only if the agent does not
immediately turn it into a gustable two-Prize Fezandipiti-ex liability.

Compute the parent action first.  Override only when all of the following are
certified from complete public state:

1. the opponent has exactly two Prizes remaining;
2. every own Pokemon already in play is exactly one-Prize and Fezandipiti ex
   is not already in play;
3. the opponent Active and attachments are complete and uniquely identified;
4. the opponent Active is not Asleep, Paralyzed, or Confused;
5. its attached Energy currently pays a printed attack; and
6. a conservative fixed-damage calculation including recognized visible
   modifiers, Weakness, and Resistance certifies at least 210 damage to an
   otherwise unmodified Fezandipiti ex.

When certified, exclude Fezandipiti ex from optional search selections and,
at MAIN, mask only PLAY-Fez actions before resuming the parent's exact
next-safe ranking.  An optional Fez-only search may choose none only when
`minCount == 0`.  Do not override mandatory selections.  Clear or avoid stale
transaction latches.  Delegate unchanged on malformed/incomplete state,
variable or conditional damage, uncertain costs/modifiers, an existing
multi-Prize board, or an uncertified/ambiguous Fez-enabled same-turn win.

No opponent, seed, player-ID, hidden-Boss, or replay-specific predicate is
permitted.

## Required anchor and focused gates

The positive anchor is
`fresh_general|historical_silver|p0|2026101804`, steps 163--165.  The rule must
decline optional Dawn-to-Fez selection or block the later Fez PLAY, leaving a
one-Prize-only board so Boss -> Fez -> Metal Defender cannot take the final two
Prizes in that line.

Focused tests must cover both seats, repeated callbacks, exact 210 damage,
fixed damage and Energy payment, Weakness/Resistance and visible modifiers,
status-disabled and variable attackers, incomplete state, mandatory search,
existing multi-Prize exposure, non-Fez search, stale-latch safety, and a fully
certified Fez-enabled terminal exemption.  If a complete terminal certificate
cannot be proven, ambiguous terminal-looking states must delegate unchanged.

## Frozen evaluation gates

Use the same 144 keys, both seats, and exact-v3 anchor.  The successor must
achieve all of:

- at least `88/144`, at least `2 gains / 0 regressions` versus exact-v3;
- at least `1 incremental gain / 0 regressions` versus reserve-v1;
- Historical Silver at least `9/16`, P0 at least `45/72`, P1 at least `42/72`;
- known at least `44/72`, fresh at least `43/72`;
- Great Tusk at least `4/16`, Rmy at least `7/16`, Kangaskhan/Crustle at least
  `11/16`, and no opponent bucket below either reference;
- at least two authorized natural activations on distinct keys, with at least
  one paired gain beginning at the intended Fez-exposure prevention;
- no removed certified current-turn win and zero execution, action, max-step,
  duplicate, schedule, or hash defects.

Only a passing independently audited result may proceed to package, packaged
both-seat smoke, authenticated pre-write refresh, and root-only consideration
of one exploratory live slot.
