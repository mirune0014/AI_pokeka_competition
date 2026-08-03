# Final strategy judgment: certified unique-Active-Mist Hammer KO transaction v1

## Decisions

### A. Baseline decision

`REJECT_FORMAL_ADOPTION`

Retain the guarded Teleportation implementation parent as the causal baseline.
The candidate is safe enough to test, but it has not demonstrated any local
strength gain, mechanism frequency, or primary-anchor movement that would
justify making it the new baseline.

### B. Live-probe decision

`PERMIT_ONE_EXPLORATORY_LIVE_PROBE`

This permission is conditional on the root's immediate pre-write refresh and
hash/package checks below. It authorizes at most one Kaggle submission of the
exact frozen candidate archive. It is not adoption, does not authorize a second
submission of the same source, and does not relax any safety or packaging gate.

## Material identity

- Candidate source SHA-256:
  `97B0742C8DF9FBE770FCD814EFDAB1A3C18DE6451E49E1FC36E69EA554FF216B`.
- Guarded implementation parent source SHA-256:
  `4A95DCE0BB095A05F58085DFC450528C5939527E30B9D40E43A76B0CFCE2AE16`.
- Frozen strategy-selection SHA-256:
  `D53557D23837F17F77C7403332F1AF6F5867E863E3DDB40BD1C67F97D047BB27`.
- Fixed-144 numerical-audit SHA-256:
  `6D447C5098A8C6018C084849CDB70E1499ADDC5E0C4D08163264E70C99BCDE93`.
- Fixed-144 root-recompute SHA-256:
  `77A031C1D0B6FB64AEE90B2E1B4D5855449649C7FD27FB9E80AAA421DF382EE8`.
- Targeted-extension numerical-audit SHA-256:
  `C38A0446C9BBD48999A3E073B7D8F9C51530CA4BDC99AE8FA54BC3A87314EF88`.
- Targeted-extension audit JSON SHA-256:
  `C9C63FA9E576C7584802839BC96E54702A46A2AF9E915A39720DF4BE3E36557D`.
- Targeted-extension calculator SHA-256:
  `91446A001D11F8BD182710937B9AEFBDFE5C0DCCDD0CA068D1C2A68A7C8BB190`.
- Targeted-extension root-recompute SHA-256:
  `19238E29D8B2C4CD2E6B9E474B2A47E86D67D06313C5F5989F0287C4577A66F0`.
- Root final combined numerical-verification SHA-256:
  `C4D21420489138CE8E34631F94119D98233E5FCD432E8D150192E427DDD925BA`.
- Clean package archive SHA-256:
  `10670F667E1C7B702B76459657EDE9A47F229BDF929B341160A3EDC0449DFA49`.
- Package-manifest SHA-256:
  `12FD2C9950C2B2810641EB1647BC3F28F257BA8DE7DA5023DBEA6FE3FBF53126`.

The causal comparator is the guarded parent `4A95...`, not the currently live
CB52 descendant. The exact-v3 artifact remains the secondary anti-overfitting
comparator. A live score difference versus submission `54841997` would combine
the rollback from CB52 to the guarded parent, opponent sampling, seat sampling,
and the Hammer overlay; it therefore cannot by itself be attributed to the new
Hammer rule.

## Formal-adoption judgment

Formal adoption fails for four independent reasons.

1. **No paired strength movement.** On fixed-144, guarded parent and candidate
   were both `89/144`, with `0` paired gains and `0` paired regressions. On the
   targeted extension they were both `40/64`, again with `0G/0R`. Thus all 208
   frozen parent-candidate keys are outcome-identical.
2. **No local action or mechanism movement.** Fixed-144 produced zero changed
   byte traces. The 64-key targeted extension replayed exactly `4,457`
   callbacks and recorded zero starts, targets, attacks, resolutions, or
   aborts. The local panels therefore establish retention only; they do not
   establish benefit or even representative mechanism frequency.
3. **The primary-anchor floor remains unsound.** Historical-Silver in the
   targeted extension was `20/32` only because of a severe seat split:
   P0 `16/16`, P1 `4/16`. The candidate made no movement on that floor. Formal
   promotion would preserve an unresolved adjacent-matchup and seat risk.
4. **One public causal position is insufficient for baseline promotion.** In
   the full live-history shadow, the candidate changed only the intended
   decision in episode `86987527` over `15,460` callbacks. That is strong
   specificity evidence but only one opportunity; it does not estimate net
   strength or rule frequency.

The structural evidence is strong: focused tests passed `702/702`; the exact
checked engine completed the Hammer -> unique Active Mist -> Powerful Hand ->
KO transaction in both seats at 150 HP and 140 HP with zero faults; the deck is
legal at 60 cards with one ACE SPEC; the source is the last callable; and the
clean package passed extraction, loader, both-seat smoke, and cache-free checks.
Those facts remove a known-broken objection. They do not substitute for a
strength signal, so the correct formal decision remains rejection.

## Why exactly one exploratory probe is justified

The candidate is not filler. Episode `86987527` supplies one exact public
causal opportunity in which the guarded parent discarded the wrong Mist
Energy, while selecting the opponent Active's unique Mist would retain a
payable seven-card Powerful Hand and certify `140 >= 130` damage for the KO.
The full-history shadow changes only that intended position, and the repaired
public-history witness is restricted to the certified Crustle `345` / Superb
Scissors `479` tuple and fails closed otherwise.

