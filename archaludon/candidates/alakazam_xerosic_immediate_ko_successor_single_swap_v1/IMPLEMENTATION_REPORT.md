# Xerosic immediate-KO successor single swap v1

## Frozen contract and parent

- Contract: `autonomous_gold_20260715/decisions/20260719_0435_alakazam_xerosic_immediate_ko_successor_single_swap_v1.md`
- Contract SHA-256: `E1E107F0E32E109E831DB3FE8347E0D57AD8D3AF2AF5D722154F00C11A4FC67A`
- Parent: `autonomous_gold_20260715/candidates/alakazam_parent_end_strict_prize_lead_retreat_ko_bridge_v3`
- Parent source/runtime/deck SHA-256 after implementation:
  `49E954F53E043CD79D928DFB2340CCB5D85A17F33CCB824C871CCE153C0C9C95` /
  `9CA7A415451B84343165EF8A5CDC0D67BBF1B4969A13C984C09B142B4898CD9A` /
  `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`.
- Destination: `autonomous_gold_20260715/candidates/alakazam_xerosic_immediate_ko_successor_single_swap_v1`
- The rejected global retained-triple ranker was not copied or stacked.

## Exact behavioral change

The original exact-v3 `agent` body is preserved as
`_exact_v3_parent_action`. The public `agent` calls it first exactly once, then
may transform only that returned action. The transform activates only for a
complete opponent-Xerosic callback and all of these public certificates:

1. own hand and unique own-HAND CARD options cover each other exactly;
2. fixed discard count is `handCount - 3` and the parent action is legal;
3. the opponent Active is non-Tera Alakazam with checked-engine Powerful Hand,
   an exact payable Psychic cost, no disabling status, and enough current
   public hand count to KO the own Active at `20 * handCount`;
4. every visible in-play component and skill is publicly complete and has no
   ambiguous attack/effect modifier. Nighttime Mine is accepted only by its
   exact checked text and only because Alakazam is not Tera;
5. exactly one evolution-ready Bench Kadabra has an exact Abra
   pre-evolution fingerprint and exact attached Psychic Energy payment;
6. no own Bench Alakazam can already pay Powerful Hand;
7. the sole hand Alakazam is discarded by the parent and exactly one Rare
   Candy is retained by it;
8. no surviving visible Abra can be a next-own-turn Rare Candy target in
   either the Active-survives or Active-KO branch.

The action then replaces only the discarded Alakazam option with the retained
Rare Candy option. It does not enumerate or rank triples, score draw/search or
disruption, penalize duplicates, inspect hidden identities, or alter any other
action.

The first repaired result replaces the same exact-v3 decision-cache entry.
An identical repeated callback therefore returns the repaired cached action
without running parent side effects twice or leaking the pre-swap action.
Unrelated latches are neither cleared nor rewritten by the wrapper.

## Checked engine/card anchors

The implementation inspected the frozen checked engine directly:

- `cg/api.py`: `C31AA24E63BF0E71779D97F6286D10A2BF23CB4A3B9449C977F63577704FBE6C`;
- `cg/cg.dll`: `0C6153F9206366F2588E5C601AB086EA997A66E80E4FEB6D95635B2987C9929B`.

The source certifies the exact metadata at import/runtime:

- Alakazam `743` is non-Tera Stage 2, evolves from Kadabra, and has only attack
  `1072`;
- Powerful Hand `1072` costs exactly one Psychic Energy, has printed damage
  zero, and places two damage counters per card in the attacker's hand;
- Rare Candy `1079` is an Item whose exact public rule evolves a Basic through
  a compatible Stage 2 in hand;
- Abra `741` / Kadabra `742` are the exact Basic / Stage 1 chain.

## Exact replay anchors

Positive `86657890/133`, replay SHA-256
`E4B18E0A357195BB35F8272A012AA7C48128D3FBDC40FCA18848B494A48FBABF`:

- parent action: `[0,1,2,3,4]`;
- parent retained: Rare Candy `(1079,31)`, Dudunsparce `(66,18)`, Basic
  Psychic Energy `(5,57)`;
- candidate action: `[0,1,2,3,5]`;
- candidate retained: Alakazam `(743,11)`, Dudunsparce `(66,18)`, Basic
  Psychic Energy `(5,57)`;
