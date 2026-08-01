# Phase 1 Iteration 008 結果

## 結論

Iteration 008 は `PASS_AS_NARROW_READ_ONLY_AUDIT` とする。

ただし、合格したのは830判断点に対する識別可能性監査の再現性であり、Iteration 007 の対戦性能でも、RL全体の有効性でもない。

今回の結果から棄却するのは、Iteration 007 のcheckpointと、「固定された表現・targetに通常の共有勾配をそのまま追加すれば、重要な正負6群を分離できる」という限定仮説だけである。

Iteration 004 の開始checkpoint、latest-v1のルール方策、clean-room RLの開発経路は維持する。

対戦は0件、学習更新は0回である。

したがって、「小さな学習で勝率が改善しなかったためRLを棄却した」という判断ではない。

## 固定入力と出力

- 監査計画: `8FAE5B736C4C1E269AC5FCD1EA1D0146EBC35B78BDA6A454AF452D6920D7E701`
- 実行仕様: `55B2F8D928F787C9B99821D556448D5F4761CAE1D46DC3E6861AE7D5ABF9F479`
- Iteration 004 checkpoint: `24D8A4EACD9D7B699D327D3F2436F4DA21AC79433038E6FA96F9AE0E50F8FB04`
- 監査対象のIteration 007 checkpoint: `5547AFD90CF039390CDA8E70E3DA5868C12B0277AA670636573F7BC0FE7715B3`
- dataset: `3D714FC248B597ADD412B1D9B4BAD60DDF6BDEB3DFA652264D763D7A843AC41B`
- manifest core: `0FB981A19C01B068E77210E06E074A94064641DFA8BA758D741CECE82449DF4C`
- manifest file: `537FF791D51A562A8DC2280461E973F4E849539DB069E3E3D1EAFA770D2A5526`
- 出力ディレクトリ: `analysis_outputs/archaludon_latest_v1_rl_phase1_iteration_007_identifiability_audit_20260801`

固定仕様どおり1回だけ実行し、exit code 0、830行、32軌跡、10出力ファイルを得た。

ゲームとoptimizer stepはいずれも0である。

## 独立再集計

rootと独立したSol Ultra数値監査が、生の830行から次の項目を再計算した。

- 行数、軌跡数、順序、重複control
- GAE、Monte Carlo return、固定value target、float32正規化
- exact collision、時間履歴、value/credit、near-neighbor
- 行・状態・軌跡単位の重み直し、ESS、上位4軌跡のweight share
- Stage 1とStage 32のclipped-PPO勾配、78個の群間cosine、実parameter deltaへの射影
- 5種類のcause gate

公開値との数値不一致は0件だった。

830個のordinalは正確に `0..829` で、`(episode_id, decision_index)` も830件すべて一意だった。

## 構造原因の監査

| 原因候補 | 再計算結果 | 判定 |
|---|---:|---:|
| 表現衝突 | `0 / 211.4662315683` | false |
| 直前履歴の不足 | baseline mass `0`、covered `0行 / 0群` | false |
| value / credit競合 | numerator `0`、denominator `0` | false |
| 単純なdataset偏り | passing group `0 / 6` | false |
| 単なるoptimizer不足 | favorable derivative `2 / 6`、update16 parameterなし | false / 判定対象外 |

`classified_causes` は空だった。

ただし、これは「5原因が存在しない」という強い証拠ではない。

opaqueな観測hash `O` が830行すべてで一意だったため、時間履歴とvalue/creditのbaseline分母が0になった。

near-neighborの符号一致も `2 / 2` にすぎない。

この標本だけでは、時間情報やcredit assignmentが十分だとは証明できない。

## 勾配競合の直接証拠

Stage 1とStage 32の全830行でPPO clippingは0件だった。

Stage 1からStage 32への `residual_head.0` parameter deltaは18,528要素、norm `0.3170803715` である。

更新は停止しておらず、単に変化量が小さすぎたわけでもない。

| 重要群 | deltaとのdot product | cosine | 方向 |
|---|---:|---:|---:|
| PLAY positive | `-1.3954060e-6` | `-0.0788715` | 逆 |
| ATTACH negative | `+1.5954217e-7` | `+0.0178035` | 順 |
| EVOLVE negative | `+3.3198895e-8` | `+0.0048030` | 順 |
| RETREAT positive | `-1.3533826e-6` | `-0.2747334` | 逆 |
| ATTACK negative | `-1.7914247e-6` | `-0.4245734` | 逆 |
| END positive | `-3.2895653e-7` | `-0.2255057` | 逆 |

重要6群のうち4群で、各群が望む勾配と実際の累積更新が逆向きだった。

また、6群すべてのStage 32 probability-space medianが逆方向であり、状態単位・軌跡単位に重みを均しても符号は反転しなかった。

したがって、同じ共有勾配を無条件に長く回すことは、学習量を増やすというより逆向き更新を増幅する可能性がある。

## GAE正規化の注意点

raw GAEとMonte Carlo advantageのrobust signは `830 / 830` で一致した。

一方、全体平均を引く正規化後はraw/MCと `611 / 830` だけが一致し、219行でrobust signが反転した。

次の実験では、正規化後の指標だけで合格させず、raw GAE、Monte Carlo、符号が安定した611行も安全条件に含める。

## 証跡上の制限

`audit_implementation_snapshot` の説明はpath順sortと記載しているが、保存されたaggregate SHA `80DDCDFC...` は実装定数順である。

本当にpath順で計算したSHAは `4EB80BD0EEC37053E06E764076B0D08FF377AC9835E6E85646168B20B3BAD7D3` になる。

個別のaudit script SHA `8BCC5819...` とtest SHA `90F4D2DC...`、および数値監査結果は一致している。

この不一致は数値結果を変えないが、次のmanifestでは実際の順序規約を明記して固定する。

## 次に検証する仮説

次は「共有interaction layer内のfamily/polarity勾配競合が直近のblockerであり、元のデータ量を変えずにmass-preserving PCGradを適用すると6重要群を同時に順方向へ動かせる」という仮説だけを検証する。

Iteration 004からbyte-identicalに開始する2-arm offline実験とする。

- control: 通常のfull-batch共有勾配を64更新
- treatment: 6重要群とremaining rowsの7 taskに分割し、各taskの元の `1 / 830` massを保ったdeterministic PCGradを64更新
- 両armともStage 1のreadout更新は同一の1回
- Stage 2では `residual_head.0.{weight,bias}` だけを更新
- dataset、target、architecture、feature、optimizer、row orderは変更しない
- 対戦とruntime smokeは行わない

64更新は各armで53,120 row-exposuresに相当する。

controlを同時に64更新するため、「PCGradが効いた」のか「通常勾配を前回より長く回しただけで直った」のかを分離できる。

offline合格には、更新48と64の両方で6重要群すべてが順方向であること、12 family/polarity群、global指標、raw/MC指標、END control、KL/TV、安全・再現性条件をすべて満たすことを要求する。

この実験が失敗しても、棄却するのはmass-preserving PCGradが直近の修正として十分だという仮説だけである。

RL全体やlatest-v1の対戦性能は棄却しない。
