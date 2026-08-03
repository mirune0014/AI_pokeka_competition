# Deferred loss memo — episode 88826681

Status:

`ROOT_VERIFIED_PUBLIC_PRIZE_RACE__ALTERNATE_WIN_UNPROVED__DEFER_HARMFUL_KO_SIBLING`

This loss is not Hero's Cape causal evidence. The submitted Hero candidate and
the exact historical-Silver parent were identical across all 67 correct-seat
callbacks, with zero Hero starts, action differences, invalid actions,
exceptions, or stale transactions.

- replay SHA-256:
  `ED58D8FB1B7E8D7E0C4603AB5DC86DAC569185D66C192FD5CB39E98765A46282`
- Hero shadow SHA-256:
  `E54201BC4CC92A8BE0216C6299D34DB22C9EE48B1F90BABAEC69B17E49A1237D`
- formal parent SHA-256:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`

Root verification:

- verifier:
  `root_verification/archaludon_mirror_nonterminal_boss_tempo_88826681_20260730/verify_nonterminal_boss_tempo_state.py`
- verifier SHA-256:
  `0B6CB514BAB5B16AF6027F69C88D88D2A269108EE5B4B3939CD2096D8823C3E2`
- output:
  `root_verification/archaludon_mirror_nonterminal_boss_tempo_88826681_20260730/root_verification.json`
- output SHA-256:
  `A9A55D9C1BFA855B3743258251AA7F9A06CFEF8CBF69018C8AD4B32B30454A56`

## Root-verified public transition

At row `135`, turn `13`, both players had two Prizes remaining. Full Metal
Lab was public. Both Active Pokemon were full-HP `300` HP Archaludon ex with
three Metal Energy.

The parent chose Boss's Orders, score `4300`, over immediate Metal Defender,
score `220`. At the Boss target callback both available targets were one-Prize
Pokemon and received the same `23100` score:

- damaged Cinderace `666#23`, `110` HP, one Energy;
- Duraludon `169#17`, `130` HP, one Energy.

The parent selected Cinderace and took one Prize with the observed `220`
Metal Defender. It therefore moved to one Prize without damaging the
opponent's two-Prize Active.

The public alternative was to retain Boss and attack the opposing Active.
With Full Metal Lab, the visible mirror damage was `190`; our own full-HP
Active also visibly survived one return Metal Defender at `110` HP. The
realized continuation later contained the expected `190` return damage.

## Potential later hypothesis

`MIRROR_TWO_PRIZE_RACE_SUPPRESS_NONTERMINAL_BOSS_KO`

Prefer beginning the two-hit Active race and retain Boss only when:

1. exactly two Prizes remain for both players;
2. both Active Pokemon are two-Prize Archaludon ex;
3. our exact current attack starts a visible two-hit KO;
4. our Active deterministically survives every current payable return attack;
5. Boss can take only one Prize and does not remove a unique ready attacker,
   evolution bridge, damage amplifier, lock, or other certified threat;
6. retained Boss preserves a public route to re-gust the damaged Active if it
   retreats;
7. healing, protection, retreat, and disruption uncertainty are handled as
   mode/risk terms, not as hidden-card facts.

Terminal Boss KOs and certified threat-removal routes retain precedence.

## Causal limitation

The public state proves the Prize race and the legal attack-first alternative,
but it does not prove the alternate wins. Healing, Hero's Cape, Judge,
retreat, promotion, and later draws can change after the branch. The
opponent's realized hidden hand is diagnostic only and must never become a
policy input.

This is a strong example of an intentionally declined immediate KO candidate,
but it requires engine counterfactuals and recurrence before becoming a hard
rule. Do not stack it into Hero's Cape or apply it outside the narrow endgame
mirror certificate.
