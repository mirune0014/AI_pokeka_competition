# Repaired cumulative Archaludon final practical-live judgment

Date: 2026-07-30 JST  
Scope: read-only post-implementation rule-policy judgment

## Verdict

`ACCEPT_FOR_ONE_EXPLORATORY_LIVE_PROBE`

This verdict applies only to repaired candidate `main.py`
`DEE5092B6785DF7A63752C7AAE497051D08DCC62F7723CD9786225A0C5A99DE8`
with deck
`08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.
It authorizes at most one Root-controlled live diagnostic. It is neither a
strength claim nor formal-parent acceptance; exact historical-Silver
`F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
remains the formal rollback.

## Verified facts used

- Frozen Root specification
  `B26A08A6F414988DE4EFEA5D8788C2F0A27221074BA6A0B6F54B4BD33A7076C3`,
  repair judgment
  `A263871FFB639DB2BB0A535642CFE534434E838ADC1665BE31637FEA66DC112B`,
  worker report
  `776363B2842D5B4DA98D02FAC6F387D12D4C99282D02848D7DB60599A1919E88`,
  and Root implementation verification
  `449B8378BE7B47288872512CD2448FCA99098A8FB9743B615E2B45FC791EB796`
  agree on the frozen identities and isolated H4 repair.
- Root directly reran 261 replays and 14,464 callbacks, including 115,712
  isolated-component comparisons: 27 parent-action differences in 23 files,
  zero isolated eligibility/action/certificate mismatches, all eight rules
  naturally attributed, 33/33 transaction starts/clears, and a passing
  collision registry. Invalid actions, exceptions, emergency fallbacks,
  unknown collisions, stale/two-owner states, owner switches, retry-parent
  calls, and max-step hits were all zero.
- The fresh raw fixed-760 CSV is
  `autonomous_gold_20260715/implementation/archaludon_cumulative_public_hierarchy_megabrave_lock_veto_v2/fixed760_raw/paired_results_with_panel.csv`,
  SHA-256
  `A44950A597DED7FF34A94D8BB77AA34024732FCE15EC4230AC469FE45B450356`.
  Its manifest is
  `fixed760_raw/fixed760_execution_manifest.json`, SHA-256
  `41DA0C390920A4A6770C225DE487519949715DCBCCAA13D5B6D291F16AA31C1E`.
  This judge directly confirmed 760 rows, 760 unique
  `(panel, opponent, seat, seed)` keys, zero duplicate groups, `478/760`
  wins for each policy, `0/0` paired gains/regressions, and exactly three
  result-or-step changes.
- Root recomputation
  `10A9570AB109869B68016D4F6BB0F150F35F316812F4C49F2C3E7959CC3F2C87`
  and independent audit
  `D1DDE86F044335B6992DDBA3505F3D3F72492952F6690475DE05D1646074BC37`
  agree: historical anchor `100/200`, adjacent population `378/560`, seat 0
  `243/380`, seat 1 `235/380`, every opponent/seat cell equal, duplicate
  controls `760/760`, and zero execution, action-error, or max-step faults.
  The inherited Kangaskhan/Crustle weakness remains `28/80`.
- Exactly three intended outcome-neutral changed traces remain. The repaired
  Mega Lucario seat-1 seed `271958318` baseline and child traces are both
  SHA-256
  `A18A6849CDE6770755AB1F0ECCB8A7C079B024A4188CC5C8B613DAA25843FE16`,
  result `1`, 85 decisions. At the old divergence the child retains Metal
  Defender; the next opposing attack is Aura Jab `982`, and the three-Metal
  Archaludon survives at 40 HP. The demonstrated Mega Brave self-lock release
  is therefore repaired completely on the frozen target.
- H3's Jumbo-versus-Metal discard trade remains unresolved. Existing evidence
  shows a forgone later Jumbo heal in one outcome-neutral win, but no
  Root-verified causal loss, rule/collision fault, or fixed-panel regression.

## Rule-policy reasoning

The repaired public-mechanic veto is implemented before H4 transaction
construction, so it preserves the exact parent's attack continuity and
attacker, Energy, and Prize position in the demonstrated lock state. No-lock
H4 behavior, all other hierarchy rules, precedence, reset semantics, board
formation, backup construction, and the exact deck remain unchanged. The
union evidence gives strong destructive-safety coverage for setup, action
legality, transaction ownership, and collision behavior.

