# Alakazam exact-Xerosic certified retained-triple v1

## Scope and frozen parent

- Parent directory: `autonomous_gold_20260715/candidates/alakazam_parent_end_strict_prize_lead_retreat_ko_bridge_v3`
- Parent `main.py` SHA-256: `49E954F53E043CD79D928DFB2340CCB5D85A17F33CCB824C871CCE153C0C9C95`
- Parent and candidate `deck.csv` SHA-256: `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`
- Candidate directory: `autonomous_gold_20260715/candidates/alakazam_xerosic_certified_retained_triple_v1`
- No deck change and no unrelated parent-policy change were made.

## Behavioral change

The new overlay activates only when every one of the following public facts is
exact:

1. `SelectContext.DISCARD`;
2. `select.effect.id == 1197` and the effect is the opponent's positive-serial
   Xerosic card;
3. `contextCard is None` and the complete own hand is visible;
4. every option is a `CARD` option in the own `HAND`, maps to a distinct valid
   hand index and distinct positive serial, and the options cover the hand
   exactly once;
5. `minCount == maxCount == handCount - 3`.

On a certified callback it enumerates all legal retained triples and returns
the discard complement in option-index encoding. The deterministic
lexicographic rank uses only public state and models both current-Active
survival and current-Active removal. Its ordered plan components are complete
attack succession, an energized Kadabra plus retained Alakazam, a visible
Kadabra plus retained Alakazam, deck-safe Dudunsparce evolution, a live
draw/search/recovery route, energy only when it improves an attack route, and
publicly targetable disruption. Dead Rare Candy, irrelevant Psychic Energy,
dead Stadium/Tool copies, and duplicates are penalized. Stable `(card id,
serial)` fingerprints are the final tie-break, so option order cannot decide
the cards retained.

All ambiguity fails closed to the exact parent. The overlay is called after
the parent's emergency-state preparation and idempotence cache check; outside
the exact callback the original scoring and overlays run unchanged.

## Exact live-anchor activation

### Episode 86657890, observation step 133

- Replay SHA-256: `E4B18E0A357195BB35F8272A012AA7C48128D3FBDC40FCA18848B494A48FBABF`
- Parent action: `[0, 1, 2, 3, 4]`
- Parent retained: Rare Candy `(1079,31)`, Dudunsparce `(66,18)`, Basic
  Psychic Energy `(5,57)`
- Candidate action: `[0, 2, 3, 5, 7]`
- Candidate retained: Hilda `(1225,50)`, Alakazam `(743,11)`, Dudunsparce
  `(66,18)`
- Candidate discarded: Shaymin `(343,22)`, Rare Candy `(1079,33)`, Enhanced
  Hammer `(1081,39)`, Rare Candy `(1079,31)`, Basic Psychic Energy `(5,57)`
- Certified plan difference: the held Alakazam is retained for visible,
  energized Bench Kadabra `(742,8)` if Active Alakazam is removed. The Basic
  Energy has no marginal attack role because that Kadabra already has
  Telepath Psychic Energy `(19,61)`.

### Episode 86666507, observation step 108

- Replay SHA-256: `17D8A116CDF58F819CFD264AD8D70A889F5FF4E926C3347CE441E68426CD6867`
- Parent action: `[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13]`
- Parent retained: Rare Candy `(1079,33)`, Rare Candy `(1079,32)`, Dunsparce
  `(305,16)`
- Candidate action: `[0, 1, 2, 3, 4, 5, 8, 9, 10, 12, 13, 14, 15, 16]`
- Candidate retained: Dudunsparce `(66,17)`, Dawn `(1231,46)`, Telepath
  Psychic Energy `(19,61)`
- Candidate discarded: Hilda `(1225,49)`, Hilda `(1225,50)`, Battle Cage
  `(1264,54)`, Psyduck `(858,21)`, Enhanced Hammer `(1081,39)`, Fezandipiti ex
  `(140,19)`, Dudunsparce `(66,18)`, Rare Candy `(1079,31)`, Hilda `(1225,48)`,
  Shaymin `(343,22)`, Enhanced Hammer `(1081,40)`, Rare Candy `(1079,33)`,
  Rare Candy `(1079,32)`, Dunsparce `(305,16)`
- Certified plan difference: one deck-safe Dudunsparce route, one live
  three-card Dawn route, and the one Psychic Energy that improves the visible
  replacement Abra attack line replace two dead Rare Candy copies and a
  redundant Dunsparce.

At both anchors the candidate retained-triple rank is strictly greater than
the parent's retained-triple rank. Repeated calls return the same action, and
reversing the option list retains the same card IDs and serials.

## Files and final hashes

