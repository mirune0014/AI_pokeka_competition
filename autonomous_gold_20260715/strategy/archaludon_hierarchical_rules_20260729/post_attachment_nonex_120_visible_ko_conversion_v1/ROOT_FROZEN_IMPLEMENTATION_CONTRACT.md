# Root frozen implementation contract

Decision:
`SELECT_POST_ATTACHMENT_NONEX_120_VISIBLE_KO_CONVERSION_V1_FOR_SHORT_DESTRUCTIVE_GATE`.

Date: 2026-07-30 JST.

This contract authorizes one isolated cumulative child and only the short
destructive-safety gate below. It does not authorize fixed-760, a full replay
shadow, formal-parent promotion, or a Kaggle write ahead of the already frozen
eight-, nine-, and ten-rule probes.

## Frozen identities

- direct cumulative parent:
  `candidates/archaludon_cumulative_normal_mode_two_prize_active_race_v1`;
- direct-parent `main.py` SHA-256:
  `C15CA505A9B7D9BC5DEE58D74647FD9C702EDBA3CC040CB43A6308293D61CC82`;
- exact historical-Silver rollback anchor SHA-256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`;
- deck SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`;
- source replay:
  `live/55083165/refresh_20260730_0625/episode_88825590_replay.json`;
- source replay SHA-256:
  `E80A121C57B0CCA51C6ABBCD5070B6437145185AE41FC502C64709269280F4AC`;
- Root source verification:
  `root_verification/archaludon_cape_nonex_lethal_evolution_88825590_20260730/root_verification.json`;
- Root source-verification SHA-256:
  `381A69283FDAEF766E22B9CC638328E96F6EC7CDB912E99B2C3AC882AEB1DC4F`;
- controlling deferred memo SHA-256:
  `7160978B8199B41A3D1AA21F07ABC0C63AC43153445BDC1C73D1736C544389AC`.

## Rule and public rationale

Rule ID:
`POST_ATTACHMENT_NONEX_120_VISIBLE_KO_CONVERSION_V1`.

At source `88825590:59`:

- our unique Active is Duraludon `169#3`, `230/230` through Hero's Cape,
  with exactly three Basic Metal Energy;
- the current turn's Energy attachment has already been used on that same
  Active;
- opposing Active Alakazam `743#86` has `110` HP;
- exact parent chooses Raging Hammer `224` for `80`, a non-KO;
- non-ex Archaludon `840#32` is a unique legal evolution on that Active;
- after evolution, the three Metal pay Coated Attack `1212` for deterministic
  `120`, an immediate KO;
- evolution retains Hero's Cape and Energy, projects maximum HP
  `230 -> 280`, and remains a one-Prize Pokemon.

The existing H5 v2 coverage stops only because `energyAttached == true`.
This rule closes that exact public coverage boundary. It does not claim that
the replay loss becomes a match win and does not generalize non-ex evolution
outside this certificate.

## Precedence

The new clear-state proposal ranks immediately below the normal two-Prize
Active-race rule and immediately above existing H5 v2:

1. exact direct-parent terminal;
2. existing active transaction owner;
3. H2 terminal transaction;
4. search-aware terminal transaction;
5. H1 ready-terminal removal;
6. normal two-Prize Active-race rule;
7. this rule;
8. H5 v2;
9. H4 plus Mega Brave veto;
10. H6;
11. Hero's Cape survival;
12. H3;
13. Boss ledger;
14. exact historical-Silver fallback.

Any higher rule, current owner, exact same-turn terminal, or equal/higher
certified route suppresses this rule. Existing components must not be edited.

## Exact transaction

Stages:

`CLEAR -> EVOLUTION_EMITTED -> EVOLVED_CONFIRMED -> ATTACK_EMITTED -> CLEAR`.

At `CLEAR`, arm only when every source certificate below is exact. Snapshot
the game/seat/turn/action identity; Active lineage and serial; evolution card
and serial; three attached Basic Metal serials; Tool; HP/damage; opposing
Active identity/HP; public modifiers; exact-parent Raging Hammer action; and
the expected Coated Attack.

1. Emit the semantic non-ex Archaludon `840` evolution onto the stored Active
   Duraludon.
2. An identical callback returns the same semantic evolution without state
   advancement or a second parent call.
