# v4 C3–C5 Premium Power Pro stacking engine amendment

Date: 2026-07-30

This amendment supersedes the single-copy `+30` cap and Item move-log
requirements in
`v4_c3_public_survival_bench0_fix5_immutable_spec.md`
(SHA-256
`1585C9FC7BEB326E2F496AC8B35D99E5B75A976F0F69C7A8B7492671E7B73B5F`)
and freezes the multiplicity requirement in
`v4_c2_c5_strategy_judge_binding_amendment.md`
(SHA-256
`C33EBED6B5C945924F0ED4AFAC1C0029C9B129D870EE4FE583D3612948CD70B6`).

## Engine-backed rule

Card ID `1141`, `Premium Power Pro`, is a normal Item.  During the current
turn, attacks by the user's Fighting Pokémon do `+30` damage to the opponent's
Active Pokémon before Weakness and Resistance.

Multiple copies may be played in one turn.  The engine applies:

```cpp
playerDamageChangeMyFighting += 30
```

The effects therefore stack:

```text
one copy   +30
two copies +60
three      +90
four       +120
```

The same-name deck limit is four.  The Fighting accumulator resets at turn
end.

Frozen engine evidence:

| Evidence | Relevant lines | SHA-256 |
|---|---:|---|
| `external/ptcg_engine/ptcgProgram 22/CardImpl.h` | 10058–10062 | `286A51820D36F9B60B5B13C58BC2EDFF352EB4050581DDADF1960F13FD6F21A9` |
| `external/ptcg_engine/ptcgProgram 22/GameProc.h` | 819–877 | `CF1537BE5C439BED44FBF08B91A6B066F3878EE5AE8A88A828F110BCE01B3260` |
| `external/ptcg_engine/ptcgProgram 22/EffectInstant.h` | 1720–1723 | `31DA884F26F9D7820D37770DFAA9A54229CD15D1185B41E20D718437FED3F217` |
| `external/ptcg_engine/ptcgProgram 22/PlayerState.h` | 84, 95–105 | `269E7C4A2C1522245FC2DDC1E89CF83412D1B00F1DEED4B673F3275906A412A1` |
| `external/ptcg_engine/ptcgProgram 22/SetProperty.h` | 276–340 | `A563762C4A8F6C1F9C77048B89F770CD2E7A5D4801CD29256196DDA9E40FCB81` |
| `external/ptcg_engine/ptcgProgram 22/Core.h` | 19 | `FDC29455564073B865CC8AC0E0429E66A1DF4A245594B26F939D64BC1D0FD7A3` |
| `external/ptcg_engine/ptcgProgram 22/Api.h` | 58–64 | `EB3FED05503F58BBB515162E259759E9574095C8B65F96B1C0AD97E6A4B1C8BD` |

An existing engine trace contains two separate `Play(1141, serial)` events in
the same turn:

- `analysis_outputs/cynthia_v23_rotation_local_population/mega_lucario/p0/game_0000.jsonl`
- relevant lines: 54 and 56
- SHA-256:
  `81352BF11EE3541B69D01C4C3DE2AD58DFDB4C6F3222EF70BB25CAF88C4EC21F`

## Physical-copy ledger

Deduplicate all evidence by physical `serial`.

```text
C_t = distinct 1141 serials with a valid Play log in the current
      opponent turn before the attack

U_t = distinct 1141 serials that public information proves cannot be
      played again before that attack

N = 4
```

`U_t` includes public discard or another public, currently unrecoverable zone.
Resolved current-turn copies normally belong to both `C_t` and `U_t`.

Current-turn supported stack:

```text
additional_max = max(0, N - |C_t union U_t|)
stack_max_current = |C_t| + additional_max
premium_cap_current = 30 * stack_max_current
premium_floor_current = 30 * |C_t|
```

For a later turn, the current accumulator has reset:

```text
stack_max_future = max(0, N - |U_future|)
premium_cap_future = 30 * stack_max_future
premium_floor_future = 0
```

Re-evaluate public zones at every callback.  If a serial is recovered from
discard, it leaves `U`.  A card merely revealed in deck or hand remains
playable and does not reduce the ceiling.

If game/turn ownership, serial identity, zone, recovery status, or accumulator
lifetime is ambiguous:

- committed floor becomes `UNKNOWN` for the affected attack;
- C3 retains the parent action;
- C4/C5 `safety_cap` is `UNKNOWN`;
- no reusable wall is certified.

## Correct Item-use evidence

Normal Item movement Hand→Playing and Playing→Trash uses `noLog=true` in the
engine.  A Hand→Discard `MoveCard` log therefore must not be required.

