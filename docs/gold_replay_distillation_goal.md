# Gold Replay Distillation：研究開発方針と完了条件

## 現行方針（2026-07-14、以下の旧研究案より優先）

現在の改善経路は、ユーザー指示により**純粋な決定論的ルールベース**へ戻す。
この文書の後半に残る replay distillation、residual RL、behavior cloning、
learned ranker、Gold 行動模倣、相手方策 proxy 再構築は過去の研究案であり、
ユーザーが改めて明示的に許可するまで実装・候補昇格・提出に用いない。

現行サイクルは、過去に最も成果が出た Archaludon の改善方法を正本とする。

1. 金圏実績のある正確な60枚と、現在のtrackで最も強い既存ルールをbaselineにする。
2. デッキ本来のセオリーを、setup、盤面形成、主力と控え、Energy・手札・山札、
   攻撃継続、賞品交換、妨害、詰めまで一体として整理する。
3. Gold/live replayは、セオリー確認、有力行動の発見、自提出の敗因診断に使う。
   上位行動そのものを教師ラベルとして模倣しない。
4. 完全実行可能な過去の銀圏 Archaludon を主アンカーとし、他の実績済み完全
   エージェントをanti-regression populationとして使う。
5. 一度に一つの解釈可能なルール仮説だけを隔離実装し、同一seed・両seatで
   baseline/candidateを比較する。
6. 平均勝率だけでなく、変更局面、絶対強度、盤面、資源、攻撃、賞品経路、
   繰り返し対面、隣接対面をrootがraw evidenceから確認する。
7. 負け筋だけ、勝ち筋だけ、replay一致率だけを最適化しない。デッキが毎試合
   やりたい基本動作を強くしつつ、戦術的な失敗も同じ評価系で直す。
8. 実務的な改善と安全性が確認できた候補だけをpackage・submitし、live replayを
   次のルール改善へ戻す。

Goalの完了条件は、実際に提出したエージェントがライブ金圏へ到達したことの
確認である。銅・銀・1000点・ローカル改善は中間成果であり、完了ではない。

---

## 0. 最終目的

Kaggle「Pokemon TCG AI Battle」において、現在のArchaludon系エージェントを改善し、実際のライブ評価で金メダル圏に到達できる提出候補を作る。

ただし、このGoalで直接保証すべき成果は「金圏到達」そのものではない。ライブ評価は試合数、対戦相手、提出回数に制約され、ローカルだけでは完了判定できないためである。

このGoalの直接目的は、次の仮説を、再現可能な実装とblind評価によって検証することである。

> 金圏エージェントの公開対戦履歴を、正解行動として無条件に模倣するのではなく、
> 1. 上位帯の局面分布、
> 2. 有力な候補行動、
> 3. 上位帯に近い相手方策モデル
> として利用し、acting-player information setに基づくbelief rolloutで反実仮想評価したうえで、現在のルール方策より良い行動だけを可変合法手rankerへ蒸留すれば、現在のルール方策を安定して改善できる。

この仮説について、成功を示すか、規定したアブレーションを実施したうえで棄却根拠を示すところまでをGoalの完了条件とする。

---

## 1. 現在の前提

現在のエージェントはArchaludonを中心とした強いルールベース方策を土台としている。

追加済みの主な要素は次のとおり。

- ルール上位3手に限定した線形sparse residual RL
- 補正上限0.12
- matchup条件付き特徴
- terminal勝敗および賞品差を用いたREINFORCE/CEM
- 狭いmatchup固有ルール
- 相手デッキ候補と残存枚数を扱うbelief-state
- 複数determinizationによる終局rollout
- 同一seedでのbaseline A、baseline B、candidateの対照評価

現在の主な弱点は次の対面にある。

- Alakazam
- Archaludon mirror
- 一部Mega Lucario

過去に試した方法では、次の問題が確認されている。

- 線形residualは学習seedと外部seedの差が大きい
- ルール上位3手外を選択できない
- exact-hidden教師は真の山札順や賞品配置へ過適合する
- replay教師を公開情報方策へ直接蒸留すると不安定
- 狭い手動ルールは改善幅が小さく、隣接分布へ悪影響を出しやすい
- ローカル相手がKaggle上位帯の方策分布を十分再現していない可能性がある

