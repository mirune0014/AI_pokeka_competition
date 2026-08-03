# 最終fixed760 changed-result定性監査

Date: 2026-08-03 JST

## 結論

勝敗が変わった6キーをbaseline Aとcandidateの対象seat traceで全件確認した。
候補規則によるinvalid、壊れたtransaction、確定勝利の喪失、明確な単発悪手は
なかった。Rule 4の2 gainはCoated AttackのBasic防御へ直結する明確な改善。
Rule 1は2 gain / 2 regressionで、初期配置そのものはいずれも局面上妥当だが、
相手policyと後続Silver検索への影響を通じて長い分岐を生じた。

## Gain

- `kang seat0 game12 seed271958325`: Rule 4。Lillie前に3 Metal付きbench
  Duraludonを非ex Archaludonへ進化。昇格後のCoated AttackがRapid-Fire
  Comboを0 damageにし、baselineのboard-outを回避。高信頼の改善。
- `kang seat1 game20 seed271958333`: Rule 4。同じく進化をLillie前に確定し、
  Basic攻撃を0 damage化。高信頼の改善。
- `kang seat0 game26 seed271958339`: Rule 1で初期Duraludonを置き、hand sizeが
  下がってHand Trimmerを回避。Metal保持、Archaludon確保、後続Rule 4、
  Coated Attackまで到達。中〜高信頼の有益な連鎖。
- `kang seat1 game32 seed271958345`: Rule 1。20 HP DuraludonのRaging Hammer
  を維持しMega Kangaskhan exを2体KO。coin結果を含む長い分岐なので勝敗因果は
  中〜低信頼だが、初期配置は妥当。

## Regression

- `arch_shumpei seat1 game32 seed271958345`: Rule 1の初期bench後、Silverの
  Ultra Ball検索がArchaludon exではなく追加Duraludonへ変化。baselineのT4
  進化・先行KOを失い、相手Archaludon exに先行された。これは具体的な有害
  policy interactionで、結果因果は中信頼。ただし初期Duraludon配置自体は
  setup局面の公開情報上妥当であり、同じ初手shapeのkang gainもあるため、
  Rule 1を初手条件で止めるguardはgainも同時に消す。明確な単発悪手とは判定しない。
- `kang seat1 game0 seed271958313`: Rule 1でHand Trimmerを回避してMetalを
  保持し、初Turbo FlareをT12からT2へ早めた。一方で相手Mega展開も早まり、
  candidateはboard-out、baselineは相手deck-outで勝利。長期stall/tempoと
  coin分岐による入れ替わりで、一般化信頼は低い。明確な悪手ではない。

## Rule 1相互作用の扱い

`arch_shumpei` regressionは無視しない。次の独立仮説候補は、Rule 1を狭める
ことではなく、「既にDuraludonが場にあり、次ターンに実行可能な進化がある
Ultra Ball局面で、冗長な追加Duraludonより進化札を選ぶ」exact search規則で
ある。ただしこれは不採用Rule 3のsurfaceと交差するため、本要件の完成候補へ
補修として積まない。

## 全trace分類確認

rootの145件分類をraw locatorで照合した。Rule 1以外はRule 4が14件、Rule 5
direct terminalが3件で、未分類はない。Rule 5の3件はすべてwin-to-winの早い
確定攻撃だった。

したがって定性結論は、base retentionを覆す明確な破壊差分なし。ただし
Rule 1と後続Silver検索の相互作用は将来の独立改善メモとして残す、である。
