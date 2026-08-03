# Deferred loss memo — episode 88777721

Status: `DEFER_ONLY__DO_NOT_STACK_INTO_H6`

Replay:
`autonomous_gold_20260715/live/55077607/refresh_20260729_184109/episode_88777721_replay.json`

Replay SHA-256:
`4D35BE58F562051164BC6AA9AE3CFD69F4A56D213F0BBF8874DE2DF6B30CDB5E`

The target was seat 1 and lost. Root shadowed all 65 actionable callbacks:
H6 v2 was exactly parent-identical with zero invalid actions, exceptions, or
stale transactions. This episode is not H6 causal evidence and does not
authorize an H6 repair.

## Root-verified turn-6 conversion failure

At row 33:

- Active was Hero's-Cape Archaludon ex `190#70`, 400/400, with exactly two
  Metal `8#114,#116`;
- opponent Active Shaymin `343#16` had 80 HP;
- hand contained Basic Metal `8#121`;
- manual attachment was unused;
- attaching that Metal to the Active made Metal Defender legal and
  deterministically KOd Shaymin;
- parent scores were tied at `20,000` for Poke Pad, either Ultra Ball, and the
  attack-completing attachment;
- list-order arbitration chose Poke Pad.

After Poke Pad, row 35 again offered the same attachment at `20,000`, tied
with either Ultra Ball. Parent chose Ultra Ball.

At row 36, the Ultra Ball discard callback scored Metal `8#121` at `20,000`
(`UB: 1st Metal`) and Cinderace `666#73` at `14,000`; both were discarded.
Ultra Ball found Archaludon ex `190#68`.

At row 39:

- the discarded Metal `8#121` was the only public Metal in discard;
- Active still had exactly two Metal;
- Bench Duraludon `169#66` was eligible to evolve;
- Archaludon ex `190#68` was in hand;
- evolving that Bench was legal but scored `-1,000`
  (`hold: evolve Active first`);
- End scored `0` and was selected.

The public card text supports a one-Metal Assemble Alloy fallback that could
attach the discarded Metal to the Active and complete Metal Defender, but the
changed continuation is not present in the replay. It must be reconstructed
in the exact engine before being treated as executable fact.

The target consequently made no attack on turns 2, 4, or 6. Attacks began on
turn 8. The later game became a two-Prize Archaludon-ex exchange against
successive one-Prize Alakazam attackers and ended in a target loss.

## Deferred hypothesis A — immediate KO attachment tie-break

When a manual Basic Metal attachment:

- immediately makes the current Active's exact printed attack legal;
- deterministically KOs the unchanged opposing Active;
- does not displace an exact terminal or higher-Prize route;
- is tied with nonterminal search/setup actions under the parent score;

apply a local modifier only to that attachment so it wins the tie, then lock
the exact attack after confirmation.

Mandatory negatives include non-KO attacks, protected/uncertain targets,
attachment needed for an exact stronger backup, retreat/forced-defense
precedence, or any search action that is itself a certified current-turn
terminal transaction.

## Deferred hypothesis B — one-Metal Alloy attack bridge

When the direct attachment opportunity has already disappeared but:

- exactly one public Metal is in discard;
- a legal Archaludon-ex evolution can trigger Assemble Alloy;
- attaching that one Metal to the current two-Metal Active completes an exact
  deterministic KO;
- the evolution target and attachment remain legal and public;

allow a narrow evolve -> accept Ability -> select exact Metal -> attach to
the stored Active -> exact attack transaction.

Mandatory negatives include zero/two-plus relevant Metals, inability to bind
the target uniquely, the attack remaining illegal or non-KO, a stronger
terminal/Prize/setup route, two-Prize liability that creates a public
immediate loss, or any need for hidden cards/opponent action.

These are two distinct future siblings. They must be tested separately and
must not be combined with H6's discard-reservation rule.