- exact changed options: remove discard option `4` (Alakazam), add discard
  option `5` (Rare Candy). The other two retained card IDs and serials are
  unchanged.

All nine frozen negatives are exact-parent:

| Episode/step | Exact action |
|---|---|
| `86676249/39` | `[0,1,2,3]` |
| `86674048/24` | `[0,1,2,3,4]` |
| `86666507/108` | `[0..13]` |
| `86665439/67` | `[0..9]` |
| `86665439/137` | `[0,1,2,3]` |
| `86660075/119` | `[0..13]` |
| `86657890/97` | `[0..11]` |
| `86656277/56` | `[0,1,2,3,4]` |
| `86656277/101` | `[0,1]` |

## Exact diff

- `main.py`: two constants; rename the byte-identical exact-v3 entry body to
  `_exact_v3_parent_action`; append checked metadata, callback, KO, modifier,
  successor, Rare Candy, and single-swap certificates plus the parent-first
  cache-safe wrapper. Parent diff: 422 insertions, one rename line.
- `runtime/main.py`: change only the private import-module name to the unique
  candidate identifier.
- `deck.csv`: copied byte-for-byte from the parent; no card change.
- `test_xerosic_immediate_ko_successor_single_swap.py`: focused deterministic
  replay, boundary, cache, permutation, and import-parity tests.
- `IMPLEMENTATION_REPORT.md`: this receipt.
- `exact_engine_smoke/`: generated one-game trace and summary evidence for
  each seat; not policy source and not an archive.

No source outside the assigned destination was edited.

## Final file hashes

| File | Bytes | SHA-256 |
|---|---:|---|
| `main.py` | 176809 | `981CAF68D02100161F99AF548AD1F21C048E1FA01BB618A4A8B0DAAEBF725FAA` |
| `runtime/main.py` | 683 | `4D34FCE70D9D8DB848E1C3886F154ABE092DD76E8676E3F6308E1AC01B1D74D6` |
| `deck.csv` | 262 | `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141` |
| `test_xerosic_immediate_ko_successor_single_swap.py` | 16559 | `66E46EDFBF706654408B6F9F25965564F3D218649C985DC36BE0D91D642A5221` |

## Verification commands and outcomes

Only the mandated interpreter was used:

`C:\Users\amuam\project\AI_pokeka_competition\.venv-rl\Scripts\python.exe`,
SHA-256 `4BDDD834FB6FC274CC20FA7CBFAA6E9B5ADE6309429EB96A635538DBA5D4A3AE`.

### AST and compile

```powershell
& 'C:\Users\amuam\project\AI_pokeka_competition\.venv-rl\Scripts\python.exe' -B -c "import ast,pathlib; p=pathlib.Path(r'<candidate>'); fs=[p/'main.py',p/'runtime/main.py',p/'test_xerosic_immediate_ko_successor_single_swap.py']; [ast.parse(f.read_text(encoding='utf-8'),filename=str(f)) for f in fs]; print('AST_OK files=3')"
& 'C:\Users\amuam\project\AI_pokeka_competition\.venv-rl\Scripts\python.exe' -m py_compile <candidate>\main.py <candidate>\runtime\main.py <candidate>\test_xerosic_immediate_ko_successor_single_swap.py
```

Exit `0`; output: `AST_OK files=3`, `PY_COMPILE_OK files=3`.

### Source/runtime import and metadata

With the checked engine and repository on `PYTHONPATH`, both files were loaded
by `importlib.util` using the mandated interpreter. Exit `0`; output:

`IMPORT_OK source_agent=callable runtime_agent=callable metadata_exact=true deck_rows=60`.

### Focused deterministic tests

```powershell
$env:PYTHONPATH='<checked-engine>;C:\Users\amuam\project\AI_pokeka_competition'
& 'C:\Users\amuam\project\AI_pokeka_competition\.venv-rl\Scripts\python.exe' -m unittest -v test_xerosic_immediate_ko_successor_single_swap.py
```

Working directory: this candidate. Exit `0`; `Ran 11 tests in 2.341s`, `OK`.
The tests cover the positive exact action and retained serials; all nine
frozen negative positions; option-order identity mapping; repeated callback
cache behavior; opponent non-KO and unpaid Energy; disabling status and Mist
effect ambiguity; newly evolved and multiple Kadabra; an already ready Bench
Alakazam; live Rare Candy targets; multiple Alakazam/Candy swap candidates;
malformed effect, owner, serial, hand, count, and option mappings; and
source/runtime/deck parity.

