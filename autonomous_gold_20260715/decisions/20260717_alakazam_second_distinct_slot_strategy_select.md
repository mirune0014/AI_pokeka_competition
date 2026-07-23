# Alakazam second distinct slot — fragile-Bench Prize-clock guard v1

- Judgment date: `2026-07-17` (JST)
- Role: read-only Sol-Ultra strategy judge
- Judgment: **no materially distinct submission-ready ACCEPT artifact exists;
  SELECT exactly one isolated implementation/screen**
- Candidate name: `alakazam_fragile_bench_prize_clock_guard_v1`
- Package/Kaggle authorization: **none before implementation, paired evidence,
  qualitative audit, and final Sol-Ultra judgment**

## Inventory disposition

The only adopted Alakazam improvement is Run Away Draw actual-capacity v3:
source/runtime/deck SHA-256
`5F8F6578BF98BC285BB468FAD26969A22EDA96378F8E3AE35F134EA70EB91830`,
`BDEA6ABD3D0B8BB252C0DDA27B3E095432EACD1EFC45E64D96BE1F7FF05A7170`,
`7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`.
Its accepted broad result is parent `819/1440 -> 829/1440`, 11 gains/one
regression, with zero negative combined-opponent floor. Authorities are the
broad raw-tree digest
`5F77DE190AD2DCB94F4EE737D301C6A798BFE4074C45D5A8A8CE27F0A7A4BB78`,
numerical audit
`05282733F5C48E4873B929A6D689CD1E14DE22E8AF7D01183B42CA34B08C066C`,
and final ACCEPT
`FC3D38CAA1DE6EF519570320B02CC7B8B56FCADA7457E17D638D550882C8F32B`.
It is excluded here because its mechanism is the first-slot mechanism.

Every materially different completed artifact is closed:

| Artifact | Source / decision SHA-256 | Raw disposition |
| --- | --- | --- |
| Neutralization Zone v1 | `31B28A5ACFCF1B50B0E8F37851593E4F4B92BED95DE9B781E0F5E2C250C3C955` / `EF45C106FE66A74B3A0AC1B9F6B4BCD86E3049F864D77756C15A9DD1B9FDD564` | `369->403`, but adjacent `-9/240`, Great Tusk and Rmy each `-5/80`: rejected. |
| Acerola v2 | `F71FBB59D2B789B3D76246B94A2396B3674A313399E04E4FBA109B4C297B9888` / `99E06D6DA7F6C69F9733323B6E360039BA7726AE3C3BA4F1B189840976C84080` | `388->386/640`, target `-4`, Historical-Silver `-1`: rejected. |
| Visible mill-clock v1 | `02684FDBF5EBD9617BD9BDFEA302069EFEFB197F67633C210B280AAEAE1B6E86` / `3E01D0548722B43020181A2F07D6542B134911B7BADF9D33B2414654099CA736` | Phase 0 gained `0/8->3/8` but qualified only `3/8` and removed parent KOs: rejected. |
| Protected-Tusk Kadabra v2/v3 | `62529EF8D680A18B2ECC7AC98683B6609F2F6484371BFE92E596255E3C5FED9B`, `7F2BAC096A9BAE6E71471AA8C9FD565BAA3F7D259B008C4B5E98BC72E6DA77E0` / `28001C0A5274669C109E73D6BD3E9A9B99B7D2B193109B79F10F3BBA4A15340C`, `D03DAB50A92102649381CDE5F953A463F52344D436A266F74C547D5A70E35CCD` | Both gained `0/8->2/8`; v2 regressed prizes and v3 lost a certified same-turn KO: rejected and mechanism terminated. |
| Sustained Prize-lane audit v1 | numerical `F4038BD1C6B32B90D2554509A7603D0FD140231299D66526A783E24BB8B52557` / NO-SELECT `2048CB114F6A4BB36C8F06260CED0BE067F0EBB64C8419117E64BEA8DCF4F100` | Only one loss schedule stayed inside the opponent-choice boundary; 5 independent matched controls: no implementation. |

Run Away Draw v1/v2 are also rejected, not alternative mechanisms (decisions
`478D5D0E7506AE70FB6883BC01D96106960894FDD6C599197C92D8BBE2A86F7A`
and `6459D260D1B1E43988F587C6C9130F24069E5999640897D1E6F7AA3D275348EA`).
The exact public Best-5 source
`DF4D597F593950B0D0C372F3E0BB26C182C4116648977F15ADBB329A6BA922F4`
is a baseline, not a second improvement. Files named
`historical_silver_alakazam_*` are Archaludon agents targeting Alakazam and
are not Alakazam-deck candidates. Therefore no already validated distinct
artifact may safely consume the second slot.

## Selected single hypothesis

