# FINAL_JUDGMENT

**Verdict: ACCEPT** `PARENT_EXACT_ATTACK_WIN_OR_UNIQUE_HIGHER_PRIZE_BOSS_TRANSACTION_V1` as a safe-neutral Rule 5 stage adoption onto the accepted Rule 4 parent.

これは数値強化の主張でもKaggle提出推奨でもない。規則全体の自然差分が2件あるため`DEFER-DORMANT`ではない。

## Verified facts

- Candidate: `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`
- Focused/inherited suite: 28/28 PASS。
- Shadow: 4,262 callback、invalid/exception 0、許可された`DIRECT_EXACT_CURRENT_WIN`差分2件。
- 2件はいずれも非終端の準備行動を、公開情報で証明された即時終局攻撃へ置き換えた。
- fixed160: 親=候補`100/160`、G/R/T `0/0/160`。
- 全8 seat/opponent cell不変。fault、action error、max-step、duplicate mismatchは0。

## Judgment

凍結条件は`gains >= regressions`、cell -3未満なし、明確な有害first differenceなしを要求し、同値を許している。本候補はすべて満たすため段階採用する。

Boss経路は自然発火0である。focused fixtureで合法性と両席transaction完結だけを認め、戦力寄与は計上しない。条件を広げず、自然発火時にはBoss確認、同一attack ID、対象fingerprint、実Prize取得、fault 0を記録する。

主な未解決リスクは、未観測のBoss状態遷移、公開modifier境界、Supporter消費を伴う近視眼的Prize変換である。最終採用には固定760戦と全勝敗差分監査が必要。
