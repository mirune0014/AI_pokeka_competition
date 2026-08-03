# Integrated public turn-plan transaction v1

## Decision

Implement one coherent deterministic public-state hypothesis:

`INTEGRATED_PUBLIC_TURN_PLAN_TRANSACTION_V1`

The candidate preserves the final verified General Archaludon hierarchy and
adds three previously isolated, mechanically verified decisions to its single
proposal/ownership resolver:

> Choose the immediate Prize route that preserves the next attacker and the
> last deterministic Boss access without surrendering a certified terminal or
> defensive line.

This is a practical multi-rule live probe. Local win-rate improvement is not
an admission requirement. Legality, deterministic ownership, traceability,
and absence of a demonstrated destructive decision are mandatory.

## Frozen parent

- Directory:
  `autonomous_gold_20260715/candidates/archaludon_general_visible_counterattack_ready_rotation_v1`
- `main.py` SHA-256:
  `AC70708082882C7BA01CFBF81D29F534B95166DFF6BAD11E1EF1FA001A5F79D2`
- `deck.csv` SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Exact historical-Silver source SHA-256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`

The child is:

`archaludon_integrated_public_turn_plan_transaction_v1`

The existing child directory is an exact copy of the frozen parent. Do not
edit the parent or add another outer agent wrapper. The inherited General
resolver remains the sole arbitration layer and evaluates historical-Silver
exactly once per callback.

## New components

### Equal-two-Prize Active race attack first

- Rule ID:
  `PUBLIC_NORMAL_MODE_EQUAL_TWO_PRIZE_ACTIVE_RACE_ATTACK_FIRST_V1`
- Donor:
  `autonomous_gold_20260715/candidates/archaludon_cumulative_normal_mode_two_prize_active_race_v1/main.py`
- Donor SHA-256:
  `C15CA505A9B7D9BC5DEE58D74647FD9C702EDBA3CC040CB43A6308293D61CC82`
- Positive:
  `88826681:135`

When both players have exactly two Prizes left, both full-health Active
Pokemon are two-Prize Archaludon, current Metal Defender is payable and
survives the maximum supported public reply, and the inherited resolver would
uniquely Boss a one-Prize Bench target, propose Metal Defender into the current
Active instead. Preserve the donor certificate and fail closed on healing,
protection, retreat, attack, identity, or damage uncertainty.

### Post-attachment non-ex 120 visible KO

- Rule ID:
  `POST_ATTACHMENT_NONEX_120_VISIBLE_KO_SAFE_SUCCESSOR_ENVELOPE_V1`
- Donor:
  `autonomous_gold_20260715/candidates/archaludon_cumulative_post_attachment_nonex_120_visible_ko_v1/main.py`
- Donor SHA-256:
  `154B2607A57F839C56ECB97350CEA3842ED1C55B70215A43BFFB2ABD0093A0B3`
- Positive:
  `88825590:59`

After a confirmed same-turn Basic Metal attachment to the unique Cape-bearing
Active Duraludon, replace an inherited Raging Hammer non-KO with non-ex
Archaludon evolution and Coated Attack only when 120 damage is a deterministic
KO and every currently ready public Bench successor is nonlethal against the
actual evolved Pokemon. Preserve the donor retained-damage, Tool, Stadium,
Weakness, Resistance, Coated-protection, and unprotected-Basic calculations.
After evolution, any failed continuation clears ownership and recomputes a
genuine General action from the actual evolved state. Never return a stale
pre-evolution Raging Hammer.

### Persistent public last-Boss ledger and discard guard

- Rule ID:
  `PERSISTENT_PUBLIC_BOSS_ACCESS_LEDGER_WITH_PLAN_EQUIVALENT_LAST_COPY_DISCARD_GUARD_V1`
- Donor:
  `autonomous_gold_20260715/candidates/archaludon_persistent_public_boss_access_ledger_last_copy_guard_v1/main.py`
- Donor SHA-256:
  `AACAC0B2E47C495A971A6CFCA91A393DBAC4A567291F849DB7912E9F26E9D3A3`
- Positive:
  `88819392:120`

Track only observation-confirmed own Boss serials in complete hand, public
discard, public lost, current reveal, or unknown hidden state. At an exact
mandatory two-card Ultra Ball discard, when all four Boss copies are publicly
certified as three discarded plus the one in hand, replace the inherited
Boss-plus-Metal discard with the same Metal plus a plan-equivalent non-ex
Archaludon. Preserve the donor line, Bench-capacity, supporter, attack-prefix,
target-value, conservation, retry, and reset certificates. Unfair Stamp,
unsupported hidden movement, or conservation failure clears and delegates.

Ledger observation updates occur once per novel public snapshot outside
proposal simulation. Proposal simulation must not advance or duplicate it.

## Fixed component order

1. H2 last Prize;
2. Search-aware Active terminal;
3. H1 terminal-threat removal;
4. new equal-two-Prize Active race;
5. new post-attachment non-ex 120 KO;
6. H5 v2;
7. H4 Mega Brave self-lock veto;
8. General visible counterattack-ready rotation;
9. immunity-aware non-ex evolution;
10. Cape-before-anchor;
11. Turbo-before-retreat continuity;
12. sacrificial-Active Bench evolution;
13. H6 Metal reservation;
14. Hero's Cape survival;
15. H3 line formation;
16. public target dominance;
17. new last-Boss discard guard;
18. exact historical-Silver ordinary action.

Mandatory/setup/result/reset/legality, inherited exact immediate terminal, and
an already active transaction owner remain above every component.

All proposals use one immutable public snapshot and the cached inherited
resolution. Only one component owns a callback. Same-action proposals still
have one owner. Suppressed proposals leave no component state. Unknown rank,
ambiguous binding, double ownership, or unclassified post-irreversible
collision fails closed to a valid recomputed General action.

## Telemetry and ablation

Every callback exposes at least:

- `snapshot_id`, `plan_id`, `rule_id`, `rank`;
- `eligible`, `rejection_reason`, `certificate_digest`;
- parent, proposed, and final semantic actions;
- owner before/after and `suppressed_by`;
- transaction stage, reset reason, duplicate/retry state;
- caught exception and emergency flag.

The public plan payload records current attacker, attack, target, Prize route,
next attacker, reserved Metal/Boss, maximum supported public reply, and
terminal/nonterminal status when the active certificate proves them.

Add:

`_cum_diagnostic_disabled_rules = frozenset()`

It is empty in the submitted build. Local replay ablation may replace the
constant before import in an isolated copy. Observations and environment
variables never alter it.

## Required fixtures

Positive fixtures in both seats with serial remap, option reversal, and
duplicate retry:

- `88826681:135`: Boss becomes Metal Defender;
- `88825590:59`: non-ex evolution through Coated Attack 120 KO;
- `88819392:120`: preserve the last Boss with plan-equivalent discard;
- `89006709:137`: inherited General rotation remains intact.

Negative/retention fixtures:

- `88929453:87`, `88935472:106`: inherited Memory Dive Raging Hammer makes
  the replacement attacker unsafe;
- `89001625:117`: Mega Brave is locked and current Active is not threatened;
- all callbacks of `88775564`: Boss ledger delegates;
- `271828218:147`: immediate last Prize is not sacrificed to preserve Boss;
- `87996118`: H5 v2 owns;
- `88602602`: inherited Boss route remains;
- `88247531:115`: do not evolve when current attack value collapses;
- H5 v1 regression `271828271`;
- known H3 v1, H4 v1/v2, and H6 v1 destructive controls.

## Practical live-admission gate

The candidate may be packaged despite a weak local win rate only if:

- compile/import, legal 60 cards, exactly one ACE SPEC;
- exactly the inherited 12 runtime files, zero caches;
- `agent` is loader-only and loader-last;
- all three new positives complete in both seats;
- all listed negatives delegate to the frozen General parent;
- inherited General focused tests remain passing;
- pairwise/all-eligible resolver checks cover the new three against all
  inherited components, with H2 winning the all-eligible case;
- the current 89-replay union shadow completes in correct seats and every
  first difference is inspected;
- invalid actions, exceptions, stale owner, unknown collision, telemetry
  fault, and max-step hit are all zero;
- the extracted clean package completes one smoke game in both seats.

An obvious bad decision, untraceable parent-external difference, duplicate
owner, or stale pre-evolution action blocks packaging. A merely low local win
rate does not.

For each live first difference compare the frozen General parent, the complete
bundle, and bundle-minus-fired-rule. A rule owns a first difference only when
removing it restores the exact parent action.