既存のルール方策は破棄しない。新しい手法においても、以下の役割で保持する。

- baseline
- 候補生成器
- 方策prior
- 不確実状態でのfallback
- safety guard

---

## 2. このGoalの基本方針

### 2.1 金圏履歴は「絶対的な教師」ではなく「専門家による提案」として扱う

金圏エージェントが選択した行動は、有力な候補ではあるが、局面ごとの最善手とは限らない。

したがって、以下は禁止する。

- 金圏の勝利ゲームだけを正例として学習する
- 対戦の最終勝敗を、全行動の品質ラベルとして直接利用する
- 金圏エージェントの選択を常にrule top-1より優先する
- 異なるデッキの行動をArchaludon方策へ直接混ぜる
- 真のhidden orderを入力したモデルを提出方策として使用する
- raw option indexをそのまま行動ラベルとして学習する
- 複数の金圏方策を区別せず、単一のbehavior cloningモデルへ平均化する

金圏履歴の主用途は次の3つとする。

1. 現在のrule top-kに含まれない有力候補行動の発見
2. Kaggle上位帯に近い相手方策populationの学習
3. ローカルself-playでは出にくい上位帯局面の収集

同じArchaludon系かつ近いデッキ構成の履歴に限り、自分の方策priorとしての直接蒸留も許可する。

### 2.2 方策改善は候補集合上のランキングとして実装する

最終的な候補集合は、原則として以下の和集合とする。

