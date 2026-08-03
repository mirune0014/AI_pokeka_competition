# Rule 5 実装・shadow root確認

## Frozen identity

- 受理Rule 4親: `F6B6266D870D3F134544A91616C27673620557D149C0496CC2034E7674F010D9`
- Rule 5 trial: `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`
- Historical-Silver: `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- deck: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- strategy: `C7417858C932B156AF115DFCB6A11878CF239E4FA7CD4FC7BBDC43631A15B2FF`
- implementation report: `E0EFBA9E523B8EB45B5F1DB4982FF4D52D5F029AFA38326232A4922A580436D9`

## Root verification

- Rule 1とRule 4を維持し、Rule 5だけを追加。Rule 2/3なし。
- final agent 1、resolver 1、parent call 1 callbackにつき1回、共有owner最大1、proposal 6項目。
- root focused再実行28/28 PASS。
- compile/import、合法60枚、ACE SPEC 1、cache 0。
- 両席smokeは110/155 step、action error 0、max-step 0。
- 非main候補ファイルはRule 4親とbyte-identical。

## Frozen shadow

- 77 readable replay、4,262 callback、invalid/exception 0。
- first difference 2件、どちらも`DIRECT_EXACT_CURRENT_WIN`。
- Boss transaction自然開始0。

### episode 89273754 / seat 1 / step 73

- 親はBasic Metalの手張り。
- 候補はArchaludon exのMetal Defender。
- 公開damage 440、相手Activeは350 HPの2-Prize ex、こちら残りPrize 2。
- 一意な即時勝利attackであり、準備より勝利を優先する意図どおり。

### episode 89280169 / seat 1 / step 161

- 親はBench進化。
- 候補はArchaludon exのMetal Defender。
- 公開damage 220、相手Active残HP 110の1-Prize、こちら残りPrize 1。
- 一意な即時勝利attackであり、進化より勝利を優先する意図どおり。

両差分とも登録attack、公開HP、Prize値、Weakness/Resistance/Stadium証明を満たし、明確な悪手ではない。

## Root decision

実装・shadow gate PASS。凍結fixed160だけを実行してよい。Boss routeはfocusedで完結を確認済みだが、自然発火0なら条件を広げない。
