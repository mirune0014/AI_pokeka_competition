# Root verification: Public Attack-Readiness Metal Allocation v1

## Decision

`RARE_NARROW_FAIL`。この候補は focused fixture では正しく動くが、固定した実戦 corpus では一度も発火しない。実エンジン、fixed760、package、Kaggle へ進めない。

## Frozen identities

- Formal parent `main.py`: `558EE5DB29E001428B0D59813613FABEE8E15B96E422746C104BDFAB4DC22DB6`
- Candidate `main.py`: `BD7A2E83CC5102C0D04226093EC628FC95AFD40DA2F0EF506FBBDD2E11DCB094`
- Parent/candidate `deck.csv`: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`
- Frozen strategy: `62CA78FF7A59113F6516F882BC2FC636815C0002503D7F240149EDC8EFE87790`

Root は候補が exact parent byte prefix を持ち、suffix 内の parent call site が一つ、runtime が12ファイル、非 `main.py` 11ファイルが親と同一、deck が60枚かつ ACE SPEC 1枚、loader の最後かつ唯一の対象 callable が `agent`、cache が0であることを再実行して確認した。

## Focused verification

Root 再実行:

```powershell
py -3.11 -B autonomous_gold_20260715/implementation/archaludon_public_attack_readiness_metal_allocation_v1/validate_candidate.py
py -3.11 -B autonomous_gold_20260715/implementation/archaludon_public_attack_readiness_metal_allocation_v1/focused_fixtures.py
```

両コマンドは exit 0。focused は24行、両席、positive/reorder/lifecycle 10、parent release 14、fault 0だった。これは条件分岐の局所的な妥当性だけを示し、自然発火を示さない。

## Root recomputation of the shadow gate

固定 corpus は207 replay、正しい対象席209。親が選んだ clear-MAIN Basic Metal 通常手貼りは744件あった。Root が `shadow_inventory.csv` を再集計した落下理由は次のとおり。

| 理由 | 件数 |
|---|---:|
| baseline current attack unknown/incomparable | 405 |
| boundary/owner | 157 |
| plan readiness/hierarchy unknown | 94 |
| parent target improves readiness | 82 |
| inherited owner live | 6 |
| 合計 | 744 |

したがって、局面自体が稀なのではない。通常手貼りは十分に多いが、候補の比較証明が全744件を親へ返した。

Shadow minimum に対する結果:

- strict-eligible starts: `0`（必要 `>=20`、両席）
- actual first differences: `0`（必要 `>=12`）
- unique replay: `0`（必要 `>=8`）
- seats: `[]`（必要 `[0,1]`）
- invalid action / semantic fault / parent-call fault: すべて `0`
- natural controls: episode 88443760 は3 attachment/0 difference、88681773 は6/0

Static shadow は候補の反実仮想 attach 後を進まないため、postcondition failure は未観測であり `null` が正しい。focused fixture の両席 lifecycle は完遂したが、自然差分の証拠には数えない。

## Interpretation

この候補を安全だから残す、または条件を後付けで緩めて fixed 評価へ進めることはしない。特に405件の baseline attack 比較不能と94件の plan 比較不能は、一般的な手貼り判断を所有するには oracle 境界が狭すぎることを示す。

候補 source は失敗記録として凍結する。formal parent は引き続き `558EE5...22DB6` とする。次の候補は、固定戦略が事前指定した Night Stretcher の exact recovery-to-attack transaction を、同じ formal parent から一つの独立仮説として選定する。
