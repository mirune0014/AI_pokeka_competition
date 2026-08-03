# Cumulative Archaludon Mega Brave lock-repair judgment

Date: 2026-07-30 JST  
Scope: read-only final judgment and one pre-implementation repair selection

## Verdict

`REJECT_EXACT_CANDIDATE_FOR_LIVE_PROBE`

The exact cumulative candidate
`archaludon_cumulative_public_hierarchy_after_search_aware_v1`, SHA-256
`BE8C67E387CE4F36344A4B0DE610CAB9976BB07EE49200997D35CCC6C5DBF18A`,
is not eligible for an exploratory live probe. Numerical safety is not enough:
one Root-verified H4 action erased Mega Brave's public self-lock and immediately
changed a one-Prize diversion into the loss of a two-Prize Archaludon ex and
its three attached Metal.

Select exactly one repair hypothesis:

`H4_PUBLIC_MEGA_BRAVE_SELF_LOCK_VETO_V1`

> A nonterminal H4 Boss conversion is inadmissible when the opponent's tracked
> immediately preceding public attack is Mega Brave `983`. Switching that
> attacker off Active clears its attacker-local next-turn self-lock, so H4
> must preserve the exact parent's deliberate Boss-save/Active-attack line.

This is a public card-mechanic rule, not an opponent-id, seed, episode, serial,
or replay-future patch.

H3 v2 remains behaviorally unchanged in this repair child. Its Jumbo-versus-
Metal trade is a required live diagnostic, not a pre-probe blocker on the
current evidence. Combining an H3 resource amendment with the demonstrated H4
repair would confound two mechanisms and violate isolated-hypothesis testing.

## Verified facts used