The remaining uncertainty is principally distributional: neither frozen local
panel activates the mechanism, while public play has produced one real target
position. A single live probe is therefore the smallest experiment capable of
measuring actual opportunity frequency and observing the complete branch in
the environment that produced the motivating case. The guarded parent also has
the best practical Alakazam live result available (`778.9`), although that
whole-artifact score is not causal evidence for this overlay. Given the user's
explicit preference for safe submit-repair cycles, the exact packaged artifact
has enough specificity and safety to justify one exploratory slot.

## Principal risks

- **Extreme rarity:** zero starts in 208 frozen paired games and `4,457`
  targeted callbacks means the probe may produce no causal observation.
- **Persistent-history semantics:** despite the restrictive witness and engine
  gates, a novel public log shape could expose tracker leakage, stale identity,
  or an incorrectly certified prior attack.
- **Score confounding:** the currently live CB52 agent is not the implementation
  parent, so score changes mix artifact rollback with the overlay and ordinary
  evaluation variance.
- **Seat weakness:** Historical-Silver P1 is `4/16`; the overlay has shown no
  ability to repair it.
- **Tactical-versus-game outcome:** even a correctly completed KO transaction
  proves the tactical conversion only. It does not by itself prove a higher
  match win rate or baseline quality.

## Mandatory pre-submit conditions

Immediately before any Kaggle write, the root must refresh submission status,
score, UTC-day quota, and genuinely new public episode IDs/replays. Exercise
this permission only if all of the following remain true:

1. Candidate source is exactly `97B074...216B` and archive is exactly
   `10670F...A49`; the package manifest and all loader/legal/smoke gates remain
   valid.
2. At least one daily submission slot remains.
3. Submission `54841997` is complete and is not demonstrably recovering above
   the guarded practical parent in a way that makes replacement irrational.
4. No newly fetched replay invalidates the public-history witness, unique-Mist
   certificate, fail-closed behavior, or any other frozen safety premise.
5. The submission is recorded explicitly as a one-time exploratory probe from
   guarded parent `4A95...`, not as baseline adoption.

If any condition fails, the root must not exercise this permission. The root
retains sole authority for the external write.

## Post-submit observation protocol

Record the submission ID, timestamp, source/archive/package hashes, guarded
parent hash, exact hypothesis, and quota at write time. Refresh public episodes
incrementally at 5, 10, 20, and 40 genuinely public games, or at each available
new block if Kaggle exposes them less regularly.

For every public game, replay the exact submitted candidate and exact guarded
parent sequentially from the initial state in the candidate's actual seat.
Record:

- whether their action streams are byte-identical;
- tracker starts, certified targets, locked attacks, resolutions, and aborts;
- the exact first changed callback and the full changed branch;
- whether the witnessed preceding attack is exactly card `345`, attack `479`;
- whether Hammer removes the unchanged Active's sole Mist Energy;
- whether immediate Powerful Hand remains payable, is selected, and certifies
  and resolves the KO.

Action-identical games are zero causal evidence for the Hammer rule, regardless
of win, loss, or score. Their outcomes sample the guarded whole artifact only.
A completed certified transaction proves that the mechanism executes in live
play, but one transaction still does not authorize adoption or resubmission.

## Stop, reject, and interpretation rules

Stop the probe immediately and reject the rule on any of these events:

1. any invalid action, exception, loader failure, max-step hit, or tracker-state
   leakage;
2. any candidate-parent action difference outside the frozen Hammer-target and
   immediate Powerful-Hand transaction;
3. acceptance of missing, multiple, malformed, proxy, stale, or unsafe prior
   attack history;
4. a started transaction that, under an unchanged normal continuation, fails
   to remove the exact unique Active Mist, fails to choose the certified
   Powerful Hand KO, or aborts without a frozen fail-closed reason;
5. any source, archive, extraction, or package hash mismatch.

Frequency stop: if 40 genuinely public games complete with zero certified
starts and zero completed transactions, conclude that the rule is too rare for
this live probe. Stop monitoring this source, do not submit it again, and
retain the guarded parent. If the first completed transaction occurs earlier,
perform a qualitative causal audit immediately; the purpose of this one probe
has then been met, but no automatic adoption follows.

Score stop: a clearly weak mature result around `700` or below may justify
ending operational monitoring early after checking status and game sequence.
Do not blame the Hammer overlay unless a changed branch is causally involved.
Likewise, a high score with no action differences is not evidence for the
overlay. Never use a second slot for the exact same source/archive merely to
resample its score.

Formal adoption may be reconsidered only under a new frozen comparison after
repeated mechanism-linked observations. At minimum it must show practical
absolute strength, at least two net paired gains or equivalent repeated causal
movement, both-seat transaction safety, primary Historical-Silver movement
without a severe adjacent-matchup regression, and zero action faults. A score
alone, one correct transaction, or action-identical wins cannot satisfy that
gate.

## Final disposition

- Baseline remains the guarded implementation parent.
- Candidate is formally rejected as a baseline.
- Exactly one conditional exploratory live probe is permitted.
- The exact candidate must not be resubmitted, automatically adopted, or used
  as causal evidence unless the monitored action branch actually differs from
  the guarded parent in the frozen way.
