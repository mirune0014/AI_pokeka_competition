# Root-verified evidence for the next Alakazam rule after 54853109

Frozen by root: 2026-07-20 22:23 JST.

## Parent and live-candidate disposition

The only permitted implementation parent is
`candidates/alakazam_guarded_teleportation_attack_continuity_v1`:

- source SHA-256:
  `4A95DCE0BB095A05F58085DFC450528C5939527E30B9D40E43A76B0CFCE2AE16`;
- runtime SHA-256:
  `9CA7A415451B84343165EF8A5CDC0D67BBF1B4969A13C984C09B142B4898CD9A`;
- legal 60-card deck SHA-256:
  `7B413177E5077777F2178143839C0155B03B92BBC8B3A6607621A7D43F351141`.

Submitted unique-Active-Mist candidate `54853109` is not a parent. Formal
adoption was rejected before its one permitted exploratory probe. Through the
root-verified eleven-public-game checkpoint, it had 607 correct-seat
callbacks, zero invalid actions, zero action differences from guarded parent,
and zero transaction starts/targets/attacks/resolutions/aborts. It cannot
explain the live results or score. See
`live/54853109/refresh_20260720_2200/ROOT_11_GAME_CHECKPOINT.md`.

## Immutable live evidence

The first nine-public-game episode CSV is SHA-256
`E8E942C93A5907E9901CE9CB9C0149951D2D67BF1F991C8FA3C898AAE65852E4`.
Root re-executed the exact target seat in all three mirror losses and the one
Mega-Lucario loss with both submitted source and guarded parent. Across 214
eligible callbacks there were zero invalid actions and zero action
differences. Thus all following choices belong to the guarded parent policy.

### Repeated Alakazam-mirror KO/resource failure

1. Episode `87076890`, observation step `173`, target seat 0:

   - Active old Alakazam `743/#13`, Basic Psychic attached, 40 HP;
   - opponent Active Kadabra `742/#69`, 50 HP, exactly one Prize;
   - own/opponent remaining Prizes `2/6`, deck `1`, hand `13`;
   - unique legal Powerful Hand option `4`, exact damage `260`, already lethal;
   - guarded parent instead chose Dawn option `0`, then selected the deck's
     last card Fezandipiti ex at step `174`, making deck `0`, and only then
     chose Powerful Hand at step `175`;
   - the game ended in a mandatory-draw loss while the target retained the
     large public prize lead.

2. Episode `87079669`, observation step `81`, target seat 0:

   - Active old Alakazam `743/#11`, Telepath Psychic attached, full 140 HP;
   - opponent Active Abra `741/#77`, 50 HP, exactly one Prize;
   - own/opponent remaining Prizes `4/6`, deck `11`, hand `4`;
   - unique legal Powerful Hand option `9`, exact damage `80`, already lethal;
   - the parent instead entered Psychic Draw, then spent Poké Pad, two Lucky
     Helmets, Run Away Draw, Night Stretcher, a recovered Energy attachment,
     and Boss before taking the same one Prize at step `92`;
   - the publicly visible Night Stretcher/Energy escape package was gone when
     Fezandipiti ex was gusted Active again; the target became stranded and
     later lost on deck clock with three Alakazam still visible.

Both states have a public prize lead of at least two, a unique immediately
lethal Powerful Hand against the unchanged one-Prize Active, and no need to
gust for equal prize value. The first is a high-confidence terminal cause; the
second is a medium-high-confidence resource/escape cause. A global
attack-immediately rule remains unsafe because setup can be correct in tied or
losing exchanges and against higher-value Bench targets.

### Dawn primary-line alignment failure

Episode `87080205`, observation step `75`, target seat 0:

- old Active Abra `741/#4` already had Telepath Psychic attached;
- no Kadabra was in hand, while Alakazam `743/#12` was already in hand;
- the public Dawn Stage-1 selection exposed four Kadabra and one Dudunsparce;
- guarded parent chose Dudunsparce option `4` rather than a Kadabra;
- first Kadabra evolution was delayed to turn 11 and first Alakazam/KO to turn
  13, after the opposing Alakazam had reached its last Prize.

