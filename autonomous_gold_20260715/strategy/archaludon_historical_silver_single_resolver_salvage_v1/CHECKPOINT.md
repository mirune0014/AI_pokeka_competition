# CHECKPOINT

Updated: 2026-08-03 JST

## Invariants

- Silver scorer unchanged.
- One final agent; one resolver; one active transaction.
- One rule at a time.
- UNKNOWN returns Silver.
- Failed rules are removed, not patched by stacking another rule.
- Existing artifacts remain read-only.

## Accepted parent

- Rules 1, 4, and 5 accepted: `archaludon_historical_silver_single_resolver_salvage_rule5_trial_v1`.
- `main.py`: `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`
- Stored exact Historical-Silver parent: `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- `deck.csv`: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`

## Completed rules

- Rule 1 `EXACTLY_ONE_DURALUDON_SETUP_V1`: accepted as a safe neutral rule.
  - shadow: 9/9 first differences on the intended setup boundary;
  - fixed160: Silver 100, candidate 100, G/R/T 0/0/160;
  - natural starts: 28, seat 0 = 11, seat 1 = 17;
  - execution faults: 0.
- Rule 4 `PARENT_LILLIE_EXACT_CURRENT_MATERIALIZATION_V1`: accepted as a safe neutral rule.
  - focused 22/22、shadow 4,262 callback、自然発火2、許可差分2、fault 0。
  - fixed160: 親100、候補100、G/R/T 0/0/160、trace 160/160一致。
  - 2差分はいずれも親Lillie前のattack-ready bench evolution。
- Rule 5 `PARENT_EXACT_ATTACK_WIN_OR_UNIQUE_HIGHER_PRIZE_BOSS_TRANSACTION_V1`: accepted as a safe neutral rule.
  - focused/inherited 28/28、shadow 4,262 callback、自然差分2、fault 0。
  - fixed160: 親100、候補100、G/R/T 0/0/160、全8 cell不変。
  - 2差分はいずれも公開情報で証明された即時終局攻撃。
  - Boss経路の自然発火は0。条件を広げず、強度寄与は主張しない。

## Failed or deferred rules

- Rule 2 `EXACT_LONE_ACTIVE_REPLY_KO_CONTINUITY_V1`: `DEFER-DORMANT`。
  - focused 9/9、両席smoke、実行fault 0。
  - shadow 4,262 callbackで差分0。
  - fixed160は親100、候補100、G/R/T 0/0/160、trace差分0。
  - 合計自然発火0のため統合しない。条件を広げない。
- Rule 3 `SILVER_DECLARED_ULTRA_BALL_TWO_ROUTE_TRANSACTION_V1`: `REJECT`。
  - focused 80/80、両席smoke、実行fault 0。
  - fixed160は親100、候補99、G/R/T 0/1/159。
  - action-observable start 3、完結transaction 0。
  - Arch Peak・seat 0・seed 271958318でmechanism-first loss 1件。
  - 補修・条件拡張は行わず、Rule 1親へ戻す。

## Current step

Implement Rule 6, the complete Poke Pad route, as the only new behavior change
from the accepted Rule 5 parent. Rules 2 and 3 are not part of that parent.

## Next step after acceptance

Rule 7, Turbo Flare energy concentration, from the last accepted Silver-based
parent.
