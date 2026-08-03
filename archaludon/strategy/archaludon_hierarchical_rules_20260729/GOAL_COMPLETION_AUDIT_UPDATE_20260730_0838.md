# Archaludon hierarchy completion-audit update

Audit time: 2026-07-30 08:38 JST.

Conclusion: `INCOMPLETE__KEEP_GOAL_ACTIVE`.

This file updates
`GOAL_COMPLETION_AUDIT_UPDATE_20260730_0803.md` after the eleventh cumulative
rule was implemented and packaged. It neither promotes a formal parent nor
authorizes a Kaggle write before the post-09:00 authenticated refresh.

## Frozen baseline

- exact historical-Silver `main.py`:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`;
- frozen deck:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.

Both remain unchanged.

## Eleventh rule: post-attachment non-ex 120 KO

The eleventh rule is integrated directly over the ten-rule candidate:

- candidate:
  `archaludon_cumulative_post_attachment_nonex_120_visible_ko_v1`;
- source SHA-256:
  `154B2607A57F839C56ECB97350CEA3842ED1C55B70215A43BFFB2ABD0093A0B3`;
- direct parent SHA-256:
  `C15CA505A9B7D9BC5DEE58D74647FD9C702EDBA3CC040CB43A6308293D61CC82`;
- clean archive SHA-256:
  `A2720434AF8DFF47D25E9FCD5B4484516912EE498CBDF0A51E95FEF723FAA677`.

In the exact source-shaped state, the parent uses Raging Hammer for 80 after
attaching the third Metal Energy to a Cape-bearing Duraludon. The new rule may
instead evolve into one-Prize Archaludon and use Coated Attack for 120 to KO a
110-HP one-Prize Alakazam. It requires at least one publicly ready Bench
successor and proves that every currently payable supported successor attack
is nonlethal against the evolved 280-HP Active. Unsupported cards, incomplete
Energy information, dynamic damage, chance, attack side effects, public
modifiers outside the audited registry, or a lethal Basic-attacker
counterfactual fail closed.

The short destructive-safety gate passed:

- eight positive variants across both logical seats, serial remaps, and option
  reversal;
- 34 negatives across 17 groups and both seats;
- four known H5-v1 harmful controls remained direct-parent identical;
- two exact-engine transactions, one per seat, retained Cape and three Metal,
  reached 280 HP, used Coated Attack for 120, removed Alakazam, and took one
  Prize;
- duplicate handling, pre/post-evolution rollback, turn/seat/game/result
  resets, option reversal, and serial mutation passed;
- zero invalid actions, exceptions, stale/two-owner states, nondeterminism,
  and max-step hits;
- compile/import, legal 60 cards, ACE SPEC one, 12 runtime files, and no cache
  entries passed.

No fixed-760, full replay shadow, or local win-rate evaluation was run.

## Package loader defect caught and repaired

The first package attempt at 08:34 is rejected and permanently marked
`DO_NOT_SUBMIT`. Although AST order ended with `agent`, redefining an existing
dictionary key did not move that name to the end of the Kaggle-style
insertion-order callable namespace. Fresh-package loader emulation therefore
selected a different callable.

The source was repaired by re-registering the final entry point at EOF without
changing policy behavior. The clean 08:37 package then passed:

- exact insertion-order loader selects final callable `agent`;
- staging and fresh extraction contain identical 12-file maps;
- only `main.py` differs from exact historical-Silver;
- extracted-package seat-0 smoke: 145 steps, zero action errors/max-step hit;
- extracted-package seat-1 smoke: 76 steps, zero action errors/max-step hit.

This was a destructive packaging defect and therefore a valid reason to delay
this later candidate. It does not affect the already packaged eight-rule
candidate scheduled for the next live probe.

## Coverage effect

The new rule extends Prize-route arbitration and harmful-KO handling by
checking the public successor response before taking a one-Prize KO. It also
adds a narrow one-turn threat envelope, but only for the audited Kadabra and
Duraludon successor registry.

Still incomplete:

1. general one-to-two-turn unfinished-threat reachability;
2. broader Bench future-value arbitration;
3. generic persistent known-access consumers beyond Boss;
4. card-count/effect-only probabilistic access;
5. explicit comeback mode and risk-budgeted winning-out selection;
6. a shared turn-plan layer spanning multiple rules.

The live sequence remains eight-rule, then ninth, then tenth, then eleventh,
with an authenticated refresh before every write and at least about three
hours of observation between replacements unless a destructive defect appears.
