# Root verification: Rule 10

## Frozen identity

- Requirements SHA-256: `24282FA6A0EF91D936E2E5B2AAD725904EF3223FCFBDF9BEEA16C62C726038C9`.
- Strategy SHA-256: `77C272880882B9C02473C00C88AEFD1F3447D696DF341990E5D62B0D14AD88B4`.
- Accepted Rule 5 parent `main.py`: `D966E455E5110F9D5616195AEAAC8663E6A92F310DAFC4B7F79E4D37149A9C62`.
- Rule 10 candidate `main.py`: `2C9249F74CA37429DECEA4801E736E13085E50C19956BB0C75176B9D6759245A`.
- Deck SHA-256: `08421AE98D080A1EE3BA28F93DA0A99C79287A2BC6F57529FDA2E4CA56CC7C6A`.

## Source and structure

Root inspected the parent/candidate diff. Only candidate `main.py` differs:
807 insertions and four replacements. Added surfaces are the Rule 10 constant
and activity telemetry, bounded public reply oracle, Rule 10 six-field
proposal, shared-owner FML lifecycle, resolver registration, and telemetry
emission. Rules 2, 3, 6, 7, 8, and 9 are absent.

The twelve package files other than `main.py` are byte-identical to Rule 5.
The extra two files visible in the parent comparison were generated parent
`__pycache__` files and are not package inputs. The Rule 10 candidate tree has
zero cache paths.

Root reran the verifier and independently confirmed:

- seven Python files compile in memory and candidate import succeeds;
- one top-level/final `agent`, one `_resolve`, one top-level owner assignment,
  and one static parent call inside `agent`;
- Kaggle last-callable loader resolves `agent`;
- legal 60-card deck and exactly one ACE SPEC;
- 13 package files, with all 12 non-main files preserved;
- Historical-Silver scorer and chooser remain in the byte-identical imported
  parent; they are not redefined in candidate `main.py`.

Verifier output SHA-256:
`1B2032439A3ED843B95FED144E1DB093522051E9BB765883C1712AF810B211CC`.

## Focused and inherited behavior

Root reran the complete test discovery with `py -3.11 -B`:

- 35/35 passed.
- Seven Rule 10 methods cover both seats, all four admitted Rule 5 attacks,
  KO-to-survival, exact board-out removal, non-KO reply, damage order,
  FML-to-same-attack lifecycle, retries, permutation, physical-copy binding,
  receipt-before-retry clearing, precedence, ambiguity, and post-spend abort.
- All 28 inherited Rule 1/4/5 methods pass.

The candidate deliberately fails closed when any opposing Metal Pokemon or
unsupported reply surface is visible. It neither owns nor changes parent
Lillie, Boss, terminal attack, END, hidden-hand, search, or comeback behavior.

## Engine and shadow evidence

Worker both-seat smoke completed in 149 and 158 steps, with zero action errors
and zero max-step hits. `smoke_summary.json` SHA-256:
`886217DB7E56CA5A90F358F6BD093A34098CBE49E180AE79AD389010BF365587`.

Root independently reran the full replay shadow:

- source paths: 46 current plus 207 historical;
- readable replays: 252; the known truncated episode 89287701 is the sole
  malformed input;
- both seats, 30,977 callbacks;
- action differences, first differences, invalid actions, and exceptions: 0;
- Rule 10 starts, completions, aborts, and faults: 0/0/0/0;
- ordered corpus SHA-256:
  `A29B61F31A84401404BF1701DDC5CF959A330EA6894C9283C533017B99ED4C9D`.

`shadow_summary.json` SHA-256:
`10CFB7339BB130D51267F96A8351CB3A8E0718E578887DDBFBA6A25BE50DEA46`.
The empty differences and activity-event files each hash to
`4F53CDA18C2BAA0C0354BB5F9A3ECBE5ED12AB4D8E11BA873C2F11161202B945`.

## Gate before fixed160

Implementation, deterministic lifecycle, inherited behavior, structure,
smoke, and shadow safety gates pass. Natural replay activity is zero, so the
candidate is currently dormant. The frozen plan still requires the exact
fixed160 schedule; the rule must not be integrated or widened unless that
schedule proves at least one complete non-fixture FML-to-same-attack
transaction and all numerical/qualitative gates pass.

