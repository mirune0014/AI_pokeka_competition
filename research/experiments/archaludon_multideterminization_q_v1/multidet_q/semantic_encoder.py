"""Semantic, embedding-based state and candidate encoders."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping, Sequence

import torch
from torch import nn


def _get(value: Any, name: str, default: Any = None) -> Any:
    if isinstance(value, Mapping):
        return value.get(name, default)
    return getattr(value, name, default)


def _number(value: Any, default: float = 0.0) -> float:
    if value is None:
        return float(default)
    raw = getattr(value, "value", value)
    try:
        return float(raw)
    except (TypeError, ValueError):
        return float(default)


@dataclass(frozen=True)
class SemanticVocab:
    max_card_id: int
    max_attack_id: int

    @property
    def card_size(self) -> int:
        return self.max_card_id + 2

    @property
    def attack_size(self) -> int:
        return self.max_attack_id + 2

    def to_dict(self) -> dict[str, int]:
        return asdict(self)


def build_vocab(api_module: Any) -> SemanticVocab:
    cards = list(api_module.all_card_data())
    attacks = list(api_module.all_attack())
    max_card = max((int(_number(_get(card, "cardId"))) for card in cards), default=0)
    max_attack = max((int(_number(_get(attack, "attackId"))) for attack in attacks), default=0)
    return SemanticVocab(max_card_id=max_card, max_attack_id=max_attack)


ZONE_IDS = {
    "stadium": 0,
    "self_hand": 1,
    "self_active": 2,
    "self_bench": 3,
    "self_discard": 4,
    "self_energy": 5,
    "self_tool": 6,
    "self_pre_evolution": 7,
    "opponent_active": 8,
    "opponent_bench": 9,
    "opponent_discard": 10,
    "opponent_energy": 11,
    "opponent_tool": 12,
    "opponent_pre_evolution": 13,
    "looking_visible": 14,
}
ROLE_IDS = {"standalone": 0, "pokemon": 1, "energy": 2, "tool": 3, "pre_evolution": 4}


class SemanticEncoder(nn.Module):
    """Encode one public state and one complete candidate without serials."""

    def __init__(self, vocab: SemanticVocab) -> None:
        super().__init__()
        self.vocab = vocab
        self.card_embedding = nn.Embedding(vocab.card_size, 32)
        self.attack_embedding = nn.Embedding(vocab.attack_size, 16)
        self.option_type_embedding = nn.Embedding(64, 8)
        self.context_embedding = nn.Embedding(64, 8)
        self.area_embedding = nn.Embedding(16, 8)
        self.owner_embedding = nn.Embedding(4, 4)
        self.zone_embedding = nn.Embedding(16, 8)
        self.role_embedding = nn.Embedding(8, 8)
        self.position_embedding = nn.Embedding(8, 8)
        self.global_mlp = nn.Sequential(nn.Linear(34, 128), nn.ReLU(), nn.Linear(128, 128), nn.ReLU())
        self.token_mlp = nn.Sequential(nn.Linear(32 + 8 + 4 + 8 + 6, 64), nn.ReLU(), nn.Linear(64, 64), nn.ReLU())
        self.state_mlp = nn.Sequential(nn.Linear(128 + 64 * 6, 256), nn.ReLU(), nn.Linear(256, 256), nn.ReLU())
        self.option_mlp = nn.Sequential(nn.Linear(8 + 8 + 32 + 32 + 16 + 8 + 4 + 8 + 8, 128), nn.ReLU(), nn.Linear(128, 128), nn.ReLU())
        self.candidate_mlp = nn.Sequential(nn.Linear(128 * 3 + 2, 256), nn.ReLU(), nn.Linear(256, 128), nn.ReLU())

    def _card_index(self, value: Any) -> int:
        card_id = int(_number(value, -1))
        if card_id < 0 or card_id > self.vocab.max_card_id:
            raise ValueError(f"card id outside frozen vocabulary: {card_id}")
        return card_id + 1

    def _attack_index(self, value: Any) -> int:
        attack_id = int(_number(value, -1))
        if attack_id < 0 or attack_id > self.vocab.max_attack_id:
            raise ValueError(f"attack id outside frozen vocabulary: {attack_id}")
        return attack_id + 1

    def _global_features(self, public_state: Mapping[str, Any]) -> torch.Tensor:
        select = public_state.get("select") or {}
        values: list[float] = [
            _number(public_state.get("turn")) / 30.0,
            _number(public_state.get("turn_action_count")) / 50.0,
        ]
        first = public_state.get("first_player_relative")
        values.extend(float(first == item) for item in (-1, 0, 1))
        values.extend(float(bool(public_state.get(name, False))) for name in ("supporter_played", "stadium_played", "energy_attached", "retreated"))
        players = list(public_state.get("players") or [])
        for index in range(2):
            player = players[index] if index < len(players) else {}
            values.extend(
                [
                    _number(player.get("deck_count")) / 60.0,
                    _number(player.get("hand_count")) / 20.0,
                    _number(player.get("prize_count")) / 6.0,
                    len(player.get("bench") or ()) / 5.0,
                ]
            )
            status = player.get("status") or {}
            values.extend(float(bool(status.get(name, False))) for name in ("poisoned", "burned", "asleep", "paralyzed", "confused"))
        values.extend(
            [
                _number(select.get("type")) / 16.0,
                _number(select.get("context")) / 64.0,
                _number(select.get("min_count")) / 6.0,
                _number(select.get("max_count")) / 6.0,
                _number(select.get("remain_damage_counter")) / 30.0,
                _number(select.get("remain_energy_cost")) / 10.0,
                _number(select.get("option_count")) / 25.0,
            ]
        )
        if len(values) != 34:
            raise AssertionError(f"global feature width drift: {len(values)}")
        return torch.tensor(values, dtype=torch.float32)

    def _token(self, card_id: Any, zone: str, owner: int, role: str, *, hp: float = 0.0, max_hp: float = 0.0, damage: float = 0.0, appeared: float = 0.0, energy_count: float = 0.0, tool_count: float = 0.0) -> list[Any]:
        return [self._card_index(card_id), ZONE_IDS[zone], int(owner), ROLE_IDS[role], [hp / 400.0, max_hp / 400.0, damage / 400.0, appeared, energy_count / 10.0, tool_count / 4.0]]

    def _tokens(self, public_state: Mapping[str, Any]) -> list[list[Any]]:
        result: list[list[Any]] = []
        for card in public_state.get("stadium") or ():
            result.append(self._token(card.get("id"), "stadium", 2, "standalone"))
        players = list(public_state.get("players") or [])
        for player_index, player in enumerate(players[:2]):
            prefix = "self" if player_index == 0 else "opponent"
            hand = player.get("hand") if player_index == 0 else ()
            for card in hand or ():
                result.append(self._token(card.get("id"), f"{prefix}_hand", player_index, "standalone"))
            for position, pokemon in enumerate(player.get("active") or ()):
                if pokemon is None:
                    continue
                zone = f"{prefix}_active"
                result.extend(self._pokemon_token(pokemon, zone, player_index))
            for pokemon in player.get("bench") or ():
                result.extend(self._pokemon_token(pokemon, f"{prefix}_bench", player_index))
            for card in player.get("discard") or ():
                result.append(self._token(card.get("id"), f"{prefix}_discard", player_index, "standalone"))
        for card in public_state.get("looking_visible") or ():
            result.append(self._token(card.get("id"), "looking_visible", 2, "standalone"))
        return result

    def _pokemon_token(self, pokemon: Mapping[str, Any], zone: str, owner: int) -> list[list[Any]]:
        tokens: list[list[Any]] = [
            self._token(
                pokemon.get("id"),
                zone,
                owner,
                "pokemon",
                hp=_number(pokemon.get("hp")),
                max_hp=_number(pokemon.get("max_hp")),
                damage=max(0.0, _number(pokemon.get("max_hp")) - _number(pokemon.get("hp"))),
                appeared=float(bool(pokemon.get("appeared_this_turn", False))),
                energy_count=len(pokemon.get("energy_cards") or ()),
                tool_count=len(pokemon.get("tools") or ()),
            )
        ]
        for card in pokemon.get("energy_cards") or ():
            tokens.append(self._token(card.get("id"), f"{('self' if owner == 0 else 'opponent')}_energy", owner, "energy"))
        for card in pokemon.get("tools") or ():
            tokens.append(self._token(card.get("id"), f"{('self' if owner == 0 else 'opponent')}_tool", owner, "tool"))
        for card in pokemon.get("pre_evolution") or ():
            tokens.append(self._token(card.get("id"), f"{('self' if owner == 0 else 'opponent')}_pre_evolution", owner, "pre_evolution"))
        return tokens

    def encode_state(self, public_state: Mapping[str, Any]) -> torch.Tensor:
        global_hidden = self.global_mlp(self._global_features(public_state))
        tokens = self._tokens(public_state)
        if tokens:
            card_ids = torch.tensor([item[0] for item in tokens], dtype=torch.long)
            zone_ids = torch.tensor([item[1] for item in tokens], dtype=torch.long)
            owner_ids = torch.tensor([item[2] for item in tokens], dtype=torch.long)
            role_ids = torch.tensor([item[3] for item in tokens], dtype=torch.long)
            numeric = torch.tensor([item[4] for item in tokens], dtype=torch.float32)
            hidden = self.token_mlp(torch.cat((self.card_embedding(card_ids), self.zone_embedding(zone_ids), self.owner_embedding(owner_ids), self.role_embedding(role_ids), numeric), dim=-1))
            pools = []
            for owner in (0, 1, 2):
                selected = hidden[owner_ids == owner]
                if selected.shape[0] == 0:
                    pools.extend((torch.zeros(64), torch.zeros(64)))
                else:
                    pools.extend((selected.mean(dim=0), selected.max(dim=0).values))
            pooled = torch.cat(pools)
        else:
            pooled = torch.zeros(64 * 6)
        return self.state_mlp(torch.cat((global_hidden, pooled)))

    def _option_parts(self, option: Mapping[str, Any], context: int, position: int) -> tuple[list[int], list[float]]:
        payload = option.get("semantic_payload") or option.get("payload") or {}
        fields = payload.get("fields") if isinstance(payload, Mapping) else {}
        fields = fields if isinstance(fields, Mapping) else {}
        execution = option.get("execution_payload") or {}
        execution_fields = execution.get("fields") if isinstance(execution, Mapping) else {}
        execution_fields = execution_fields if isinstance(execution_fields, Mapping) else {}
        def value(name: str, default: Any = None) -> Any:
            return option.get(name, fields.get(name, execution_fields.get(name, default)))
        option_type = int(_number(payload.get("option_type", option.get("option_type", 0))))
        area = int(_number(value("area", 0)))
        player = int(_number(value("playerIndex", 0)))
        index = int(_number(value("index", 0)))
        in_play_index = int(_number(value("inPlayIndex", 0)))
        tool_index = int(_number(value("toolIndex", 0)))
        energy_index = int(_number(value("energyIndex", 0)))
        number = int(_number(value("number", 0)))
        count = int(_number(value("count", 0)))
        in_play_area = int(_number(value("inPlayArea", 0)))
        source_card = value("source_card_id", execution.get("source_card_id") if isinstance(execution, Mapping) else None)
        target_card = value("target_card_id", execution.get("target_card_id") if isinstance(execution, Mapping) else None)
        attack_id = value("attack_id", value("attackId", None))
        categorical = [
            min(max(option_type, 0), 63),
            min(max(int(context), 0), 63),
            self._card_index(source_card) if source_card is not None else 0,
            self._card_index(target_card) if target_card is not None else 0,
            self._attack_index(attack_id) if attack_id is not None else 0,
            min(max(area, 0), 15),
            min(max(player, 0), 3),
            min(max(in_play_area, 0), 15),
        ]
        numeric = [index / 20.0, in_play_index / 6.0, tool_index / 4.0, energy_index / 10.0, number / 20.0, count / 20.0, float(player), position / 6.0]
        return categorical, numeric

    def encode_candidate(self, candidate: Mapping[str, Any], *, context: int = 0) -> torch.Tensor:
        options = list(candidate.get("selected_options") or ())
        if options:
            categorical: list[list[int]] = []
            numeric: list[list[float]] = []
            for position, option in enumerate(options):
                cat, num = self._option_parts(option, context, position)
                categorical.append(cat)
                numeric.append(num)
            tensors = []
            for cat, num in zip(categorical, numeric):
                tensors.append(
                    self.option_mlp(
                        torch.cat(
                            (
                                self.option_type_embedding(torch.tensor(cat[0])),
                                self.context_embedding(torch.tensor(cat[1])),
                                self.card_embedding(torch.tensor(cat[2])),
                                self.card_embedding(torch.tensor(cat[3])),
                                self.attack_embedding(torch.tensor(cat[4])),
                                self.area_embedding(torch.tensor(cat[5])),
                                self.owner_embedding(torch.tensor(cat[6])),
                                self.area_embedding(torch.tensor(cat[7])),
                                torch.tensor(num, dtype=torch.float32),
                            )
                        )
                    )
                )
            stacked = torch.stack(tensors)
            pooled = torch.cat((stacked.sum(dim=0), stacked.mean(dim=0), stacked.max(dim=0).values, torch.tensor([len(options) / 6.0, float(bool(candidate.get("order_sensitive", False)))])))
        else:
            pooled = torch.zeros(128 * 3 + 2)
        return self.candidate_mlp(pooled)

    def forward(self, public_state: Mapping[str, Any], candidate: Mapping[str, Any], *, context: int = 0) -> tuple[torch.Tensor, torch.Tensor]:
        return self.encode_state(public_state), self.encode_candidate(candidate, context=context)


__all__ = ["ROLE_IDS", "ZONE_IDS", "SemanticEncoder", "SemanticVocab", "build_vocab"]
