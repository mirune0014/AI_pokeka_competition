# Deferred loss memo — episode 88827776

Status:

`ROOT_VERIFIED_SAME_TURN_TERMINAL_COMPONENTS__NO_BOSS_BRANCH_GATE_REQUIRED`

This loss is not Hero's Cape causal evidence. The submitted Hero candidate and
the exact historical-Silver parent were identical across all 67 correct-seat
callbacks, with zero Hero starts, action differences, invalid actions,
exceptions, or stale transactions.

- replay SHA-256:
  `7B3D23A6F04179A10E6B972033D8D84151FDBD81FB6D6AB47AC3D6129DBADD8A`
- Hero shadow SHA-256:
  `75D07AE7D2E0354CFD41F9042901E59EF2F306B3F8E36DFCB25B8B26B250DABE`
- formal parent SHA-256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`

Root verification:

- verifier:
  `root_verification/archaludon_search_aware_active_terminal_88827776_20260730/verify_search_aware_active_terminal.py`
- verifier SHA-256:
  `0EEAF12C4DAFBEAA37CDD9DEF329E6F143F3893F1BB959CCC4900A0B83265CC4`
- output:
  `root_verification/archaludon_search_aware_active_terminal_88827776_20260730/root_verification.json`
- output SHA-256:
  `3FE0588CF32565D945902F9BAE9171B031F75093D214DEC716495243B150C33E`

## Root-verified public transition

At row `134`, turn `12`:

- we had exactly three Prizes remaining;
- our established Active Duraludon `169#66` had three Metal and could evolve;
- opposing Active Mega Lucario ex `678#16` was worth three Prizes;
- it had exactly `220` HP remaining under Hero's Cape;
- our hand contained two Ultra Balls;
- no Supporter had been played.

The parent scored each Boss's Orders `4200`, each Ultra Ball `300`, Raging
Hammer `80`, and Hammer In `30`. It selected Boss, then selected the
one-Prize Solrock target. The parent failed to include a searchable
Archaludon ex in its active-lethal planning before Boss arbitration.

The rest of the actual same turn proves every enabling component:

1. Ultra Ball was played legally;
2. its public search exposed three Archaludon ex copies;
3. Archaludon ex `190#67` legally evolved the established Active Duraludon;
4. Assemble Alloy resolved and attached Metal;
5. Metal Defender was legal and dealt the observed `220`.

On the realized path this attack hit the Bossed Solrock for one Prize. Without
the Boss diversion, the unchanged original Active was already exactly within
the same `220` damage and worth all three remaining Prizes.

## Candidate hypothesis

`SEARCH_AWARE_ACTIVE_TERMINAL_BEFORE_BOSS`

Before any Boss score can replace the current Active, enumerate a certified
same-turn active-lethal transaction that starts with a legal search Item:

`Ultra Ball -> exact discard -> Archaludon ex search -> Active evolution -> optional Assemble Alloy resolution -> stored Metal Defender -> all remaining Prizes`.

Required gates:

1. remaining Prizes exactly equal the unchanged Active's verified Prize value;
2. target HP and exact public damage, prevention, Weakness, Resistance, Tool,
   Stadium, and temporary effects prove lethal;
3. the Duraludon is established, uniquely identified, and legally evolvable;
4. Ultra Ball is legal, its discard payment is feasible without consuming the
   required route, and an Archaludon ex is actually present in the public
   search choices;
5. the selected evolution serial, Active serial, target fingerprint, Prize
   counts, Energy payment, and stored attack are revalidated at every callback;
6. exact terminal Boss lines may compete, but non-terminal Boss targets cannot
   preempt this route;
7. duplicate callbacks, changed options, unsupported effects, missing search
   target, or any fingerprint mismatch roll back to the parent snapshot.

## Mandatory pre-edit limitation

The actual replay proves all components after Boss, but the exact no-Boss
branch has not yet been executed. Before source implementation, a checked
both-seat engine counterfactual must prove:

`skip Boss -> Ultra Ball -> discard -> Archaludon ex -> evolve the unchanged Active -> resolve Alloy -> Metal Defender into the unchanged Mega Lucario ex -> take three Prizes`.

This is the strongest current exact-win source because it contains no
opponent-response interval and does not require hidden-hand inference. It must
still be implemented as a transaction, not as a broad rule to avoid Boss.

Do not stack it into Hero's Cape or use the episode ID as a policy condition.