```text
C(h) =
    rule方策の上位候補
    ∪ 金圏方策head群の上位候補
    ∪ 行動種別ごとの意味的に多様な候補
    ∪ 必要に応じたrule下位からの探索候補

単純な方策確率の線形混合は行わない。

π = α π_rule + (1 - α) π_gold

という形ではなく、ruleとgoldを候補生成器として使い、別のpaired advantage rankerが最終選択する。

2.3 教師はacting-player information set上で作る

ここでいうpublic-beliefは、厳密には「行動主体がその時点で知っている情報集合」を意味する。

モデルおよびrollout方策が利用可能な情報は次のとおり。

公開盤面
公開されたカード
公開行動履歴
自分自身の手札
自分が知っている山札上部、下部、サーチ結果等
自分の既知情報から計算されるbelief
合法手一覧

利用禁止情報は次のとおり。

相手の真の手札
真の賞品配置
未公開の真の山札順
未来のログ
未来のドロー
エンジン内部のRNG状態
raw object ID
raw serial値の大小
最終勝敗を示す未来情報

各replayを学習データへ変換するときは、必ず行動主体の視点へ変換する。

相手方策モデルを学習するとき、相手プレイヤー自身の手札をその相手方策モデルへ入力することは許可する。それは、そのプレイヤー自身が知っていた情報だからである。

2.4 exact-hidden情報は診断専用とする

replayから復元可能な真のhidden状態は、以下の診断には利用してよい。

belief samplerの整合性検証
value of perfect informationの測定
exact-hidden最善手とbelief最善手の乖離分析
hidden-order sensitivityの測定

ただし、提出方策の学習入力、行動ラベル、通常のvalue targetとして直接使用してはならない。

exact-hidden由来データは通常の学習データと別ファイル、別loaderに分離し、training loaderが読み込めないようカラムwhitelistを設定する。

3. 作業開始時に行うこと

大規模な変更を始める前に、現在のリポジトリを調査する。

最低限、次を確認して記録する。

現在のpackage構造
agent entry point
ルールスコア計算箇所
合法手の表現
完全行動と単一optionの区別
replay loader
公開観測の構築方法
belief sampler
rollout runner
RNGおよびseed管理
baseline A/B/candidate評価
matchup集計
既存テスト
既存の学習・評価スクリプト
Kaggle提出物の依存関係と推論制約

次のファイルを作成または更新する。

docs/gold_replay_progress.md

このファイルには、以下を継続的に記録する。

現在の仮説
実施した変更
使用したデータ
実行コマンド
seed manifest
結果
失敗原因
次に行うアブレーション
採用または棄却判断
未解決のblocker

既存の構造が利用可能なら再利用し、同じ役割のmoduleを重複作成しない。

4. Phase 1：Gold replayの取得・復元・正規化
4.1 データ取得方針

利用するのは、公式に公開され、競技規約上利用可能なreplayまたはdatasetだけとする。

禁止事項：

認証やrate limitの回避
非公開endpointの探索
他参加者の非公開提出物取得
credentialsのコード埋め込み
取得制限を無視した並列アクセス

取得機構を実装する場合は、以下を必須とする。

local cache
retry backoff
rate limit
checksum
rawデータの不変保存
取得日時とsource metadata
submission IDまたはagent ID
replay ID
対戦日時
デッキarchetype
席
対面
結果

既にローカルにreplayがある場合は、それを優先して使用する。

4.2 replayからdecision recordを構築する

1行動を1レコードとして、最低限以下を保存する。

episode_id
submission_id
agent_or_style_id
decision_index
turn
seat
own_deck_archetype
opponent_deck_archetype
acting_player_observation
acting_player_private_information
public_history
legal_options
canonical_complete_actions
chosen_action
rule_scores
rule_ranks
terminal_result
timestamp
source_metadata

terminal_result は診断・value学習候補として保存してよいが、chosen actionの正解weightとして直接使用しない。

4.3 行動を意味表現へ正規化する

raw option indexではなく、次の意味情報からcanonical actionを作る。

action type
使用カード
効果またはattack ID
対象player
対象zone
対象Pokémon
対象カード集合
数量
selection context
effect source
remaining cost
完全transaction内の選択列

複数選択、カードサーチ、energy選択などは、可能な限りoption単体ではなく、意思決定として完結した完全行動へまとめる。

同じ意味の行動が、option順、serial、内部indexの違いだけで別ラベルにならないようにする。

4.4 視点変換と漏洩テスト

以下のunit testまたはproperty testを作る。

player A視点とplayer B視点が正しく入れ替わる
opponent hidden handが方策入力に混入しない
true prizeが混入しない
true deck orderが混入しない
future logを削除しても現在入力が変化しない
raw serialを置換しても意味入力が不当に変化しない
未公開山札順を変更しても、既知順序制約以外のroot policy inputが変化しない
canonical actionから合法なenvironment actionへ戻せる
同じ公開状態のcanonical state IDがprocessをまたいで一致する

Python組み込みのhash()を永続IDや再現seedには使わない。安定hashを使用する。

4.5 データ分割

randomなdecision単位分割は禁止する。

最低限、次の単位をgroup化して分割する。

episode
submission version
agent/style family
日付または期間
seed
deck variant

推奨split：

train:
  モデル学習と教師生成

development:
  閾値、特徴、モデル構造、particle数の選択

blind:
  設計確定後に一度だけ主要評価

policy-family holdout:
  同じarchetypeだが別実装・別submission family

blind manifestはチューニング前に固定し、hashとともに保存する。

5. Phase 2：Gold Replay Disagreement Audit

ニューラルモデルを本格実装する前に、金圏履歴が候補生成として本当に有効かを測る。

5.1 収集対象

最初のpilotでは、目安として512状態を使用する。

優先配分：

Alakazam
Archaludon mirror
Mega Lucario
中立対面
強対面のanti-regression用状態
両席
勝利と敗北の両方
複数の金圏submissionまたはstyle
ruleとgoldの行動が異なる状態
一部は一様抽出し、disagreementだけへの選択biasを防ぐ

データが不足する場合は、得られた全件を使い、不足を明記する。件数不足を無視して強い結論を出さない。

5.2 測定項目

各gold decisionについて、次を測る。

gold actionのrule rank
gold actionがrule top-3外である割合
gold actionがrule top-10外である割合
gold actionが現在の候補生成器で生成不能な割合
gold actionとrule actionのsemantic difference
対面別、席別、turn帯別、action type別のdisagreement
agent/style別の差
同じ公開状態に対するgold方策間agreement
勝利gameと敗北gameでの差

最重要指標は、gold actionの模倣精度ではない。

次のoracle差を測る。

rule候補のみを探索した場合のoracle価値
vs
rule候補 + gold候補を探索した場合のoracle価値

gold候補を追加してもoracleが改善しなければ、直接蒸留へ進まない。

6. Phase 3：information-set beliefによる反実仮想教師
6.1 候補行動

各状態で、最低限以下を比較する。

baseline rule action
rule top-6
gold action
gold方策head群のtop action
action typeごとの代表
rule下位から意味的に多様な候補1～2個

候補数が大きい場合は、最初に少数particleでscreeningし、有望候補へ追加particleを割り当てる。

6.2 belief sampling

acting playerの情報集合に整合するhidden worldをサンプルする。

満たすべき制約：

公開カードの枚数整合
自分の既知手札
公開捨て札
公開盤面
deck hypothesis
既知のsearch結果
既知のtop/bottom操作
公開行動履歴から分かる制約
prize、hand、deckの枚数整合
候補外デッキを表すunknown mass

相手デッキをhardなtop-1 IDへ固定しない。

以下を保持する。

deck posterior
posterior entropy
top-1 mass
unknown mass
カード別zone期待枚数
分散
手札に1枚以上存在する確率
次の数draw以内に引く確率
6.3 paired rollout

全候補を同じouter particle群で比較する。

各outer particleでは以下を共通化する。

root hidden world
opponent policy style
continuation policy family
比較可能な将来chance

可能であれば、乱数をイベント意味単位でkey付けしたsemantic random tapeを用いる。

単に同じ整数seedを渡しただけでcandidateとbaselineが完全にpairedであると仮定しない。

各rollout中、方策には各プレイヤーが実際に観測可能な情報だけを渡す。engine内部が完全状態を持つことは許可するが、continuation policyが完全状態を参照してはならない。

6.4 相手方策population

単一のローカルルールエージェントだけで教師を作らない。

以下を可能な範囲で含める。

現在のルール相手
historical snapshot
金圏replayから学習したbootstrap imitation model
style別head
softmax temperature変種
tie-break変種
資源温存、速度重視、gust重視等の小さな方策変種
完全holdoutする同一archetype別実装

異なるデッキのgold履歴は、自分の直接教師ではなく、主にこの相手方策populationへ利用する。

6.5 教師ラベル

baseline actionをa0として、各候補について次を推定する。

Q(h, a)
Δ(h, a) = Q(h, a) - Q(h, a0)

主utilityはterminal win/lossとする。

賞品差は主rewardとして加えない。利用する場合は診断または補助headに限定し、terminal勝率との整合を確認する。

保存する集約値：

mean_win_probability
advantage_vs_baseline
cluster_standard_error
one_sided_lcb90
probability_advantage_positive
opponent_group_advantages
batch_A_rank
batch_B_rank
value_of_perfect_information
is_stable_label

outer particle、episode、seed blockを独立標本として扱い、同一particle内の複数branchを独立標本として数えない。

6.6 teacher stability

最低限、独立したparticle batch A/Bを作る。

高margin状態について、以下を測る。

top-1一致率
advantage符号一致率
rank correlation
opponent policy group間の符号反転率
particle数16、32、64での収束
hidden-order resampling感度

不安定な状態をhard label化しない。

7. Phase 4：Gold priorと可変合法手ranker

teacherが安定し、gold候補の追加にoracle改善が確認できた場合だけ実装する。

7.1 モデル構造

提出環境で軽量に動作する小型モデルとする。

初期候補：

state/entity encoder:
  2層程度の小型TransformerまたはSet Transformer

history encoder:
  GRUまたは小型Transformer

belief encoder:
  deck posterior token
  重要カードtoken
  集約belief embedding

action encoder:
  canonical complete actionをDeepSetsまたは小型Transformerでencode

interaction:
  action queryとstate/entityのcross-attention

output:
  各合法完全行動のscalar score
  advantage prediction
  uncertainty estimate

目安：

hidden dimension 128
1～3M parameters
ensemble 3個
提出時にネットワーク不要
依存ライブラリ最小化
CPU推論時間を測定
7.2 gold方策prior

gold replayからbehavior priorを学習する場合、次の区別を保持する。

submission/style
deck archetype
deck variant
matchup
time period

複数方策を無条件に1つへ平均しない。

以下のいずれかを使う。

style embedding
mixture-of-experts
agent/style別head
bootstrap ensemble

同じArchaludon系のgold履歴だけを、自分の直接priorとして強く使用する。

異なるデッキの履歴は、shared representation pretrainingまたは相手モデルへ使用する。

7.3 学習目的

中心lossはpairwise rankingまたはadvantage regressionとする。

L =
    L_pairwise_rank
    + λ1 L_advantage_regression
    + λ2 L_filtered_behavior_cloning
    + λ3 L_value
    + λ4 L_invariance

filtered_behavior_cloningへ含めるgold actionは、belief teacherで少なくとも非劣化と判断されたものを優先する。

勝利replayだからという理由だけでweightを上げない。

7.4 最終選択

ruleとlearned modelを単純平均しない。

候補score例：

score =
    normalized_rule_prior
    + predicted_paired_advantage
    + optional_gold_prior

ただし、最終的には安全ゲートを通す。

初期ゲート条件：

predicted advantageのone-sided lower boundが正
ensembleの2/3以上が同方向
OOD判定が閾値以内
belief entropyが許容範囲
主要matchup groupで大きな負差がない
hard safety ruleに反しない

条件を満たさない場合はbaseline rule actionへ戻す。

7.5 DAgger

最初の蒸留後、最大3 roundまで選択的DAggerを行う。

収集対象：

ruleとlearned policyのdisagreement
ensemble disagreement
OOD状態
gold priorとrankerの不一致
弱対面の重要状態
override直前・直後の状態

各roundで新しい状態をbelief teacherに問い合わせ、datasetへ追加する。

一度のDAgger失敗だけで方式を打ち切らない。

8. Phase 5：評価
8.1 比較対象

最低限、以下を比較する。

A: 現在のbaseline control
B: baseline controlの再実行
C: rule + gold候補のsearch oracle
D: 蒸留ranker
E: 蒸留ranker + safety gate

baseline A/Bが一致しない評価blockは無効とする。

8.2 評価軸
全体勝率差
弱対面合計
各matchup
両席
action type
turn帯
seed窓
external seed
policy-family holdout
deck variant holdout
gold submission time holdout
action error
max-step
推論時間p50/p95/p99
override率
override時勝率差
fallback率
OOD率

単純な総勝利数だけでなく、seed・相手・席block単位のdiscordant pairを保存する。

統計には以下を使用する。

paired bootstrap
seed block bootstrap
opponent groupでstratifyしたbootstrap
exact McNemar test
point estimate
one-sided 90% lower confidence bound
8.3 blind評価

development結果を見てarchitecture、閾値、粒子数を確定した後にblind評価を1回行う。

blind結果を見た後に閾値だけ調整して同じblindを再評価しない。

blindで失敗した場合、そのsetは以後development扱いとし、新しいblind manifestを作る。

9. 成功条件
9.1 teacher成功条件

以下を満たすこと。

高margin状態における独立batch間のadvantage符号一致率が80%以上
高margin状態のtop-1一致率が70%以上
particle数増加により順位が収束する
hidden-order置換による不当なラベル反転がない
action inputへのhidden leakage testが全件成功
gold候補を追加したsearch oracleが、rule候補のみのoracleよりblind評価で1.5勝率ポイント以上改善する
改善が単一submissionまたは単一相手方策だけに依存しない
gold由来の有効候補の一部がrule top-3外に存在する
9.2 蒸留成功条件

以下を目安とする。

search oracle改善量の50%以上を実ゲームで回収する
blind external seedでbaseline比1.5勝率ポイント以上改善
one-sided 90% lower confidence boundが0以上
弱対面合計で明確な改善
強対面の最大悪化が1.5ポイント以内
policy-family holdoutで非劣化
action error増加なし
max-step悪化なし
提出環境相当で推論時間上限内
hidden情報を除去した入力だけで再現可能
同じ設定とseed manifestから結果を再生成可能

統計的に十分なsample数がない場合、閾値を都合よく緩和して成功扱いにしない。信頼区間と不足件数を報告する。

10. 同じ仮説内で実施するアブレーション

一度の失敗でPPO、CQL、NFSP、Deep CFRなど別方式へ移らない。

以下を順に確認する。

10.1 データ・復元
player perspective変換
action canonicalization
complete transaction復元
serialおよびoption order依存
future information leakage
train/dev/blind leakage
submission versionの混入
勝利replayへの選択bias
10.2 teacher
particle数16、32、64
opponent policy単体とpopulation
continuation policy単体とensemble
sequential RNGとsemantic random tape
terminal-only reward
unknown deck mass有無
exact-hidden diagnosticとのVPI分析
candidate数6、12、16
rule top-kのみとgold候補追加
同一デッキgoldと異種デッキgoldの分離
10.3 モデル
stateのみ
state + history
state + belief
state + history + belief
単純concat
state-action cross-attention
option単体表現
complete transaction表現
hard classification
pairwise ranking
absolute Q regression
baseline差分advantage
gold styleを統合
style別head
ensembleなし
ensemble + safety gate
10.4 DAgger

最大3 roundまで行い、各roundについて次を測る。

disagreement状態数
新規状態coverage
teacher安定率
oracle回収率
override精度
holdout改善

同じ状態を繰り返し追加して見かけ上datasetだけを増やさない。

11. 打ち切り条件
11.1 gold候補仮説の棄却

以下を実施しても、gold候補追加によるoracle改善の90%上側信頼限界が1勝率ポイント未満なら、金圏履歴の自分方策への直接利用を打ち切る。

正しいplayer-view復元
complete action canonicalization
particle数64
独立teacher batch
opponent policy population
continuation policy ensemble
hidden leakage除去
同一デッキgoldの分離
candidate coverage確認

この場合も、gold replay利用全体は打ち切らない。

用途を以下へ限定する。

相手方策モデル
上位帯局面dataset
meta分布推定
評価set
デッキarchetype推定
11.2 teacher仮説の棄却

上記アブレーション後も、高margin状態の符号一致率が60%未満なら、belief rolloutを主要なaction teacherとして打ち切る。

その場合は、不安定性の原因を以下へ分解した報告を作る。

hidden-order variance
opponent-policy variance
continuation-policy variance
candidate action variance
belief misspecification
engine RNG divergence
11.3 ranker蒸留の打ち切り

teacherとsearch oracleが安定しているにもかかわらず、以下を行った後もoracle改善量の25%未満しか回収できない場合、汎用ranker蒸留を打ち切る。

history encoder
belief input
complete transaction action
cross-attention
pairwise advantage
ensemble
safety gate
最大3 roundのDAgger

その場合は、searchが安定する限定状態clusterだけのselective overrideまたはtable化へ切り替える。

11.4 デッキ探索へ進む条件

以下の両方が成立した場合、現在のArchaludonデッキ固定を終了する。

十分なsearch oracleを用いても方策改善余地が1勝率ポイント未満
弱対面の敗因が、行動差ではなく展開速度、必要カード密度、賞品レース構造に集中している

デッキと方策を最初から同時最適化しない。

まず方策を固定してデッキを比較し、その後デッキを固定して方策を再学習するcoordinate descentを用いる。

12. このGoalでは原則実装しないもの

次は、このGoalの初期手法として実装しない。

PPO
CQL
NFSP
Deep CFR
大規模なend-to-end self-play
exact-hidden MCTSの直接蒸留
金圏行動の無条件behavior cloning
rule方策を完全に置き換える巨大モデル
Kaggle提出環境での大規模online search

これらが必要と判断された場合も、先に現在の仮説の棄却証拠を示す。

13. 実装品質
13.1 再現性

全実験で以下を保存する。

git commit SHA
engine version
agent version
dataset manifest
split manifest
seed manifest
config
Python version
dependency version
実行コマンド
raw結果
集計結果
13.2 テスト

最低限、以下を自動テスト化する。

replay parsing
player perspective
action canonicalization
action round trip
belief consistency
hidden leakage
stable state ID
deterministic control
label aggregation
cluster bootstrap
model input invariance
fallback動作
illegal action防止
serialization
submission environment import
13.3 計算資源

ローカル環境はWindowsおよびWSLを前提とする。

game simulationはCPU並列を優先
neural network学習とbatch inferenceはRTX 4070またはKaggle GPUを使用
workerごとに独立engine instanceを持つ
メモリ使用量とprocess数を設定化
中間結果をshard保存し、再開可能にする
同一rolloutの再計算を避けるcacheを持つ
GPUがない環境でも小規模テストを実行可能にする
13.4 変更方針
既存baselineを直接破壊しない
feature flagまたは別agent classで追加する
大きな変更は小さい検証可能なcommitへ分ける
既存評価を通してから次へ進む
無関係なrefactorを同時に行わない
magic numberを避け、configへ置く
実験途中の一時コードを提出経路へ混ぜない
14. Kaggle提出ループ

この節をKaggle提出ルールの正本とし、従来の実戦フィードバック重視の提出ループを採用する。提出ごとにユーザーの個別確認を要求する後発ルールは採用しない。既存のKaggle credentialsを使用し、1日5回の提出枠を必要に応じて利用してよい。Kaggleへの外部書き込みと最終的な提出判断はroot agentだけが行う。

現在の提出と、その1つ前の提出が十分な試合数を消化しても1000未満である場合は、ローカルで根拠を持つ次候補を提出し、ライブでの挙動と対戦履歴を収集する。700前後以下で明らかに弱い場合は、execution errorと主要な敗因を確認した後、通常より早く置換してよい。

ただし、回復中の提出を有効な候補なしに置換しない。仮説、ローカル対照評価、期待する改善bucketを記録せずに提出枠を消費しない。提出後はvalidationとexecution errorを直ちに確認し、その後の公開replayを取得して次の改善へ反映する。leaderboard scoreだけを見た閾値調整や、公開範囲外のデータ取得は行わない。

ローカル昇格条件を満たした場合は、提出可能なartifactと次の報告を準備する。

候補agent
依存関係
重み
config
推論時間
ローカル評価
matchup別評価
blind評価
既知のrisk
baselineとの差分
推奨するライブ観測条件
rollback方法

提出後も、scoreだけでなくmatchup別結果、意思決定差分、replay上の敗因を保存し、候補の採用またはrollbackを判断する。

15. 進行中の判断方針

作業中に軽微な曖昧さがあっても、合理的な前提を置いて先へ進む。置いた前提はprogress logへ記録する。

ただし、以下の場合はblockerとして明示する。

必須データが存在しない
credentialsが利用不能または無効
競技規約上の可否が不明
engineの再現性が壊れている
replayからplayer-viewを復元できない
評価に必要なbaselineが実行不能
必要な操作が既存データを破壊する
Kaggle APIまたはcompetition側の障害で提出・replay取得が不能

単なる設計上の選択では作業を停止しない。小さなpilot、アブレーション、既存コードの証拠を使って決定する。

各phaseの終了時に、progress logへ次を追記する。

What was tested
What evidence was obtained
What failed
What remains uncertain
Decision
Next experiment
16. Goal完了条件

このGoalは、次のいずれかを満たした場合に完了とする。

完了条件A：仮説を支持
replayからplayer-view decision datasetを再現可能に構築
hidden leakage testに合格
Gold Replay Disagreement Auditを完了
rule + gold候補でsearch oracle改善を確認
belief teacherの再現性を確認
可変合法手rankerを実装
safety gateを実装
最大3 round以内のDAggerを実施
blind評価で規定した昇格条件を満たす
提出可能artifactと評価報告を作成
完了条件B：仮説を棄却
規定したデータ、teacher、候補集合、モデル、DAggerのアブレーションを実施
仮説が失敗した原因を定量分解
単一の実装bugや漏洩が原因ではないことを確認
打ち切り条件を満たす
次に進むべき方針を、証拠とともに1つに絞って提案
再利用可能なreplay dataset、相手モデル、評価基盤を残す

単にコードが動いた、学習lossが下がった、特定seedで勝った、公開leaderboardが一時的に上がった、という理由だけでは完了扱いにしない。

最終報告には、最低限以下を含める。

1. 実装したもの
2. 変更ファイル
3. データ件数と分割
4. 漏洩検査結果
5. disagreement audit
6. teacher stability
7. oracle gap
8. ranker性能
9. 実ゲーム評価
10. matchup別結果
11. ablation結果
12. runtime
13. 既知の失敗
14. 成功または棄却判断
15. 次に行うべき1つの方針
16. 再実行コマンド
