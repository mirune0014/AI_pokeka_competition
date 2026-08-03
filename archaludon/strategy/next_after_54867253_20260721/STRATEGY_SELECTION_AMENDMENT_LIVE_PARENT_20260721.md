# Controlling amendment — retain the causal retreat bridge

- Frozen by root: 2026-07-21 22:16 JST
- Applies to: `STRATEGY_SELECTION.md`
- Original contract SHA-256: `D749154CD648EBE4C3860E649FE9081A0D2C23B22A4797F9D5A72856822DAE42`

This amendment supersedes only the original contract's selected-parent and
retreat-overlay statements. All Starmie-Shaymin predicates, positives,
negatives, ordering, and fail-closed boundaries in the original contract
remain controlling.

## Parent amendment

Implement the Starmie-Shaymin guard as exactly one isolated overlay directly
on current live source
`alakazam_finalized_super_psy_bolt_retreat_ready_alakazam_ko_bridge_v1`,
SHA-256
`7838FBFF3CBA3AE5D9142E45B1334B192A5E758CFFA5598AF2A626E5C7D636E3`.

The H0/H1 source SHA
`23B89E347565F1782F44494E8ACD89FAB0FEED20C484B2DA14DE1195B908CBE9`
remains a comparison anchor, not the implementation parent. Formal rollback
remains guarded Teleportation SHA
`4A95DCE0BB095A05F58085DFC450528C5939527E30B9D40E43A76B0CFCE2AE16`.
Using the live source here is exploratory parentage and does not formally adopt
it as the rollback baseline.

The candidate-versus-live diff may add only the frozen Starmie-Shaymin guard.
Preserve every live retreat-bridge latch, predicate, abort rule, payment,
promotion, attack, and continuation exactly. The deck, Energy policy, Prize
selection, disruption rules, and all unrelated decisions remain unchanged.

Inherited transactions and certified immediate wins, KOs, and their enabling
actions retain precedence. Shaymin search/deployment must not preempt a
currently certified Powerful Hand KO or finishing route, reduce its hand-count
damage below lethal, or suppress attacks, retreat, attachments, evolutions,
or attacker/backup continuity.

## Mandatory causal-retention gate

Episode `87213204`, seat 1, must be candidate-versus-live identical on every
callback:

1. At step 33 the candidate chooses RETREAT, not Super Psy Bolt.
2. It completes the exact retreat payment and promotes the ready paid Alakazam.
3. It selects Powerful Hand `1072`.
4. It KOs the lone 50-HP Dunsparce and retains the board-out win.
5. The live-versus-H0/H1 first difference remains exactly step 33.
6. The equivalent exact-engine route passes in both semantic seats.

The evidence for this amendment is the root current52 shadow
`live/54867253/refresh_20260721_2205/root_current52_live_shadow.json`, SHA
`40CD308D9A267C4F0B312CA21AF3D8F78E8C8012DD80004982CFABCB9267132B`,
and root checkpoint `ROOT_LIVE_CHECKPOINT.md`, SHA
`3DFB76F347B70387B573AA696627E08687F5F4515D97694A4B3057A95C107810`.

## Amended practical-probe gate

Before any package or Kaggle write, require:

- both named Starmie positives and every original negative/fail-closed case;
- callback-complete current52 plus historical shadows against live, H0/H1,
  and formal rollback, with every change classified, all nonactivating
  callbacks live-identical, and zero invalid/duplicate mismatches;
- the complete episode-87213204 retention gate above;
- fixed both-seat smoke against historical-Silver, Starmie, Alakazam mirror,
  and Mega Lucario, with zero action errors/max-step hits, no historical-Silver
  seat regression, and Starmie not net worse;
- compile/import, legal 60 cards with one ACE SPEC, loader-last callable,
  source/runtime parity, cache-free archive, and package-local smoke;
- a fresh authenticated Kaggle refresh with available quota and no new replay
  contradiction.

If every gate passes, one exploratory live probe is permitted. It remains a
probe, not formal adoption. Root alone packages and writes to Kaggle.
