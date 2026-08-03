# 最終判定

Date: 2026-08-03 JST

## Verdict

**ACCEPT**。

本候補を、要件定義上の「Historical-Silverを壊していない単一resolver再基盤化
エージェント」として受理する。定量的な強化版とは呼ばない。

## Frozen inputs

- Requirements SHA-256:
  `24282FA6A0EF91D936E2E5B2AAD725904EF3223FCFBDF9BEEA16C62C726038C9`
- Historical-Silver `main.py` SHA-256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- Candidate `main.py` SHA-256:
  `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`
- Shared deck SHA-256:
  `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Fixed760 specification SHA-256:
  `49B89DDAEDF6745A7ADD203602DA457BDDE912B2B7F4F18FAA3C2955780BC75D`
- Raw tree SHA-256:
  `F3B7393D88DFC4026404AC5D8AC32AD629739A2C0960E642C5634859E7853168`

## Numerical decision

- Historical-Silver `478/760`、candidate `480/760`。
- Paired gains / regressions / ties: `4 / 2 / 754`。
- Silver mirror: `100 -> 100`。
- Adjacent population: `378 -> 380`。
- Seat 0: `243 -> 245`、seat 1: `235 -> 235`。
- 最悪の相手別差分はArch Shumpeiの`-1`。
- fault、action error、exception、max-step、duplicate mismatchはすべて0。
- 基礎保持条件はPASS。
- 強化条件は`480 < 486`のためFAIL。

独立Sol-Ultra数値監査とroot再計算は、760キー、各勝数、G/R/T、席・相手別集計、
fault、duplicate、信頼区間について一致した。

## Qualitative decision

145件のfirst differenceはRule 1が128件、Rule 4が14件、Rule 5が3件で、
未分類は0件だった。勝敗discordant 6件の内訳は次のとおり。

- Rule 4: 2 gains / 0 regressions。Lillie前の進化からCoated Attackの防御へ
  つながる明確な改善。
- Rule 5: discordantなし。3件とも確定勝利を早めたwin-to-win差分。
- Rule 1: 2 gains / 2 regressions。

Arch Shumpeiの1 regressionでは、Rule 1後のSilver Ultra Ball検索が
Archaludon exから重複Duraludonへ変わる実在の相互作用を確認した。ただし、Rule 1の
初期配置そのものは公開情報上妥当であり、同じ初期手札形状が別キーではgainを生み、
勝敗因果も中信頼に留まる。このため「明確な有害機構」には該当せず、定性棄却条件は
発動しない。拒否済みRule 3を本候補へ補修追加しない。

## Required wording and limitation

> Accepted only as the requirements-defined non-destructive Historical-Silver
> rebaseline. It is not demonstrated stronger: the fixed760 strengthened gate
> failed (`480/760 < 486/760`), the mirror was unchanged, and the paired `+2`
> is practically and statistically inconclusive.

physical CSVにはliteralな`panel`列がなく、immutableなpanel別directory名から
partitionを復元した。これはartifact schema上の注意点であり、行動上の欠陥ではない。

本v1の完成に追加検証は不要。将来「強化」と主張する場合は別versionの仮説として、
`486/760`以上、両席非悪化、全安全条件、全discordantの再監査を要求する。