### Deck and parent integrity

The mandated interpreter parsed nonempty deck rows and compared bytes to the
parent. Exit `0`; output:

`DECK_OK rows=60 byte_identical=true sha256=7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`.

All three parent hashes remained equal to the frozen contract values listed
above.

### Checked-engine both-seat multistep smoke

Runner `tools/run_local_battle.py` SHA-256:
`E1ABA0151CDAEE425B858511AA760CE5C5647D555DDEFBD69D7319C29C5B773B`.

Candidate p0:

```powershell
& 'C:\Users\amuam\project\AI_pokeka_competition\.venv-rl\Scripts\python.exe' -B tools\run_local_battle.py --engine-dir analysis_outputs\cynthia_v9_vs_v11_poffin_role_selection_20260713\seeded_engine --agent-a <candidate>\runtime --agent-b autonomous_gold_20260715\baseline\historical_silver_archaludon_54495224 --deck-a <candidate>\deck.csv --deck-b autonomous_gold_20260715\baseline\historical_silver_archaludon_54495224\deck.csv --games 1 --seed-base 2026071901 --engine-seed --max-steps 1000 --trace-options --trace-dir <candidate>\exact_engine_smoke\p0\traces --summary <candidate>\exact_engine_smoke\p0\summary.jsonl
```

Candidate p1:

```powershell
& 'C:\Users\amuam\project\AI_pokeka_competition\.venv-rl\Scripts\python.exe' -B tools\run_local_battle.py --engine-dir analysis_outputs\cynthia_v9_vs_v11_poffin_role_selection_20260713\seeded_engine --agent-a autonomous_gold_20260715\baseline\historical_silver_archaludon_54495224 --agent-b <candidate>\runtime --deck-a autonomous_gold_20260715\baseline\historical_silver_archaludon_54495224\deck.csv --deck-b <candidate>\deck.csv --games 1 --seed-base 2026071902 --engine-seed --max-steps 1000 --trace-options --trace-dir <candidate>\exact_engine_smoke\p1\traces --summary <candidate>\exact_engine_smoke\p1\summary.jsonl
```

Both commands exited `0`:

| Candidate seat | Seed | Steps | Started | Max-step | Action errors | Summary SHA-256 | Trace SHA-256 |
|---|---:|---:|---|---|---:|---|---|
| p0 | 2026071901 | 119 | true | false | 0 | `87B6C2B9233449944913190A601D92D8492A323480495B84B09255A8A5086B50` | `D58168AE288D97CE69D8BFA47DF5B50958975356CA672DBC8710597EC51D40CF` |
| p1 | 2026071902 | 153 | true | false | 0 | `1447920BCB536904B984098FC2C83CD0E14D5B1315D737E0A6578819E5FE3F6B` | `0212F9F9F15A0CFDE92DB1D43F92A2DDC3F38C0434B82B88020E4F17F8344B14` |

Trace bytes are 257349 (p0) and 329565 (p1). These are execution smokes,
not strength evidence.

## Known tradeoffs and evaluator obligations

- The public certificate is deliberately strict. Any incomplete or unusual
  visible skill, component, Energy unit, status, serial, mapping, modifier, or
  branch delegates to exact-v3.
- Every visible Abra is conservatively treated as a next-own-turn Candy target,
  including one that currently carries `appearThisTurn`; this can suppress a
  strategically attractive swap but cannot create a false targetless claim.
- Nighttime Mine is the only additional context-specific visible-modifier
  exception, and only its exact checked metadata is accepted for non-Tera
  Alakazam.
- The rule does not guarantee opponent policy; it proves only that the public
  immediate Powerful Hand attack is payable and lethal if chosen.
- The evaluator must verify every first difference is exactly this one swap,
  preserve the other two retained card IDs/serials, check repaired-cache repeat
  behavior, and trace the complete KO -> Kadabra promotion -> Alakazam
  evolution -> Powerful Hand transaction under the frozen gates.
- The evaluator must run the parent-specified 576-run matrix and later mirror
  confirmation panel. No broad evaluation was run here.
- No archive was created. No package, Kaggle submission, upload, Notebook,
  Discussion, or configuration change was made.