Frozen evidence:

| Evidence | Relevant lines | SHA-256 |
|---|---:|---|
| `external/ptcg_engine/ptcgProgram 22/GameProc.h` | 121, 152–155 | `CF1537BE5C439BED44FBF08B91A6B066F3878EE5AE8A88A828F110BCE01B3260` |
| `external/ptcg_engine/ptcgProgram 22/CardMove.h` | 109–122 | `7252D27C63C539C30899E3C7136E34506E9B3BE3F09E974CFC4B2F3139E26A0D` |
| `external/ptcg_engine/ptcgProgram 22/AddLog.h` | 99 onward | `70C4B980FD7B64FD53E4ADD3269DE076546B8F3284304D6CCA84B6B070AEF869` |

A committed copy requires:

1. `Play(cardId=1141, serial=s)` by the correct actor in the exact current
   game and turn;
2. duplicate callbacks collapsed to one physical serial;
3. after resolution, the same serial in the public Trash as an integrity
   check.

A direct discard of `1141` without `Play` proves that the copy is unavailable;
it does not add `+30` to the floor.

## C3 evidenced policy cap

After the original family-marker, same-battle reveal, and two-public-list
evidence gates pass, use `N=4` and the formulas above.  Both frozen public Mega
Lucario lists contain four copies:

- `meta_agents/mega_lucario_aib4_live_84983544_simple/deck.csv`
  — `2A541D7BF3D9E6B36037123F53F4DFEF6348223F79FD27095DAFC602A5357C19`
- `meta_agents/mega_lucario_fujiborozoukin_live_85033862_simple/deck.csv`
  — `D6B1417B848C75991BCF1EA5FE96E65A2B8A56FEC27DCD95DDC51005A6C1E90E`

This is a supported maximum, not a claim that every hidden copy is currently
held.  C3 may use it only in the already-frozen low-cost, cap-only board-out
comparison.

Family markers without a same-battle `1141` observation remain
`ARCHETYPE_COMMON_UNCONFIRMED` and do not produce a numerical C3 cap.

## C4/C5 safety cap

When the public evidence supports the four-copy family, begin at the legal
four-copy maximum and subtract only copies proven unusable by public state.
Then apply all other supported modifiers, Weakness, and Resistance in engine
order.

`CERTIFIED_REUSABLE_WALL` requires:

```text
wall_hp > final_safety_cap
```

The comparison is strict.  Equality is a KO and does not certify survival.
Any unresolved additional modifier makes the final safety cap `UNKNOWN`.

## Episode 88843743 correction

Replay:

- `C:/Users/amuam/Downloads/88843743.json`
- SHA-256:
  `B0B8752CA10D9319C667A5482323BF8A780A3038FFDD50AF7DCF588EDA882948`

Public facts:

- `steps[7][0]`: card `1141`, serial `27`, is discarded without `Play`.
- `steps[41][0]`: card `1141`, serial `26`, has a valid `Play`.
- `steps[42][0]`: Solrock's 70-damage attack resolves for an observed 100.

Before the later attack, when only serial `27` is publicly unavailable, the
next-turn supported cap is:

```text
Solrock 70 + three remaining copies * 30 = 160
```

At the actual attack:

```text
C_t = {26}
U_t = {26, 27}
stack_max_current = 1 + (4 - 2) = 3
supported safety cap = 70 + 90 = 160
committed floor = 70 + 30 = 100
```

The observed attack used one copy and dealt 100.  That observation must not be
misreported as proof that 100 was the maximum legally supported damage.

If both serials remain in Trash on a later turn, only two copies remain
playable and the later neutral cap becomes `70 + 60 = 130`.

C3's episode fixture therefore keeps:

- Run Away unchanged at C3;
- Hilda unchanged;
- Shaymin as the low-cost Bench-0 candidate before the same Kadabra attack;

but replaces the old single-copy cap `100` with the supported cap `160`.
At that earlier state, Dudunsparce at 120 HP is not a certified reusable wall
against the full supported stack.

## Additional mandatory fixtures

1. Two current-turn `Play` serials produce committed `+60`.
2. Four legal copies produce cap `+120`.
3. A direct discard without `Play` reduces future copy count but adds no
   current floor.
4. Duplicate callbacks for one serial add only `+30`.
5. A recovered serial leaves `U` and raises the later cap.
6. Current-turn committed copies and future-turn available copies use
   different formulas.
7. `88843743` distinguishes observed floor 100 from supported cap 160.
8. Missing turn boundary, serial, or public-zone proof yields `UNKNOWN` and
   no action change.

