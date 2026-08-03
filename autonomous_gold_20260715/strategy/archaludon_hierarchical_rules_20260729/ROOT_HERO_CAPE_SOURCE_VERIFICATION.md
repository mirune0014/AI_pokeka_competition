# Root verification — Hero's Cape source

Root independently verified the recommended source state from the frozen
48-loss audit. This is strategy evidence only; no candidate, package, or
Kaggle artifact was created.

## Frozen identities

- Replay `88643491`:
  `5C385365DBCA461A5E99B633E00C011CFDCE18ADD7EB0E9DECAF6F4A2FD16DDF`
- Historical-Silver parent:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`
- Correct seat: `0`, verified from `TeamNames[0] == rurumi`
- Row: `77`
- Turn: `8`

## Root-recomputed state and action

The exact parent recomputation returns option `[5]`, attack `224` Raging
Hammer. The relevant parent scores are:

- Hero's Cape `1159#37 -> Duraludon 169#5`: `8,000`;
- Raging Hammer `224`: `25,000`, due to the parent's remote-Ogerpon
  override;
- Hammer In `223`: `30`;
- End: `0`.

The public board is:

- Active Duraludon `169#5`, `130/130`, four Basic Metal, no Tool;
- Hero's Cape `1159#37` visible in hand;
- opposing Active Mega Lucario ex `678#93`, `340/340`, with one visible
  Energy providing Fighting;
- no Stadium;
- current Raging Hammer damage `80`, a non-KO;
- printed Aura Jab `982` costs one Fighting and does `130`;
- Hero's Cape's printed effect grants `+100 HP`.

Therefore the immediate public arithmetic is exact:

- parent attack: Mega Lucario `340 -> 260`, Duraludon remains `130/130`;
- payable Aura Jab without Cape: `130 -> 0`, lethal;
- after Cape, Duraludon is `230/230`;
- the same 130 damage would leave `100 HP`.

This verifies the same-turn survival boundary and the scoring blind spot. It
does not prove the opponent chooses Aura Jab, forbid a later attachment into
Mega Brave, prevent gust, or establish an alternate match win. The mechanism
must remain a narrow soft transaction and fail closed on unknown public
damage or changed options.

## Root artifacts

- Verification script:
  `root_verify_hero_cape_source.py`
- Script SHA:
  `DEABE7B6BDE857F6CBC4BB4423B21FA3CAC7380DA817AECD7DB8DE4E6703607A`
- Raw Root output:
  `ROOT_HERO_CAPE_SOURCE.json`
- Output SHA:
  `8EA9B3B3D52EBE1C1CD9DDF1E46A145F3E89C08CF7C0A37126826792556EF7B8`
- Frozen 48-loss audit:
  `DECLINE_KO_AND_ALTERNATE_DAMAGE_AUDIT.md`
- Audit SHA:
  `18E965D0DB8BE3F7231F4F145A4083FEE7374620903EA7936CE34DF727D9B65D`
