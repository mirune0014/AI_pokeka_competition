# Decision: reject Xerosic certified retained-triple v1

- Recorded: 2026-07-19 04:37 JST
- Decision: **REJECT; do not package, submit, or stack**
- Retained parent: exact-v3
- Kaggle slot used: no

## Frozen artifacts

- parent source/runtime/deck:
  `49E954F53E043CD79D928DFB2340CCB5D85A17F33CCB824C871CCE153C0C9C95` /
  `9CA7A415451B84343165EF8A5CDC0D67BBF1B4969A13C984C09B142B4898CD9A` /
  `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`;
- candidate source/runtime/deck:
  `60C5899F8E709996FBFEC23133E595AE5369E10956289307B20025F106673AF0` /
  `83EDC85D28D40161A476E6A7231F03D43EB5638F8C18F1B99F805BFB071ED173` /
  `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`;
- certified paired-evaluation freeze:
  `F793CF3268F8095A18ADB1FD222292F3B784C21880E220A8E0EEA0DE7E69B1C5`;
- 576-row raw ledger:
  `E1205236690CF5D9464E19768E716946BAC04ED3C5963012B605AC15792282F6`;
- Sol-Ultra numerical audit:
  `05BA130B3318BB6AC205285B4C3839F747652C01B6A22F36361C9EEDEE4B4ABD`;
- Sol-Ultra current-50 qualitative audit:
  `417E77BEB9FBA63BD5735505076C8DBDD64124AD84E6770CC23D9305D452133D`;
- root certified replay-v2 verification:
  `374C4DD33738BAEE3EDAA0A3F64535C18A01061289F34F38DEAD3BEA48E5CA1E`;
- certified replay-v2 ledger:
  `19D3271445904D749B2DA4D6882E8CA620B07A0C7DE7B83B530D6400FE3F18AD`.

## Root-recomputed result

- exact duplicate controls: 144/144 baseline and 144/144 candidate summary
  and trace matches;
- baseline/candidate: 86/144 -> 86/144;
- paired outcomes: 4 gains, 4 regressions, 136 ties;
- P0: 45/72 -> 43/72; P1: 41/72 -> 43/72;
- known/fresh: 44->46 / 42->40;
- Historical-Silver: 8/16 -> 8/16;
- Alakazam-Rmy: 7/16 -> 7/16;
- Kangaskhan/Crustle: 10->9; Marnie: 11->12;
- every primary first difference: exact opponent-Xerosic callback, 43 keys;
- eight changed outcomes, including four exact-v3 wins becoming losses.

The aggregate tie is not safety parity: substantial rule exposure merely
trades four wins for four different wins and violates the zero-regression and
P0 gates.

## Qualitative blockers

- `86674048/24`: generic duplicate penalty discards a second immediately live
  Kadabra, and its Psychic Draw 2, for a targetless Enhanced Hammer;
- `86666507/108`: Dawn is called a certified three-card search despite public
  inventory allowing at most one and possibly zero target;
- `86656277/101`: the Active-survives branch is called attack-complete although
  an unenergized Active Kadabra has no public retreat, switch, Energy, or
  evolution access;
- `86657890/133`: energized-Kadabra plus retained-Alakazam is a correct
  successor diagnosis, but it does not justify the global ranker.

## Recorded execution defects

The raw simulation outcomes and duplicate controls are internally exact, but
the evaluation artifact is also formally noncompliant:

- all 576 ledger trace facts falsely record missing traces;
- all 576 displayed command strings duplicate the runner prefix, although the
  inspected `Start-Process` argument array executed it once;
- no ledger row contains all promised frozen hashes;
- the runner did not itself enforce duplicate, action-error, max-step, and
  opponent-hash fail-fast controls.

Independent post-hoc verification does not silently repair those defects.
They are recorded separately from the strategic failure, which is already
sufficient to reject the candidate.

## Next experiment

Return directly to exact-v3 and implement only the separately frozen
`xerosic_immediate_ko_successor_single_swap_v1` parent-action repair.  It may
swap a targetless retained Rare Candy for the only discarded Alakazam when a
fully public opponent Powerful Hand KO would otherwise strand an energized,
evolution-ready Bench Kadabra.  It must preserve the other two parent-retained
cards and fail closed everywhere else.