3. On a novel observation, require the exact Active evolution, retained
   Energy/Tool/damage arithmetic, one-Prize liability, and unchanged target.
4. Recompute payment, damage, prevention, and KO from the actual evolved
   observation.
5. If and only if Coated Attack `1212` is the unique deterministic lethal
   attack, emit it.
6. Clear after attack emission or any turn/result/reset boundary.

Before an irreversible evolution, failure clears and returns the exact parent.
After evolution, failure clears and recomputes the genuine parent from the
actual evolved observation; never return a stale stored attack or synthesize
rollback.

## Required public certificate

- ordinary own `MAIN`, unresolved result, supported select context;
- unique existing Active Duraludon `169`, not newly appearing this turn;
- complete, unique public card serials and exact three Basic Metal attached;
- `energyAttached == true` plus public current-turn attachment evidence that
  binds the completed attachment to this same Active;
- unique legal non-ex Archaludon `840` evolution onto that Active;
- exact-parent unique action is Raging Hammer `224`;
- every currently legal inherited attack is nonlethal;
- post-evolution Coated Attack `1212` is currently payable, deterministic,
  and lethal after every supported public modifier;
- evolution retains one-Prize liability, Tool, Energy, and supported HP/damage
  arithmetic;
- H5 v2 urgency remains true: the surviving opposing Active has a currently
  payable deterministic lethal return attack, and no opposing Bench Pokemon
  has a currently payable printed attack;
- no Ogerpon exception, terminal route, higher-ranked owner, reservation, or
  collision.

No replay ID, opponent identity, hidden hand, hidden deck order, Prize
identity, future draw, realized continuation, or opponent-policy assumption
may enter the policy.

## Mandatory fail-closed negatives

Delegate the exact direct parent for at least these sixteen groups:

1. non-Main, mandatory callback, or completed result;
2. Active absent, duplicated, newly appearing, or not Duraludon `169`;
3. `energyAttached == false`;
4. current-turn attachment cannot be bound to the same Active;
5. not exactly three supported Basic Metal Energy;
6. evolution card/target absent, ambiguous, duplicated, or illegal;
7. evolution changes Prize liability from one Prize;
8. Tool, Energy, damage, HP, or lineage inheritance is unsupported;
9. exact-parent action is not unique Raging Hammer `224`;
10. inherited attack already KOs;
11. Coated Attack is unpaid, ambiguous, nondeterministic, prevented, or
    nonlethal;
12. unsupported Stadium, Tool, status, weakness, resistance, reduction, or
    continuous effect;
13. exact terminal, Boss terminal, alternative evolution KO, or equal/higher
    certified route;
14. the surviving opposing Active lacks a currently payable lethal return
    attack;
15. any opposing Bench Pokemon has a currently payable printed attack or its
    public state is unsupported;
16. active/higher owner, Ogerpon/endgame exception, reservation conflict,
    serial mutation, option mutation, duplicate-owner state, or stale state.

Frozen negatives include `87996118` as existing H5 v2 ownership,
`88602602` as a Boss route, `88775564`, `88247531`, `88779311`, all existing
component positives/collisions, and every rejected H3/H4/H5/H6 control.

## Short destructive-safety gate

Do not run fixed-760 or a full replay union.

Required:

1. only candidate `main.py` differs from the direct-parent 12-file runtime;
2. compile/import, loader only/last, legal 60, ACE SPEC one, cache-free;
3. source reconstructed in both logical seats, serial identity/remap, and
   option identity/reversal;
4. exact engine completion:
   `Raging Hammer parent -> non-ex evolution -> retained Cape/Energy ->
   280 maximum HP -> Coated Attack 120 -> Alakazam KO -> one Prize`;
5. at least the sixteen negative groups parent-identical in both seats;
6. duplicate callback, pre-evolution rollback, post-evolution actual-state
   recomputation, target mutation, turn/seat/game/result reset;
7. zero invalid action, exception, stale/two-owner state, nondeterminism, or
   max-step hit;
8. fresh package extraction followed by the same both-seat source smoke;
9. freeze source, deck, tests, outputs, package, and archive hashes.

Passing this gate means destructive-safe for a later diagnostic live probe.
It does not prove strength or authorize skipping the already scheduled
eight-, nine-, and ten-rule live order.