| File | Bytes | SHA-256 |
|---|---:|---|
| `main.py` | 175201 | `60C5899F8E709996FBFEC23133E595AE5369E10956289307B20025F106673AF0` |
| `deck.csv` | 262 | `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141` |
| `runtime/main.py` | 674 | `83EDC85D28D40161A476E6A7231F03D43EB5638F8C18F1B99F805BFB071ED173` |
| `test_xerosic_certified_retained_triple.py` | 11042 | `57E34B6CA572024E4E8EFC166B9A1D66A448D3CC27A28A1C1D8093050A8C82FF` |

Changed source spans are the `itertools.combinations` import, card ID constant
at line 55, exact-Xerosic helpers at lines 159-548, the two-line overlay call
at lines 3999-4001, and the runtime module-name isolation. The test file and
this report are new. `deck.csv` is byte-identical to the parent.

## Verification commands and exact outcomes

### Compile

```powershell
py -3.11 -m py_compile <candidate>/main.py <candidate>/runtime/main.py <candidate>/test_xerosic_certified_retained_triple.py
```

Exit `0`.

### Focused replay, boundary, determinism, and parent-equivalence tests

The checked seeded engine directory was placed on `PYTHONPATH`, then:

```powershell
py -3.11 -m unittest -v test_xerosic_certified_retained_triple.py
```

Result: `Ran 10 tests in 1.511s`, `OK`.

The ten tests cover both exact replay callbacks, exact actions and retained
IDs/serials, strict rank improvement over the parent retained triples,
repeatability, option-order permutation, wrong effect, non-DISCARD context,
non-own-hand and malformed/duplicate mappings, wrong count/not-exactly-three,
unsafe-deck Dudunsparce suppression, absent visible evolution-route
suppression, action validity, and 24 real replay observations that are
byte-for-byte action-equal to the parent outside the exact callback.

### Runtime wrapper and initial request

Loading `runtime/main.py` against the checked engine produced a callable
`agent`, resolved `_SOURCE` to this candidate's `main.py`, returned
`[0, 2, 3, 5, 7]` at episode 86657890 step 133, and returned exactly 60 deck
rows when the same observation's `select` was set to `None`.

### Deck legality/equality

- Nonempty `deck.csv` rows: `60`.
- Byte comparison to the frozen parent: equal.
- Hash comparison to the frozen parent: equal.

### Checked exact-engine both-seat smoke

Runner SHA-256:
`E1ABA0151CDAEE425B858511AA760CE5C5647D555DDEFBD69D7319C29C5B773B`.
Engine `cg/api.py` / `cg/cg.dll` SHA-256:
`C31AA24E63BF0E71779D97F6286D10A2BF23CB4A3B9449C977F63577704FBE6C` /
`0C6153F9206366F2588E5C601AB086EA997A66E80E4FEB6D95635B2987C9929B`.

The commands were the checked `tools/run_local_battle.py` invocation with
`--games 1 --engine-seed --max-steps 1000 --trace-options`, first with the
candidate as player 0 at seed `2026071901`, then as player 1 at seed
`2026071902`, against the exact historical-Silver Archaludon anchor.

Authoritative final outputs are under `exact_engine_smoke_final/`:

| Seat | Exit | Started | Steps | Max-step | Action errors | Summary SHA-256 |
|---|---:|---:|---:|---:|---:|---|
| candidate p0 | 0 | true | 119 | false | 0 | `57CB13497E43BD95F40A97ACC5B6415264B98D6B149A061C0108897BD5C5EC0D` |
| candidate p1 | 0 | true | 153 | false | 0 | `F4BFDB09EE765A9A594E517ADCA85C363F44888D4DE309E0509BEBD6781F0249` |

The p1 smoke contained a different `DISCARD` callback (`effect.id == 1121`);
the candidate delegated it normally. Exact Xerosic activation is therefore
proven by the two public replay callbacks, while the complete checked-engine
games prove valid multi-step execution in both seats. No win-rate inference is
made from these two smoke games.

## Known tradeoffs and evaluator targets

- Certification is deliberately strict. Any partial option set, hidden hand,
  unexpected owner, duplicate mapping/serial, nonpositive effect serial, or
  count mismatch delegates to the parent.
- The rule uses no hidden top-deck, hidden prize identity, learned score, or
  opponent-policy proxy. Consequently, it values only routes whose activation
  and capacity are visible now; it cannot guarantee a particular searched or
  drawn card.
- Draw safety conservatively reserves the mandatory next-turn draw and
  requires the resulting deck to remain strictly larger than the own prize
  count.
- The evaluator should freeze these four files, run identical both-seat seeds,
  inspect every changed Xerosic position, and specifically test Alakazam
  mirrors and Xerosic-bearing Great Tusk/Lucario panels while retaining the
  historical-Silver and adjacent non-Xerosic floors.
- No broad stochastic evaluation, packaging, archive creation, or Kaggle write
  was performed.
