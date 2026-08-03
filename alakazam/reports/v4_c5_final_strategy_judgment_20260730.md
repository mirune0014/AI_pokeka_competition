# フーディン v4 C5 最終戦略判断

日付: 2026-07-30

## 最終判断

- C5一般化壁行動: `NO-OP`
- 提出経路: C2 action path
- C1ポフィン行動: 棄却
- C3ベンチ0回避行動: 棄却し、pure analyzerのみoffline/shadow資産として保持
- C4: 開発用shadowとして保存し、提出実行経路には含めない

評価した仮説は、公開情報だけで保護対象、相手の反復攻撃、攻撃拒否時の進展、
壁解除後の安全、Prize交換をすべて`STRICT`認定できる局面だけ壁行動を変えれば、
攻撃継続を改善しながら回帰を避けられる、というものである。

現データには、この仮説を行動変更へ移すための証拠がない。

## 独立再計算

C4の固定ペア700行は、baselineとcandidateがともに452勝248敗だった。

```text
gain = 0
loss = 0
tie = 700
```

両seat、全対面、全seed blockで差分は0だった。これはC4がC2と行動同一で
あることの証明であり、強化されたことの証明ではない。

絶対強度にも弱点が残る。

- Historical Silver: 56/100
- Rocket proxy: 38/100
- Rocket proxy・seat 1: 17/50

900試合、55,514 callbackのシャドー計測では、実行・binding・action identityの
faultは0だった。一方、行動変更に必要な証拠は次のとおり不足した。

| 判定項目 | 実測 | 必要値 |
|---|---:|---:|
| valid `STRICT` | 0 | 24 |
| `STRICT` opponent bucket | 0 | 2 |
| natural parent agreement | 0 | 12 |
| trace-complete outcome | 0 | 8 |

valid `PRESERVE_CHANCE`は246件あったが、すべて一度しか現れていない。
また、raw chance 987件のうち741件は一意な保護対象がなく、収集器追補に従って
証拠から除外された。したがって、`PRESERVE_CHANCE`を行動変更へ使ってはならない。

## 危険な反例

- 相手が攻撃を拒否してBossや盤面形成を進める間に、保護対象が完成しない。
- 再充電が必要な相手に、不要な壁や1-Prize犠牲を置く。
- Run Away後の昇格先が即KOされ、攻撃継続とPrize交換を悪化させる。
- 最終Prizeを献上する。
- 公開済みgustやベンチ狙撃により、壁の後ろの唯一の系統を倒される。
- 壁のためにEnergy、進化札、検索札、draw engineを失い、後続を作れない。
- C1はRocketで6勝、Historical Silverで4勝悪化し、両seatでも5勝・4勝悪化した。
  MarnieやCynthiaでの局所改善では相殺できない。
- C3の700局完全tieは安全性の証明ではなく、行動到達0の結果である。
  productionで初めて発火する状態は未評価となる。

## 提出契約

提出版は次のC2 closureへ固定する。

```text
29084BC13CB74236ABE557B57A9E633A8F9E88FA83FF22D131C835293E987157
```

C1、C3、C5のaction gateと、C4 shadow collectorは提出実行経路へ含めない。

検証済みC2アーカイブ:

```text
submission_alakazam_newdeck_v4_c2_safe_final_20260730.tar.gz
SHA-256:
9F4DE9078E522501F99AEA97FC1D8319C3C81C93869EA1D2D5E2CEE2239B5E1A
```

## 次回C5に必要な証拠

行動実装より先に、reach-firstのシャドー証拠を追加する。

- `STRICT` unique states 24件以上
- `STRICT` opponent bucket 2つ以上
- 両seat、3相手以上、非mirror 2相手以上
- natural parent agreement 12件以上
- trace-complete outcome 8件以上
- 同一機構が非mirror 2 bucketで反復し、各bucketでcomplete agreement 2件以上
- refusal、gust／snipe、safe release、final Prize、backup continuityの重大反例0
- action、raw binding、fingerprint、closure、error、max-stepのfault 0

これらを通過しても、Run Away、再利用壁、犠牲壁、またはA/B/C作用点のうち
一つだけを独立候補として実装する。C2と同一seed・両seatで比較し、overallの
正のdelta、Historical Silverの改善、隣接対面の安全、bucket／cell floor、
意図した機構で勝敗が変わったことをすべて再確認してから採用する。

## 参照証拠

- `analysis_outputs/v4_c4_wall_shadow_fix6_formal_audit_20260730/AUDIT_REPORT.md`
- `analysis_outputs/v4_c4_wall_shadow_fix6_formal_audit_20260730/audit_results.json`
- `evaluations/v4_c4_wall_shadow_fix6_combined_attempt2/root_independent_paired_audit.json`
- `metrics/formal_v4_c4_wall_shadow_fix6_union_audit_attempt2/root_independent_metric_audit.json`
- `specs/v4_c4_wall_shadow_fix6_collector_erratum_20260730.md`

この判断は、読み取り専用のSol-Ultra戦略監査が独立再計算した内容を、rootが
証拠パスとともに保存したものである。
