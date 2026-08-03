# Root-frozen normal-mode two-Prize Active race contract

Frozen: 2026-07-30 JST.

## Decision

Implement exactly one new cumulative rule:

`PUBLIC_NORMAL_MODE_EQUAL_TWO_PRIZE_ACTIVE_RACE_ATTACK_FIRST_V1`

The direct parent is the frozen nine-rule cumulative candidate:

- path:
  `candidates/archaludon_cumulative_public_hierarchy_megabrave_veto_boss_ledger_v1`;
- source SHA-256:
  `7092ED0409F348E38E4E568E06452258A4DF8290BBA871D614C7D67D3D031A57`;
- deck SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.

The exact historical-Silver rollback remains
`F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`.

## Root-verified source

- episode `88826681`, row `135`, logical seat `0`;
- replay SHA-256:
  `ED58D8FB1B7E8D7E0C4603AB5DC86DAC569185D66C192FD5CB39E98765A46282`;
- evidence memo SHA-256:
  `1AF4FB96CB25BE4E760773DD7CC026412CC305CB471E13B13E3C710827B5F6D9`;
- state verifier output SHA-256:
  `A9A55D9C1BFA855B3743258251AA7F9A06CFEF8CBF69018C8AD4B32B30454A56`.

Both players had exactly two Prizes. Both Active Pokemon were full-HP,
three-Metal, two-Prize Archaludon ex under Full Metal Lab. Exact Silver chose
Boss and took one Prize from a Bench Pokemon. The public alternative was
Metal Defender into the opposing two-Prize Active: exact current damage was
`190`, exactly two attacks were required, and our full-HP Active publicly
survived one currently payable return Metal Defender at `110` HP.

## Narrow public predicate

At an ordinary own `MAIN` decision, emit the unique current Metal Defender
attack instead of the direct-parent Boss action only when all of the following
are proved from the current public observation:

1. both players have exactly two Prizes;
2. both Active Pokemon are two-Prize Archaludon ex;
3. both Active Pokemon are at full printed HP and have complete public card,
   Tool, Energy, status, and continuous-effect information;
4. our unique current Metal Defender is payable and its exact public damage
   starts a two-hit KO of the unchanged opposing Active;
5. every currently payable opposing attack, after exact public modifiers,
   leaves our Active alive for the second attack;
6. the direct parent uniquely chooses Boss's Orders;
7. every legal Boss target yields exactly one Prize and none is a unique
   visible ready terminal threat, evolution bridge whose removal immediately
   prevents a lethal attack, damage amplifier, lock, or other already
   certified H1/H2/search-aware terminal object;
8. the unique Metal Defender option attacks the unchanged Active and no
   immunity, prevention, protection, unsupported effect, or ambiguous damage
   calculation exists;
9. no higher-ranked cumulative transaction is active or eligible.

No opponent identity, episode/row/seed, hidden hand, hidden deck order, Prize
identity, future draw, or replay continuation may be read or encoded.

## Action and precedence

The rule makes one immediate action: select the unique current Metal Defender.
It stores no cross-callback owner because the attack ends the Main action.

Insert it at rank 6:

1. exact direct-parent terminal action;
2. existing active owner;
3. H2 last-Prize transaction;
4. search-aware terminal transaction;
5. H1 unique ready terminal-threat removal;
6. this normal-mode two-Prize race rule;
7. H5 v2;
8. repaired H4;
9. H6 v2;
10. Hero same-attack survival;
11. H3 v2 line formation;
12. passive Boss last-copy ledger;
13. exact historical-Silver fallback.

Record a proposal, winner, semantic action, public certificate digest, and
suppression reason in the existing cumulative telemetry. Any uncertainty
returns the exact direct-parent action without state mutation.

## Mandatory parent-identical negatives

- either Prize count is not exactly two;
- a terminal action or an active higher-ranked transaction exists;
- Boss takes two or more Prizes;
- Boss removes an already certified unique ready terminal threat;
- either Active is not the supported two-Prize Archaludon ex;
- either Active is damaged, statused, protected, Tool-ambiguous, or otherwise
  incomplete;
- current attack is not an exact two-hit KO;
- any currently payable return attack KOs our Active;
- Energy payment, attack identity, damage, Weakness, Resistance, Stadium,
  Tool, or continuous effect is unknown or unsupported;
- Boss or Metal Defender is absent, duplicated semantically, or parent does
  not uniquely choose Boss;
- any existing positive or rejected-control fixture from the nine-rule
  parent, including episode `88247531:115`.

## Short destructive-safety gate

Do not run fixed-760 or a full replay-union evaluation for this candidate.
Require only:

1. compile/import, legal 60 cards, ACE SPEC one, loader-last `agent`, no cache;
2. the source callback changes Boss to Metal Defender in both logical seats,
   with serial remapping and option-order reversal;
3. at least 16 mandatory-negative mutations delegate exactly to the direct
   parent;
4. identical retry is deterministic and does not create an owner;
5. a short exact-engine branch in both seats reaches the attack result with
   the certified `190` damage and zero invalid actions, exceptions, stale
   state, or max-step hits;
6. fresh extracted-package smoke in both candidate seats.

If these pass, the candidate is safe for a diagnostic live probe after the
earlier eight-rule and nine-rule probes respect the user-requested observation
interval. Weak local or live win rate alone is not a defect. Repair only a
rule-owned changed action or a destructive runtime fault.