- Exact historical-Silver formal parent:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`.
  Exact deck:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.
- Cumulative integration policy:
  `F8E81D3872C809477068E7C9B476302BE20C14001127EA308C4C80B4CB95BB66`.
  Integration selection:
  `2797D1C3B590E369FF3B38B20D2783ADAF1223FB0056759AAAEE69AFC453D942`.
- Root implementation verification:
  `F77963EC293EB862D185077A75238C181D7F485179BEB09D8800DB5FDC317E5E`.
  It reports all focused/component/collision/union/structure gates passing,
  zero invalid actions, exceptions, stale/two-owner states, and max-step hits.
- Root-verified combined fixed-760 CSV:
  `B58EBC8CF088B9B740651E8058478838D27EB1D0205A1E8CFB4C303276340BB4`;
  execution manifest:
  `E28E458C456A7F1259C5781F2CD82C80B9DF2CDC5A1DEDCDE449ECC5A1BADFD4`.
  Direct recomputation from the CSV gives 760 rows and 760 unique
  `(panel, opponent, seat, seed)` keys; parent and candidate are both
  `478/760`, with zero gains and zero regressions.
- Primary historical anchor is unchanged at `100/200`; adjacent population is
  unchanged at `378/560`; seats are unchanged at `243/380` and `235/380`.
  Every opponent total is unchanged, including the weak
  Kangaskhan/Crustle floor of `28/80`.
- Root numerical report:
  `61EF3B7B07B792E7638368871CCDC8324C6C4523DEF0B60AA63F685A41D78DC8`.
  Independent numerical audit:
  `837919D3A3EBC1BAE9558BED2EF81B7C7A6449C28B0A7CD0E9B3A21791679CE8`.
  Both report zero action errors, nonzero exits, missing starts, duplicate
  faults, and max-step hits.
- Only four fixed-760 traces differ, all outcome-neutral wins. The independent
  qualitative audit is
  `3C71161C542737732C4F4F2529DDB59BC2F931A9539DDAE8EBFA522BD3F35814`.
- In Mega Lucario, seat 1, seed `271958318`, both branches first received Mega
  Brave `983` for Full Metal Lab-reduced 240 damage. After Jumbo, our
  three-Metal Archaludon ex had 140 HP and five Prizes remained. The parent
  attacked Active with Metal Defender `253`; the candidate played Boss,
  selected 110-HP Lunatone, and used the same attack for one Prize.
  On the next opposing turn, the parent branch used Aura Jab `982` for
  reduced 100, leaving Archaludon at 40 HP. The candidate branch used Mega
  Brave `983` for 240, KO'd the two-Prize Archaludon, and discarded its three
  Metal. The candidate still eventually won, but the immediate Prize/resource
  exchange is causally worse.
- Source inspection confirms the exact parent already returns
  `"save Boss: Mega Brave stuck"` when
  `_opp_last_attack_id == MEGA_BRAVE`. H4's
  `_h4_persistent_effects_supported()` does not recognize Mega Brave's
  `"During your next turn, this Pokemon can't use Mega Brave"` restriction,
  so H4 can override that deliberate parent safeguard.
- In Mega Lucario, seat 0, seed `271958329`, H3 discarded Jumbo plus Boss,
  preserved Metal, completed the Duraludon/Turbo Flare setup, and both branches
  won. The parent later used Jumbo for an observed +80 heal. That proves an
  opportunity cost, but not a certificate breach or a causal lost game.

## Why the exact candidate fails

The candidate passes setup legality, board formation, attacker/backup
readiness, deterministic execution, both-seat aggregate safety, adjacent
population totals, and action/max-step checks. It does not pass the complete
rule-policy judgment:

- Practical strength and primary-anchor movement are absent: `478/760` and
  `100/200` are exactly unchanged, with no paired gain.
- H4 changes three winning trajectories. Two spend Boss and abandon Active
  chip for an earlier one-Prize KO; the third additionally releases a
  self-lock and immediately loses two Prizes plus three Metal. This is not
  repeated evidence of a beneficial Prize-exchange mechanism.
- The failing seat-1 Mega Lucario trace is an adjacent-population qualitative
  regression even though its terminal result remains a win.
- Immediate H4 transaction binding is correct, but its certificate is
  incomplete for attack continuity, disruption value, resource preservation,
  and the next-turn Prize exchange. Correct execution of an unsafe certificate
  is not sufficient.
- H3's setup/resource trade remains uncertain; it neither repairs nor excuses
  the demonstrated H4 defect.

Thus the exact hash is rejected for a live probe and cannot be accepted as a
formal parent.

## Frozen implementation contract

Create one isolated, fresh source child of the exact cumulative candidate
`BE8C...F18A`; do not call that candidate as a runtime parent. Retain the one
embedded exact historical-Silver chooser and exact deck. The behavioral diff
must be limited to this H4 eligibility repair:

1. Before `_h4_build_certificate()` creates or mutates any transaction, return
   ineligible when `_opp_last_attack_id == MEGA_BRAVE` (`983`).
2. In that state H4 must propose no action, own no transaction, spend no Boss,
   and leave every H4 namespaced field clear. The cumulative resolver then
   processes other rules normally; when none outranks/changes the exact case,
   the final action must be the exact parent's Metal Defender.
3. Do not add a generic text parser or broaden the veto to other attacks in
   this child. Unknown attack effects retain the existing fail-closed behavior.
   Any later self-lock taxonomy expansion requires separate evidence.
4. Do not change H2, search-aware, H1, H5, H6, Hero, H3, exact-parent scoring,
   precedence ranks, collision rules, transaction semantics, access
   probabilities, option binding, deck, or non-`main.py` runtime files.
5. Give the repaired H4/cumulative rule a new identity and contract/source
   ledger entry after implementation. It must not continue claiming the
   unmodified H4-v3 source hash for the edited component.
6. Preserve reset semantics: deck request, result, seat/turn rollback,
   duplicate callback, exception, and new-game boundaries must clear the
   tracked attack/H4 state exactly as before.

## Frozen focused and engine cases

All cases run in both logical seats, with at least two serial permutations and
two legal-option orderings.

### Required veto negatives

- Recreate the otherwise-H4-positive Mega Lucario/Lunatone state with tracked
  prior attack `983`, Boss legal, parent witness Metal Defender `253`, and a
  unique nonterminal one-Prize Bench KO. Require: H4 certificate `None`, no H4
  owner/state, no Boss action, and exact-parent semantic action.
- Replay the exact seat-1 seed `271958318` branch. Require parent/candidate
  semantic identity at the old first divergence and thereafter, no Boss or
  Lunatone gust, Mega Brave unavailable on the immediately following opposing
  turn, and the three-Metal Archaludon not KO'd on that turn.
- Repeat with duplicate callbacks, turn/reset boundaries, and a synthetic
  simultaneous lower-rule proposal. H4 must remain clear; the unchanged
  resolver must select the legitimate remaining owner or parent.

### Required no-lock positives

- In matched component fixtures replace prior attack `983` with `None` and
  Aura Jab `982`. When every original H4-v3 certificate predicate holds, H4
  must still complete Boss -> unique target -> exact inherited attack.
- Re-run every prior both-seat H4-v3 positive transaction, including the two
  fixed H4 changes at historical-Silver seat 0 seed `271828201` and Arch
  Shumpei seat 1 seed `271958328`. Their semantic transaction must be unchanged.
- Re-run H4's original no-Boss, no-unique-target, terminal-target,
  unsupported-effect, changed-board, wrong-attack, retry, rollback, exception,
  and reset negatives. No previously rejected H4-v1/v2 behavior may reappear.

### Integration safety

- Re-run the checked collision registry and all-eight clear/owner smoke. Ranks
  and winners are unchanged when the lock is absent. In a lock state H4 is
  absent, suppressed state stays clear, and there is never a second owner.
- Require zero invalid action, exception, emergency fallback, stale owner,
  owner switch, action error, nondeterminism, or max-step hit.

## Minimal reevaluation gate

The minimum evidence sufficient for a new practical judgment is:

1. exact source/deck/diff hashes plus compile/import/structure checks;
2. all focused and both-seat engine cases above;
3. the prior union shadow augmented with the four fixed changed traces,
   comparing exact parent, repaired cumulative policy, and isolated component
   proposals at every callback;
4. one fresh immutable full fixed-760 paired run. Reusing only the old neutral
   aggregate is insufficient because the source hash and one realized
   trajectory changed;
5. independent numerical recomputation and Root verification from raw rows;
6. both-seat extracted-package smoke and a fresh nonduplicate archive hash.

The repair's falsifiable fixed-760 prediction is strict: `478/760`,
`100/200`, `378/560`, seats `243/380` and `235/380`, zero gains, zero
regressions, every opponent/seat cell unchanged, Kangaskhan/Crustle at least
`28/80`, and zero action/max-step faults. Exactly three prior changed traces
should remain; Mega Lucario seat 1 seed `271958318` must become
parent-identical. Any other outcome or trace change blocks the probe until
causally explained.

## Exploratory-live eligibility after repair

Passing the preceding gates makes the fresh child eligible for at most one
Root-authorized practical exploratory probe under the cumulative integration
policy; it does not demonstrate strength or make the child a formal parent.
The Root must confirm quota/status, fresh source/archive identity, and package
integrity, and remains the only Kaggle writer.

Correct-seat shadow every genuinely new replay. Stop and roll back on any
H4 self-lock release, H4/collision-owned Prize or attacker regression,
certificate/attribution failure, stale/two-owner state, invalid action,
exception, or max-step hit. Audit the first H3 activation specifically for the
Jumbo heal forgone, whether retained Metal was attack-completing or surplus,
attacker survival, attached Energy lost, and ensuing Prize exchange. A causal
H3 loss selects a separate H3-only hypothesis; it does not retroactively
invalidate this isolated H4 repair.

Formal-parent acceptance still requires practical absolute strength and the
existing cumulative thresholds: at least `486/760`, at least `104/200` on the
primary anchor, adjacent at least `378/560`, no seat/cell/floor or parent-win
regression, repeated both-seat mechanism-valid gains, and zero action/max-step
faults. A tiny paired delta or one live win is not sufficient.

## Regression risks and exact evidence needed next

Principal risks are applying the veto after H4 has already armed; stale or
incorrect `_opp_last_attack_id` reset behavior; accidentally disabling no-lock
H4 positives; changing arbitration metadata or another component while
repairing H4; and treating the unresolved H3 heal trade as proven safe. The
veto may conservatively suppress an H4 opportunity if the tracked attack is
stale, but its fallback is the exact parent, which already uses the same Mega
Brave Boss-save guard.

The next judgment requires these exact raw authorities:

1. repaired child `main.py`, deck, direct-diff, new H4 contract, and component
   ledger hashes;
2. raw focused results and both-seat engine traces for every locked/no-lock,
   permutation, retry, reset, and collision case above;
3. augmented union-shadow callback rows with owner, proposal, final semantic
   action, and zero-fault counts;
4. fresh fixed-760 CSV, execution manifest, summaries/traces, exit codes,
   action errors, max-step fields, Root recomputation, and independent
   numerical audit;
5. a semantic/byte comparison proving the repaired seed `271958318` path is
   parent-identical and that the three intended remaining changed traces still
   match their H3/H4 mechanisms;
6. extracted-package inventory and archive hash; then, only if Root authorizes
   a probe, correct-seat live replay telemetry and exact-parent
   counterfactuals for every first difference.