Choosing a Kadabra would certainly advance the ready primary line, but a win
conversion remains counterfactual. This is distinct from the rejected
`alakazam_mandatory_draw_reserve_kadabra_resource_first_v1`, which guarded a
late exhausted-board draw reserve and had zero intended Hammer transaction
activations. It is also distinct from Active-Kadabra pre-attack stage-up.

### Lone-Psyduck bench-out rescue failure

Episode `87080766`, observation step `25`, target seat 0:

- lone Active Psyduck `858/#21`, 10 HP, no Bench, no Energy, six Prizes;
- deck `40`, hand `11`, no Basic reserve or search Item in hand;
- Hilda had just selected Dudunsparce plus Enriching Energy;
- legal options were four Psychic/Telepath attachments, exact Enriching
  attachment option `4`, and END option `5`;
- guarded parent chose END; Mega Lucario then KO'd the only Pokémon for the
  board-out loss.

Enriching attachment was the sole immediate draw/reserve route, but its draw
four could still whiff. This is a high-confidence policy error with only
low-to-medium confidence of changing the result. A narrow extension of the
existing Hilda -> Enriching -> reserve transaction from lone Dunsparce to lone
Psyduck has lower surface area than a generic bench-out draw rule.

## Root verification artifacts

Mirror qualitative report SHA-256:
`3E762298221D0924F0352C11E1623E09E6A93245E7B548C4437B0DD5AEF54055`.
Root mirror verifier/output SHA-256:
`564C16227759FEF2706CDC58579F5DE1657B08FD17E7C0C8A6E77DBDE8EA543B` /
`E7A6B17CA4F08534D099830635E5CC65173E89FD9D7A0DC4B7EA42396E98E8AB`.

Lucario qualitative report SHA-256:
`5AFC652992E8CA55A804D7D9BC1D6E728080A829A41BC4C01038B5CBCDBA40F8`.
Root Lucario verifier/output SHA-256:
`A2E18F74F19ACC96BDFB006EE93CA9AEECBC13203EB0042B93EC175C06448EB7` /
`5EE021EAC54B22189CA04419DBAE33ACF702FFE08ED2F1491B514AC91F1595FD`.

## Competing one-rule hypotheses

The Sol-Ultra strategy judge must select exactly one, refine it into a complete
fail-closed contract, or return `STOP_NO_CREDIBLE_RULE`.

1. **Certified prize-lead one-Prize Active KO lock.** At MAIN, with an old
   ready Active Alakazam, a unique current Powerful Hand option lethally KOing
   the unchanged complete one-Prize Active, public remaining-Prize lead at
   least two, and no strictly higher certified current-turn prize route,
   attack before optional draw/search/tool/recovery/Boss spending. Positive
   anchors: `87076890/173` and `87079669/81`. The judge may add a public backup
   or clock clause, but may not broaden to all KOs or stack a setup rule.
2. **Dawn energized-Abra primary-line alignment.** During Dawn's exact Stage-1
   selection, if an old energized Abra is in play, no Kadabra is in hand, a
   Kadabra is publicly selectable, and Alakazam follow-up is already in hand
   or transaction-bound, choose the deterministic Kadabra before
   Dudunsparce. Positive anchor: `87080205/75`.
3. **Certified lone-Psyduck Hilda-Enriching reserve extension.** Extend only
   the existing guarded Hilda -> Enriching -> reserve transaction to an early,
   six-Prize, empty-Bench, unenergized lone Psyduck under a complete public
   next-turn board-out threat and exact option-set guards. Positive anchor:
   `87080766/22-25`.

The judge must inspect prior rejected attack/setup/reserve candidates and state
why the selected rule is not a disguised retry. It must freeze exact positive
and negative anchors, transaction state/duplicate/rollback behavior, loader
ordering, focused fixtures, current-plus-historical live shadow, full-engine
proof, and a compact identical-seed/both-seat evaluation. Formal adoption must
preserve guarded-parent absolute strength, Historical-Silver, both seats, and
zero paired regressions. The user's practical preference may permit one
packaged exploratory probe after all safety gates even if outcome improvement
is locally unexercised; it never permits a broken or duplicate artifact.
