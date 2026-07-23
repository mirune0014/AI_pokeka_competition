# Strategy selection: Active Dudunsparce Run Away KO transaction v1

Decision: implement immediately in isolation from exact submitted v3.

Exact parent policy SHA-256: `6AEF53400B9413037FB79DDCB9BE752A632FF4E0803B1D00EE84F188C44EDB6C`.

## Hypothesis

When submitted v3 has completed ordinary development and would end with damaged Dudunsparce Active, replace only that END with an atomic `Run Away Draw -> uniquely ready one-prize Psychic attacker promotion -> certified KO of unchanged Active` transaction.

## Start certificate

Start only on ordinary MAIN when all conditions hold:

1. The exact parent is called once and returns the unique legal `END`.
2. No inherited or candidate transaction/owner is active.
3. Own Active is damaged Dudunsparce `66`; its exact Active Run Away Draw option is uniquely legal; no special condition; deck count at least three.
4. Dudunsparce has at most one fully known Energy and at most one fully known Tool. Zero attachments are allowed; unknown attachment semantics fail closed.
5. Exactly one benched attacker qualifies:
   - Kadabra `742` with Super Psy Bolt `1071`; or
   - Alakazam `743` with Powerful Hand `1072`.
6. The attacker is one-prize, has publicly sufficient attached Energy, may attack this turn, and its frozen exact damage KOs the current opposing Active.
7. Damage certification includes visible Weakness, Resistance, stadiums, abilities/effects, and remaining HP. Powerful Hand uses the guaranteed post-draw floor `current handCount + 3`.
8. Reject coin-dependent, hidden-choice, prevention, redirection, damage-counter, or incompletely modeled cases.
9. The opposing Active is publicly one-prize for v1.

## Transaction

1. Replace only the exact parent END with the frozen Active Run Away Draw action.
2. Latch player, turn, Dudunsparce/evolution/attachment serials, hand/deck counts, frozen attacker serial and Energy serials, opposing Active serial, and attack ID.
3. Duplicate callbacks return the same action without advancing state.
4. At forced promotion, verify exactly three draws, exact returned Dudunsparce stack/attachments, unchanged turn and target, then promote only the frozen attacker.
5. At the resulting MAIN callback, reverify attacker, Energy, target, legal attack, and KO certificate; select only the frozen attack.
6. Verify attack/KO resolution, clear the latch, and delegate Prize selection and every later callback to exact v3.
7. Any stale, ambiguous, mutated, or unexpected callback clears the latch and safely delegates. The child owns only Run Away Draw, forced promotion, and the frozen attack.
8. Parent post-state is preserved on delegation or abort. Parent pre-state may be restored only for the exact three child overrides.
9. Fezandipiti ex remains entirely parent-owned; add no Fez play, bench, promotion, or exposure ban.

## Precedence and exclusions

- Higher-precedence parent owners, existing transactions, prize-taking parent actions, parent non-END actions, and final-prize routes remain parent-owned.
- No start for healthy/non-Dudunsparce Active, low deck, ambiguous Run Away/promotion, unsupported or unpowered attacker, non-KO, attack prohibition, uncertain effects, multiple qualifiers, excessive/unknown attachments, multi-prize target, target mutation, or sole-board removal.
- Never inspect opponent ID, replay ID, exact turn number, hidden hand/deck identities, or future evolution assumptions.

## Breakage-only gates

- Exact checked-engine branch for `87411430`: Run Away -> promote Alakazam `#12` -> Powerful Hand -> KO Kadabra `#82`.
- Exact checked-engine branch for `87411965`: Run Away -> promote Kadabra `#10` -> Super Psy Bolt -> KO opposing Active.
- Both semantic seats; exact three-card draws; returned attachment serials; duplicate idempotence; parent-owned Prize selection.
- Public-five shadow starts only at the two certified causal states; zero starts in the three wins or unrelated callbacks; zero invalid, emergency, fallback, or latch leak.
- Strict negatives for every exclusion above.
- Reuse the older `alakazam_bossed_active_run_away_ko_bridge_v1` logic/tests only as read-only design precedent; do not runtime-import or modify it.
- Direct-parent diff limited to the isolated candidate; compile/import, legal 60 cards with one ACE SPEC, sole/last callable, cache-free tree, both-seat package smoke, deterministic duplicate behavior, and full current-plus-historical shadow must pass.

Weak or tied local win rate is non-blocking under the user's practical live-probe instruction. Structural failure, invalid actions, known broken continuation, or unclassified divergence blocks packaging and submission.
