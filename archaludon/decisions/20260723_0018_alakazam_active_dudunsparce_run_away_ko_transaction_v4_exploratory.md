# Decision: submit Active Dudunsparce Run Away KO transaction v4

## Decision

Package and submit exactly one exploratory live probe of
`alakazam_active_dudunsparce_run_away_ko_transaction_v4`.

This is not a formal strength adoption. The user explicitly authorized a
breakage-only release standard: weak local or live win rate is nonblocking,
while a known invalid action or structural continuation failure blocks.

## Hypothesis and target

When the exact formal parent would end the turn with a damaged Active
Dudunsparce, a unique one-Prize ready Kadabra or Alakazam can immediately KO
the unchanged one-Prize opponent Active, and all public effects are inside the
affirmative no-effect envelope, use Run Away Draw, verify the exact three-card
draw and returned stack, promote the frozen attacker, force the certified KO,
and return Prize selection to the parent.

The target is general tempo and Prize conversion from an exposed Dudunsparce,
not an opponent-archetype label. The transaction must remain history-free and
public-state deterministic.

## Frozen source and package

- Formal parent policy: `6AEF53400B9413037FB79DDCB9BE752A632FF4E0803B1D00EE84F188C44EDB6C`.
- Candidate planner: `B89DCB6363CBD6ADF094115CF0CF5B93D6B9975A2505E1B976F387AAE8A198CD`.
- Candidate transaction: `B70D7374E0D3C4613EBEC3CE0B8EBA931C641CB9423B8140817BCFCB7F996535`.
- Deck: `A7B6C7972915D09F6314C42633AA89D82B55DDF0A7199F7138E681FA52516529`.
- Verification results: `D4A5EF9E861891D160B6EAB617258B4DE04425005DD8EDD42983FF1ED651B99E`.
- Implementation receipt: `7221D027552726B9BCD21601DAF3F787E2BF0951BC2F6A4D5488740030513449`.
- Clean archive: `D1A7DF3B39F6E4CDA9FBB312863867CCD15E73F8040C40F0D1384BC2F1FF7194`, 2,080,300 bytes.
- Package manifest: `24C1E8995FA0C7A64A8FEBFBEA9E422D8ACBFD5A8454A6D5F559881521978C57`.
- Module-set hash: `8F4A643A59C005219063E4FD0CEA5564B99C6BCBD965DC1E899CFE9AE73CD540`.

The formal-parent recursive comparison has exactly two differences: the new
`planner_active_dudunsparce_ko.py`, and the minimal import/start/continuation
dispatch in `planner_final_policy.py`. All other shared files are byte-identical.

## Breakage evidence

- Focused matrix: PASS, 6 positive branches and 82 negatives across both
  semantic seats, including Survival Brace, Lucky Helmet, Spiritomb, Flygon,
  Slowking, public-discard Walrein, Iron Defender/Metal, unknown effects,
  duplicate callbacks, stale transitions, and fail-closed parent delegation.
- Full-engine transaction: PASS in both seats for `87416244` and `87428139`;
  `87411430` and `87411965` have the same full continuation covered in the
  focused engine harness. Every observed start reaches Run Away, promotion,
  exact KO, parent-owned Prize selection, and a clear latch.
- Current-42 shadow: 42 public episodes, 2,723 unique callbacks per source,
  exact schedule equality, four causal starts only, zero invalid actions,
  duplicate mismatches, parent-call mismatches, emergencies, fallbacks, or
  unclassified differences. Candidate raw SHA
  `FB68241F2FFDB3ED39AF4910A355241D855612E146780DF6A398DADCDF87AD97`,
  parent raw SHA
  `E9A016A7F1E92204713444D76FCFEEE8322943BBFE267CA60FF3728148AA3269`,
  comparison SHA
  `903F194246DF7A24BCFE4C5AC4F8BF74761E19A1F5C48DBA2FF89C2FA445B66C`.
- The four later static-replay aborts are counterfactual parent-path artifacts;
  all four changed starts have separate exact continuation coverage.
- Historical anti-overfit population: 186 episodes / 11,866 callbacks, exact
  schedule, zero differences and zero faults.
- Candidate smoke and clean-package smoke: both seats complete with zero
  action errors and zero max-step hits. The extracted package is byte-identical,
  contains 42 safe members, 60 legal cards, one ACE SPEC, and a sole/last
  callable `agent`.

An independent source auditor returned PASS after checking copied and
persistent attacks, hidden next-turn fields, exact KO accounting, latch and
duplicate mechanics, and the formal-parent diff. The required Sol-Ultra final
judge returned `ACCEPT_FOR_EXPLORATORY_SUBMISSION`. Absolute strength remains
unknown; live start-to-Prize continuity is the next required evidence.

## Immediate prewrite state

- Current live submission: Kaggle `54895497`, COMPLETE at `632.2`.
- Episode table: 43 rows = 42 public plus one validation; public 22-20.
- Final episode CSV SHA:
  `B51CB730022EA9937D0EB5C145D7A957B0375FAA748B3F69CE2E444CB61E2076`.
- The final refresh found no episode addition or removal from the shadowed
  current-42 set.
- UTC 2026-07-22 submission quota: 2/5 used, 3/5 remaining.
- The candidate archive filename and source have never been submitted.

The current live recovered from its earlier checkpoint, but it is mature at
42 public games and remains clearly weak. V4 is separately valid and fixes a
specific observed end-turn conversion, so replacement is permitted.

## Live retention rule

Inspect every new replay. Any genuine v4 start that fails to complete through
promotion, exact KO, and parent-owned Prize selection, or any invalid action,
blocks retention. Score movement without a v4 policy difference is not causal
evidence.