Use frozen v3 unchanged as parent. Preserve its Run Away Draw action. Change
only the later decision to Bench Abra `741` when that body is publicly
stage-dominated and can give the opponent the next Prize under an already
ready spread attack.

After computing the exact v3 score vector, the overlay may run only when all
of these public predicates hold:

1. context is MAIN and v3's top-ranked action is `PLAY` Abra `741`;
2. own Active is Alakazam `743`, has Psychic Energy `5` or `19`, and legal
   Powerful Hand `1072` is offered, preserving the current attack (H0);
3. opponent has at most three Prizes remaining;
4. opponent Active has a conservatively certified ready spread attack:
   Mega Starmie ex `1031` with Water Energy `3` for Jetting Blow `1487`
   (50 Bench damage), or Dragapult ex `121` with Fire `2` plus Psychic
   `5/19` for Phantom Dive `154` (six freely placed damage counters);
5. the new full-HP Abra is within that public Bench-damage bound; and
6. a distinct Bench line already stage-dominates the new Abra: Bench
   Alakazam `743`, or Bench Kadabra `742` with Alakazam `743` already in
   hand. Thus the new Abra cannot advance the earliest public evolution
   depth of the successor; it only adds redundancy and an immediately
   exposed one-Prize body.

When all predicates hold, set **all** legal `PLAY Abra` scores to `-1` for
that observation and choose the exact next-highest v3 action. Recompute on
every observation. No other Pokemon, setup choice, attack, target, Boss,
draw, evolution, attachment, retreat, Supporter, deck card, or tie-break may
change. Do not key on opponent name, seed, prior Run Away Draw, or replayed
action. Unsupported Energy or attack interactions fail closed.

This is materially different from v3: v3 decides whether three cards improve
the current hit bound; this rule decides whether a later Bench placement
improves successor timing enough to justify advancing the opponent's public
Prize clock. It is a deterministic `current attack -> Bench liability -> H1
stage dominance -> next Prize` rule, not one bad-action avoidance.

## Frozen evidence and rapid evaluation

The accepted-v3 broad evidence contains 10 matching parent `PLAY Abra`
events in 9 unique schedules across known, fresh, and new-fresh blocks, both
seats, Starmie and Dragapult. Six are parent wins and three are parent losses;
the losses include, but are not limited to, the v3 Starmie regression
`new_fresh/starmie/p1/2026091719`. This diagnostic count was recomputed from
the frozen v3 raw tree above; it is an opportunity ledger, not promotion
evidence.

### Phase 0

Materialize those exact 9 keys plus deterministic boundary controls: ready
spread with opponent Prizes 4-6, no stage-dominating Bench line, no ready
spread Energy, and non-target Historical-Silver plus both Alakazam mirrors.
Run v3 and candidate on identical seeds in both seats with the checked engine,
`--trace-options`, and `max_steps=1000`.

All gates are conjunctive:

- compile/import, legal unchanged 60-card deck, exact schedule equality,
  deterministic repeat, zero action errors and max-step hits;
- every first divergence is only v3 `PLAY Abra` versus candidate next-best
  legal v3 action at the exact predicate; every boundary control is
  trace-identical;
- Powerful Hand remains available and is not delayed past the parent attack
  turn; the stage-dominating Bench line is retained;
- all six matching parent wins remain wins and no terminal Prize count
  regresses;
- at least one of the three matching parent losses becomes a win, or at least
  two take an additional Prize/retain an additional attack without any
  matched-control regression; and
- all changed traces receive qualitative Prize-clock, H0, H1, Bench-exposure,
  and deck-clock review. Any failed clause stops this exact hypothesis.

### Broad retention

Only after Phase 0 passes, run candidate-only on the exact accepted-v3
1,440-key schedule (nine opponents, both seats: known/fresh 20 games per cell
and new-fresh 40), reusing the frozen v3 parent raw evidence. Require:

- candidate at least `830/1440`, zero parent-win-to-loss regressions, gains
  greater than regressions, and nonnegative delta in each seat and each of
  the three blocks;
- Starmie and Dragapult each nonnegative and combined at least `+1`;
- all seven non-target opponents, including Historical-Silver and both
  Alakazam mirrors, result-and-trace identical to v3;
- every changed first action satisfies the exact predicate, every parent
  immediate KO and attack turn is retained, and the claimed Bench Prize is
  actually withheld before the next own turn in every promotion-supporting
  trace.

The stop conditions are any source spillover, invalid action, parent-win
regression, negative target/seat/block floor, failure to withhold the exposed
Prize, or dependence on hidden draws/opponent choices. Passing these screens
still authorizes only a final Sol-Ultra accept/reject judgment; it does not
claim live Bronze or authorize submission by itself.
