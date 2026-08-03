# Rule 3 fixed160 root再計算

## Frozen inputs

- 受理Rule 1親 `main.py`: `153D8461FB66927DB9731CBE614B71FF5398B8EAE8980AE0BB4D46ADD0E8792A`
- Rule 3 trial `main.py`: `3F05F353B868307E91A38FA62ED460D4BFB9A82B85400E2D98B3DBB5CE67A0FC`
- Rule 3 helper: `2015A4E589D2AE428A151AF50520C160CED7E1B1926D5599A2B35EB0CC6CEA61`
- deck: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- fixed160 spec: `BDB2B72162A2CED3BF99547E713C33E4A87670A0A3151074117F6A29E45EE95B`
- checked runner: `063784175D20984660947DCCBE632B103EE175455D537542527A5E9BA9F2AC1C`
- raw tree digest: `24885F5E21D43C2A87F717BD83E80777BF6CEAB006B2CE97EBF8760C8099E638`

## Schedule and validity

- 160個の`(panel, opponent, seat, seed)`キーは一意で、親と候補のscheduleは完全一致。
- Historical-Silver mirror 40戦、Arch Peak・Alakazam・Marnie各40戦。
- 各対戦相手は20 seed・両席。
- action error、例外、start fault、max-step、duplicate mismatchはすべて0。
- duplicate controlの意味的traceは160/160で一致。

## Independent root counts

- Rule 1親: `100/160`
- Rule 3候補: `99/160`
- paired gains / regressions / ties: `0 / 1 / 159`
- mirror: `20/40 -> 20/40`
- Alakazam: `29/40 -> 29/40`
- Arch Peak: `20/40 -> 19/40`
- Marnie: `31/40 -> 31/40`

唯一の勝敗回帰は`adjacent_population / arch_peak / seat 0 / game 5 / seed 271958318`。
親は勝利、候補は敗北した。

## First-difference audit

同じseed `271958318`・seat 0で、三つの隣接対戦相手すべてにRule 3由来のtrace差分が生じた。

- 最初の差はUltra Ballの捨て札選択。
  - 親: option position `[0, 2]`
  - 候補: option position `[2, 0]`
  - 公開手札card ID列: `[8, 1097, 8, 1185, 8]`
- 続く検索選択は親`[0]`、候補`[7]`。
- その後候補はRule 3のArchaludon ex進化・エネルギー・攻撃transactionを継続し、親と異なる手順へ入った。

最初の捨て札位置差だけなら同じMetal Energy 2枚の順序差に見えるが、その直後から検索serialと後続手順が変わるため、勝敗回帰を単なるoption順序差として無視できない。Arch Peakではこのtransaction開始を含む差分系列が親の勝利を候補の敗北へ反転した。

## Gate result

- 自然発火は存在するため`DEFER-DORMANT`ではない。
- `paired gains >= paired regressions`を`0 >= 1`で満たさない。
- 明確に無害と証明できないmechanism-first lossが1件ある。

したがって段階採用条件は**FAIL**。Rule 3を補修・拡張せず、不採用としてRule 1親へ戻すのが要件どおりの処理である。
