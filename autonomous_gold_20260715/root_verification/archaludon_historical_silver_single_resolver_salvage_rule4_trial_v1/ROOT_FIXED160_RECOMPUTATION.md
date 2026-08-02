# Rule 4 fixed160 root再計算

## Inputs

- Rule 1親: `153D8461FB66927DB9731CBE614B71FF5398B8EAE8980AE0BB4D46ADD0E8792A`
- Rule 4候補: `F6B6266D870D3F134544A91616C27673620557D149C0496CC2034E7674F010D9`
- spec: `3649FFDDEF35ADCE6A50EBC8F1BE581E9E4780426D4FF8AA5271F8A2912A9D7A`
- runner: `05363E4AC9062E1AAC46283D4E4F8992F2AE4C70D1EA6859840411FF5A5279D7`
- raw tree digest: `82CE2B713417F754D13BCF8B2EC9C682AA0EFEC930EBB14FA19D0D4BA68782E1`

## Schedule and mechanical validity

- 160 unique `(opponent, seat, seed)` keys。
- Historical-Silver mirror 40、Arch Peak 40、Alakazam 40、Marnie 40。
- 各相手20 seed・両席で、親と候補のscheduleは完全一致。
- action error、exception、start fault、max-step、duplicate mismatchは0。
- duplicate control 160/160一致。

## Root counts

- Rule 1親: `100/160`
- Rule 4候補: `100/160`
- gains / regressions / ties: `0 / 0 / 160`
- 全8 seat/opponent cellで勝数差0。
- candidate-parent action traceは160/160 byte-identical。

固定160内の自然開始・完結・失敗は`0/0/0`。shadowでは2件の自然開始があり、いずれも一意な親Lillie PLAYからの`BENCH_EVOLUTION_BEFORE_LILLIE`だった。したがってcombined natural startsは2で、dormant条件には該当しない。

## Gate result

- faults 0。
- 明確な有害first difference 0。
- gains >= regressionsは`0 >= 0`でPASS。
- 席・相手別3勝悪化なし。
- combined natural starts > 0。

root再計算は段階採用条件を**PASS**と判定する。これはSilverを壊していない安全中立の採用であり、勝率強化の証明ではない。