The fixed panel gives both-seat and adjacent-population safety but no strength
movement. Setup and board formation remain executable; H3 can still form the
Duraludon/Turbo Flare backup line and preserve Metal, while its possible cost
is the discarded Jumbo heal. H4's two remaining Boss conversions and H3's
remaining conversion all finish as wins, but they do not establish superior
attack timing, hand/Energy use, disruption, Prize exchange, or finishing.
Absolute local strength is merely inherited: `62.8947%` overall, `50%` on the
primary anchor, and a severe `35%` Kangaskhan/Crustle floor.

Accordingly, this candidate fails formal-promotion strength gates and has no
repeated beneficial paired mechanism. That does not block this narrower
decision: the user explicitly permits a cumulative multi-rule live experiment
when no destructive defect remains and accepts neutral local movement for live
diagnosis. H3 is therefore a required monitored diagnostic, not a pre-probe
blocker. A fixed panel in which only three trajectories change cannot
discriminate rare live activation quality; one controlled probe has practical
information value.

## Frozen package and live contract

1. Freeze the source and deck hashes above. Any source, deck, ledger, rank,
   runtime, or rule change voids this verdict.
2. Root alone may build a fresh authoritative archive from this repaired
   candidate. It must contain exactly the 12 expected runtime files, no cache,
   tests, or evidence, and pass compile/import/deck-request plus extracted
   both-seat smoke. Root must record the archive SHA-256 and inventory before
   any write.
3. Immediately before the write, Root must refresh authenticated submission
   status, UTC-day quota, current score/status, and the exact prior episode-ID
   set. The description must identify the cumulative eight-rule hierarchy and
   Mega Brave self-lock veto.
4. This judgment permits one submission only. It does not permit adopting this
   candidate as the new formal parent, spending a second slot on its behalf,
   or claiming strength from a single score, win, or neutral replay.

## Live monitoring and rollback conditions

Correct-seat shadow every genuinely new replay against exact
historical-Silver and record the first semantic difference, public state,
winning rule, transaction owner/stage, collision set, attack continuity,
attacker/backup readiness, hand/deck/Energy transaction, Prize movement, and
finish.

Stop the probe and return to exact historical-Silver for subsequent use on any
of the following:

- package/hash/inventory mismatch or execution failure;
- invalid action, exception, emergency fallback, max-step hit, stale owner,
  two owners, owner switch, retry-parent call, or unattributed/certificate-
  external action;
- any H4 action that releases Mega Brave or another tracked public self-lock;
- any H4- or collision-owned line that causally worsens immediate attacker
  survival, attached Energy loss, attack continuity, or Prize exchange;
- a causally verified H3 loss or attacker collapse produced by discarding
  Jumbo when its heal had survival value and the retained Metal was surplus.

A weak aggregate score alone is diagnostic rather than a causal rule failure,
but it cannot justify continuation or promotion under this one-probe verdict.

## Regression risks and exact evidence needed next

Remaining risks are stale prior-attack tracking, an overbroad H4 veto in an
unseen no-lock state, rare multi-rule precedence not exercised in the union,
H4 Boss expenditure that abandons valuable Active chip, the unresolved H3
Jumbo/Metal survival trade, and the inherited Kangaskhan/Crustle floor.

The next authoritative evidence is:

1. the clean archive hash, exact 12-file inventory, and extracted-package
   both-seat smoke;
2. the timestamped pre-write submission/quota/status snapshot and exact prior
   episode-ID set;
3. the post-write set difference, raw replay paths/IDs, score/game sequence,
   correct-seat identity, exits, action errors, and max-step fields;
4. callback-level candidate versus exact-parent shadows for every first
   difference, including public attack history, rule/certificate attribution,
   collision ownership, semantic action, attacker HP/Energy, hand/deck
   transaction, Prizes, and subsequent attack/KO;
5. for the first H3 activation, the discarded Jumbo's reachable heal,
   whether retained Metal was attack-completing or surplus, backup readiness,
   attacker survival, attached Energy lost, and ensuing Prize exchange.

If the live probe contains no relevant H3/H4 activation, it is inconclusive.
The next discriminating local experiment is a both-seat H3 fixture matrix that
crosses attack-completing versus surplus retained Metal with survival-relevant
versus irrelevant Jumbo healing. Formal-parent reconsideration still requires
at least `486/760`, at least `104/200` on the primary anchor, adjacent at
least `378/560`, no seat/cell/floor or parent-win regression, repeated
mechanism-valid gains in both seats, and zero action/max-step faults.
