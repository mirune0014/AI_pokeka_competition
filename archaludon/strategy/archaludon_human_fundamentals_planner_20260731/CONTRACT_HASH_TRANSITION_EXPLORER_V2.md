# Explorer v2 contract hash transition

`STRATEGY_SELECTION_EXPLORER_MARGINAL_TURN_DOMINANCE_V2.md` は作成時に
次の SHA-256 だった。

`7AD45C49361D50E25B0415BAC17D03C17F0097787D15685C1D197DFFE7CEDEC7`

別ファイルの controlling amendment への参照を一度だけ先頭へ追加し、
同じ turn 内でその参照を削除して本文を元へ戻した。
この `apply_patch` によりファイルのバイト表現が正規化され、
意味内容は同じだが現在の SHA-256 は次になった。

`4CD290798E0BE514AB0186E7A297B68EC281BC7946670CDA6601345099D3E52A`

実装 freeze では現在の SHA を使う。
作成時 SHA は、worker が最初に読んだ契約を識別する履歴値としてだけ残す。

二体目以降の ready attacker の意味内容は、別ファイル
`STRATEGY_AMENDMENT_EXPLORER_ATTACK_DEPTH_V2.md`
が上書きする。

同 amendment の SHA-256:

`381EA0A77F6B3C00A16C3BFD72C43B5B6A4779E37481BE7437D42A92AD280523`

