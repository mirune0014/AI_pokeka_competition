# Archaludon式ルールベース改善手順

## 位置づけ

現在の各Gold deck trackは、過去にArchaludon提出がライブで1000を超え、
最大約1045まで到達したときの改善手順を使う。対象archiveは
`submission_archaludon_gtmidguard_lucariobev_crustledeckguard.tar.gz`、
Kaggle submissionは`54495224`である。

## 成功時に実際に行ったこと

1. その時点で広い対面に最も強かった既存ルールをbaselineとして保持した。
2. live replayから、勝敗ではなく再現可能な失敗機序を特定した。
3. 失敗機序を、デッキ全体の役割に沿う一つのルールテーマへ変換した。
4. 同じreplayで意図した行動変化が起きることを確認した。
5. 対象対面だけでなく、既存の主要対面を同一seedで比較した。
6. 対象改善と隣接対面の安全性が両立した候補だけを提出した。
7. 提出後は回復・停滞・新しいloss bucketをliveで確認し、次の仮説へ戻した。

この手順の中心は、強い一手を断片的に集めることではなく、デッキが毎試合
再現したい強い動きを時系列のルールとして愚直に実行することである。盤面形成、
資源投入、攻撃開始、控え準備、攻撃継続、賞品変換を一つの経路として定義し、
各合法手をその経路が成立する順序へ並べる。live lossは経路の欠落を見つける
材料であり、個別の負けだけを直す例外条件の供給源にはしない。

代表例はKangaskhan/Crustle戦のdeckout対策である。既存ルールはGreat Tuskが
見えた場合だけ山札を保存したため、Great Tuskを含まないCrustle構成に対して
Poké Pad、Pokégear、Explorer、Ultra Ballを使い続け、山札切れした。修正は
相手名や特定seedではなく、公開されたCrustleと自分の山札・盤面状態を条件に、
安定attacker完成後の不要な検索を止め、低山札ではLillieによる補充を優先する
一貫した資源ルールだった。対象対面は`46/64 -> 59/64`、主要smoke全体も
`0.7396 -> 0.7656`となり、提出後に1000を超えた。

## 同じ時期に棄却したもの

- mirrorの一つのBoss対象を変える案は、該当lossを直してもseat・mirror variantで
  不安定だった。
- Alakazamで非ex Archaludonへ進化する案は、該当局面を変えても別Alakazamや
  Starmieを悪化させた。
- mirrorの空benchを直すCinderace検索は、一部mirrorを改善しても他mirrorと
  Great Tusk/Alakazamを崩した。

したがって「その負けを変えた」は採用条件ではない。公開情報から一般化できる
機序、デッキの役割との整合、対象対面の実質的改善、隣接対面の安全性が必要である。

## 現在のCynthia trackへの適用

- baselineは、提出済みv9ではなく、同一scheduleで絶対成績がより高い純ルール
  方策v23とする。
- 主アンカーは正しいhistorical-Silver Archaludon `54495224`とする。
- setup、Gible/Gabite/Garchomp、Champion's Call、Roserade、Energy、最初の攻撃、
  控え準備、賞品交換、Boss target、詰めを一つの時系列として読む。
- 基本経路は、Gible主線を2本確保し、3本目のGibleより先にRoselia支援線を1本
  確保し、GabiteのChampion's CallでGarchompとRoseradeを完成させ、Energyを持つ
  後続を作ってからDraconic Busterを賞品へ変換する流れとする。カードが合法候補に
  あるのにこの役割構成を作れない複数選択は、個別matchup patchではなく基礎方策の
  欠陥として直す。
- 一度に実装するのは一つの解釈可能なルールテーマだけとする。
- v35の広いdevelopment、v43のRoserade breakpoint、v44のBuster前Attachは既に
  棄却済みであり、条件を小刻みに追加して再提出しない。
- 旧銀Archaludonへの`9/60`というfloorを、小さな平均差で隠さない。新候補は
  失敗機序を実際に変え、主アンカーで実務的な絶対改善を示す必要がある。
- 同時に他の完全実行可能な実績済み方策をanti-regressionとして使い、
  盤面、資源、攻撃継続、賞品経路を勝率と一緒に確認する。

## 現在使わない方法

ユーザーが明示的に再許可するまで、residual RL、learned ranker、behavior
cloning、Gold行動模倣、replay由来の相手方策proxy再構築は使わない。
