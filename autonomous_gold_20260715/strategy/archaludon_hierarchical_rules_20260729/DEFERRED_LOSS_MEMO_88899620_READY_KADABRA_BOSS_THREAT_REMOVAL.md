# Deferred loss memo: ready Kadabra threat removal

Episode: `88899620`  
Replay SHA-256:
`D6C6D21FDA0DE8B083061A9FE390115F973127C13EA299F81B10F16546D6E98A`

This is a future isolated rule hypothesis. It is not mixed into the currently
submitted eight-rule candidate.

## Attribution

- target: `rurumi`, seat 1, reward -1;
- submitted eight-rule source:
  `DEE5092B6785DF7A63752C7AAE497051D08DCC62F7723CD9786225A0C5A99DE8`;
- exact historical-Silver source:
  `F4B578453C9D953BE94885144DD50E05DBA4510DF3340BE27ADE07495896046E`;
- correct-seat shadow:
  33 decisions, zero action differences.

The eight added rules did not cause this loss.

## Earliest decisive error

At replay step 43/44, turn 6:

- our Active: Duraludon `169#64`, 130 HP, initially two Metal;
- our Bench: Duraludon `169#65`, zero Energy;
- our hand: two Boss's Orders, two Metal, Night Stretcher, Jumbo Ice Cream;
- opponent Active: Abra `741#21`, 50 HP, one Telepath Psychic Energy;
- opponent Bench: the sole ready Kadabra `742#23`, 80 HP, plus two Abra and
  two Dunsparce;
- opponent hand count: 18;
- Prizes: 6-6.

Attaching the third Metal to the Active is compatible with the best line.
After attachment, the parent scored:

- Raging Hammer 80: `80`;
- Hammer In 30: `30`;
- each Boss's Orders: `-500`,
  reason `save Boss: can KO Active`.

It chose Raging Hammer and KO'd the low-value Abra. The opponent then promoted
Kadabra, evolved it to Alakazam, used Psychic Draw, attached Telepath Psychic
Energy, and used Powerful Hand for 400 damage to KO Duraludon.

## Root-verified counterfactual

The exact replay state was reconstructed in the native engine:

1. play either Boss's Orders;
2. select the sole ready Kadabra `742#23`;
3. attach the third Metal to Duraludon `169#64`;
4. use Raging Hammer for exactly 80 and KO Kadabra;
5. take one Prize.

After the opponent promoted the energized Abra, its next-turn state had:

- zero legal Alakazam evolution options;
- only Teleportation Attack for 10 as a payable attack.

Thus the alternative takes the same one Prize while deleting the unique
immediate Stage-2 launch point. Hammer In into the Active is inferior because
Abra can retreat or use Teleportation Attack while leaving Kadabra available.

## Future rule shape

When the Active and a Bench target are worth the same Prize and the current
attack KOs either, Boss the Bench target if all of the following are public:

- it is the unique already-ready Stage-1/Stage-2 launch point;
- removing it eliminates every currently in-play one-turn route to a lethal or
  attack-locking successor;
- the current Active is a lower-threat Basic pivot;
- the Boss spend does not break a stricter terminal Prize route;
- the KO attack and target remain exact after the switch.

This should outrank the generic `save Boss: can KO Active` score. It must be
implemented later as one isolated transaction with fail-closed checks for
duplicate evolution lines, alternate ready attackers, Prize value, attack
payment, switch legality, and terminal precedence.
