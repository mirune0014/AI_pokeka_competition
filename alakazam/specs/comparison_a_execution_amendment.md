# Comparison A execution amendment

## 変更しない項目

Comparison Aのengine、baseline、candidate、7 opponents、両seat、50 seeds、max steps、勝敗定義、paired keyはimmutable specificationから変更しない。

比較対象のsource hash、deck hash、seed集合も変更しない。

## 実行方法だけを分割する理由

checked runnerのmonolithic実行は、attempt 1でsequence 3、attempt 2でsequence 38の子プロセスがexit code 1となり停止した。

attempt 1の失敗report SHA-256は`9D45911D919C69EBA17B17F9CF295DEB20DAE4B67E6518D9060C405E950F724C`である。

attempt 2の失敗report SHA-256は`07993DF586C2C8C53819A215A7D36E9AB0390C76F21BB49A8DDDFE1DDC056FD3`である。

checked runnerは`capture_output=True`で子プロセスのstderrを保存しないため、両attemptにtracebackは残っていない。

失敗したMarnie seat 1の10-game commandと、direct frozen seat 0の失敗seedをrootが同じengine、agent、deck、seedで再実行すると、いずれもexit 0、action error 0、max-step hitなしで完走した。

したがって、途中の120 paired rowsを採用したり失敗を勝敗へ変換したりせず、同じ固定日程を35個の`(seed_base, opponent)` panelへ分割する。

## 分割契約

各panelはchecked `tools/run_seeded_paired_suite.py`をそのまま使う。

各panelには1 opponent、1 seed base、10 games per seat、両seat、baseline control A、baseline control B、candidateを含める。

1 panelの正規出力はpaired rows 20、manifest rows 6である。

全35 panelの正規出力はpaired rows 700、manifest rows 210である。

exit code非zero、`report.valid=false`、20行未満、duplicate mismatch、action error、max-step hitのあるattemptは失敗証拠として保存し、正規データへ含めない。

機械的retryは同じcommandを最大3回まで許可し、seed、agent、opponent、seat、games、max stepsを変更しない。

各panelで最初に`report.valid=true`となったattemptだけを正規panelとして採用する。

3回とも失敗したpanelが1つでもあればComparison A全体をBLOCKEDとし、部分勝率を報告しない。

## 結合と監査

実行担当はpanelごとのchecked runner出力だけを作り、独自aggregateを作らない。

Sol Ultra numerical evaluatorは35個の正規`paired_results.csv`を直接読み、全schedule key、重複、行数、勝敗、seat、opponent、seedを再計算する。

rootは同じ700 raw rowsを独立に再計算する。

checked `tools/audit_paired_results.py`へ渡すcombined ledgerは、raw行をheader一つで辞書順に連結するだけとし、値を変換しない。

monolithic attempt 1とattempt 2はfailure provenanceとして残し、正規panelと混在させない。
