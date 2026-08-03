from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass
from typing import Any, Callable, Mapping


class DecisionError(RuntimeError):
    pass


class UnsafeOptionError(DecisionError):
    pass


class StaleDecisionError(DecisionError):
    pass


class InvalidSelectionError(DecisionError):
    pass


SELECT_TYPE_NAMES = {
    0: "main",
    1: "card",
    2: "attached_card",
    3: "card_or_attached_card",
    4: "energy",
    5: "skill",
    6: "attack",
    7: "evolve",
    8: "count",
    9: "yes_no",
    10: "special_condition",
}

OPTION_TYPE_NAMES = {
    0: "number",
    1: "yes",
    2: "no",
    3: "card",
    4: "tool_card",
    5: "energy_card",
    6: "energy",
    7: "play",
    8: "attach",
    9: "evolve",
    10: "ability",
    11: "discard",
    12: "retreat",
    13: "attack",
    14: "end",
    15: "skill",
    16: "special_condition",
}

COMPATIBLE_OPTION_TYPES = {
    0: {7, 8, 9, 10, 11, 12, 13, 14},
    1: {3},
    2: {4, 5},
    3: {3, 4, 5},
    4: {6},
    5: {15},
    6: {13},
    7: {9},
    8: {0},
    9: {1, 2},
    10: {16},
}

CONTEXT_PROMPTS = {
    0: "行動を選んでください。",
    1: "バトル場に出すたねポケモンを選んでください。",
    2: "ベンチに出すポケモンを選んでください。",
    3: "入れ替えるポケモンを選んでください。",
    8: "トラッシュするカードを選んでください。",
    21: "カードをつけるポケモンを選んでください。番号は盤面にも表示されます。",
    22: "ポケモンにつけるカードを選んでください。",
    35: "使うワザを選んでください。",
    38: "枚数を選んでください。",
    41: "先攻を選びますか？",
    42: "引き直しますか？",
    43: "効果を使いますか？",
}

OPTION_LABELS = {
    1: "はい",
    2: "いいえ",
    12: "にげる",
    14: "番を終わる",
}

SPECIAL_CONDITION_LABELS = {0: "どく", 1: "やけど", 2: "ねむり", 3: "マヒ", 4: "こんらん"}


def _strict_int(value: Any, name: str) -> int:
    if type(value) is not int:
        raise UnsafeOptionError(f"{name} must be an integer")
    return value


def _card_at(cards: Any, index: Any) -> dict[str, Any] | None:
    if type(index) is not int or not isinstance(cards, list) or not (0 <= index < len(cards)):
        return None
    card = cards[index]
    return card if isinstance(card, dict) else None


def _card_in_area(
    obs: dict[str, Any],
    *,
    area: Any,
    index: Any,
    player_index: Any,
) -> dict[str, Any] | None:
    current = obs.get("current") or {}
    select = obs.get("select") or {}
    players = current.get("players") or []
    if not (type(player_index) is int and 0 <= player_index < len(players)):
        return None
    player = players[player_index] if isinstance(players[player_index], dict) else {}
    if area == 1:
        return _card_at(select.get("deck"), index)
    if area == 2:
        return _card_at(player.get("hand"), index)
    if area == 3:
        return _card_at(player.get("discard"), index)
    if area == 4:
        return _card_at(player.get("active"), index)
    if area == 5:
        return _card_at(player.get("bench"), index)
    if area == 6:
        return _card_at(player.get("prize"), index)
    if area == 7:
        return _card_at(current.get("stadium"), index)
    if area == 12:
        return _card_at(current.get("looking"), index)
    return None


def resolve_option_card(obs: dict[str, Any], option: dict[str, Any]) -> dict[str, Any] | None:
    current = obs.get("current") or {}
    actor = current.get("yourIndex")
    option_type = option.get("type")
    area = 2 if option_type == 7 else option.get("area")
    owner = option.get("playerIndex", actor)
    pokemon_or_card = _card_in_area(obs, area=area, index=option.get("index"), player_index=owner)
    if option_type == 4 and isinstance(pokemon_or_card, dict):
        return _card_at(pokemon_or_card.get("tools"), option.get("toolIndex"))
    if option_type in {5, 6} and isinstance(pokemon_or_card, dict):
        return _card_at(pokemon_or_card.get("energyCards"), option.get("energyIndex"))
    if option_type == 15:
        card_id = option.get("cardId")
        serial = option.get("serial")
        if type(card_id) is int and type(serial) is int:
            return {"id": card_id, "serial": serial, "playerIndex": actor}
        return None
    return pokemon_or_card


def resolve_option_target(obs: dict[str, Any], option: dict[str, Any]) -> dict[str, Any] | None:
    if option.get("type") not in {8, 9}:
        return resolve_option_card(obs, option)
    actor = (obs.get("current") or {}).get("yourIndex")
    return _card_in_area(
        obs,
        area=option.get("inPlayArea"),
        index=option.get("inPlayIndex"),
        player_index=actor,
    )


def _name_for_card(card: dict[str, Any] | None, card_names: Mapping[int, str]) -> str | None:
    if not isinstance(card, dict) or type(card.get("id")) is not int:
        return None
    card_id = card["id"]
    return card_names.get(card_id) or f"カード {card_id}"


def _anonymous_card_label(option: dict[str, Any], ordinal: int) -> str:
    area = option.get("area")
    if area == 6:
        return f"サイド{ordinal + 1}"
    if area == 1:
        return f"山札のカード{ordinal + 1}"
    if area == 12:
        return f"確認中のカード{ordinal + 1}"
    return f"カード{ordinal + 1}"


def _safe_option(
    obs: dict[str, Any],
    option: dict[str, Any],
    ordinal: int,
    card_names: Mapping[int, str],
    attack_names: Mapping[int, str],
    target_token: Callable[[dict[str, Any]], str | None] | None,
) -> dict[str, Any]:
    option_type = _strict_int(option.get("type"), "option.type")
    if option_type not in OPTION_TYPE_NAMES:
        raise UnsafeOptionError(f"unknown option type: {option_type}")
    kind = OPTION_TYPE_NAMES[option_type]
    label = OPTION_LABELS.get(option_type)
    detail = ""
    hidden_prize = option.get("area") == 6
    card = None if hidden_prize else resolve_option_card(obs, option)
    target = None if hidden_prize else resolve_option_target(obs, option)
    if option_type == 0:
        number = _strict_int(option.get("number"), "option.number")
        label = str(number)
    elif option_type in {3, 4, 5, 7, 8, 9, 10, 11}:
        label = _name_for_card(card, card_names) or _anonymous_card_label(option, ordinal)
        verbs = {7: "使う", 8: "付ける", 9: "進化", 10: "特性", 11: "トラッシュ"}
        detail = "裏向きのサイド" if hidden_prize else verbs.get(option_type, "カード")
        if option_type in {8, 9}:
            target_name = _name_for_card(target, card_names)
            if target_name is None:
                raise UnsafeOptionError("attach/evolve target is not visible safely")
            source_name = label
            label = f"{source_name} → {target_name}"
            action = "つける" if option_type == 8 else "進化させる"
            detail = f"「{source_name}」を「{target_name}」に{action}"
    elif option_type == 6:
        count = _strict_int(option.get("count"), "option.count")
        energy_name = _name_for_card(card, card_names) or "エネルギー"
        label = f"{energy_name}（{count} 個分）"
    elif option_type == 13:
        attack_id = _strict_int(option.get("attackId"), "option.attackId")
        label = attack_names.get(attack_id) or f"ワザ {attack_id}"
    elif option_type == 15:
        card_id = _strict_int(option.get("cardId"), "option.cardId")
        label = card_names.get(card_id) or f"効果 {card_id}"
    elif option_type == 16:
        condition = _strict_int(option.get("specialConditionType"), "option.specialConditionType")
        if condition not in SPECIAL_CONDITION_LABELS:
            raise UnsafeOptionError(f"unknown special condition: {condition}")
        label = SPECIAL_CONDITION_LABELS[condition]
    if label is None:
        label = _anonymous_card_label(option, ordinal)
    shortcut_card = target if option_type in {8, 9} else card
    safe_option: dict[str, Any] = {
        "token": secrets.token_urlsafe(24),
        "kind": kind,
        "option_type": option_type,
        "choice_number": ordinal + 1,
        "label": label,
        "detail": detail,
        "target_token": target_token(shortcut_card) if target_token is not None and shortcut_card is not None else None,
    }
    if isinstance(card, dict) and type(card.get("id")) is int:
        safe_option["card_id"] = card["id"]
    if isinstance(target, dict) and type(target.get("id")) is int:
        safe_option["target_card_id"] = target["id"]
    if option_type == 13:
        safe_option["attack_id"] = _strict_int(option.get("attackId"), "option.attackId")
    if option_type == 6:
        safe_option["energy_count"] = _strict_int(option.get("count"), "option.count")
    return safe_option


@dataclass
class DecisionRequestState:
    request: dict[str, Any]
    token_to_index: dict[str, int]
    consumed: bool = False

    def submit(self, request_id: str, revision: int, tokens: list[str]) -> list[int]:
        if self.consumed:
            raise StaleDecisionError("request was already consumed")
        if request_id != self.request["request_id"] or revision != self.request["state_revision"]:
            raise StaleDecisionError("request id or state revision is stale")
        if not isinstance(tokens, list) or not all(isinstance(token, str) for token in tokens):
            raise InvalidSelectionError("tokens must be list[str]")
        if len(tokens) != len(set(tokens)):
            raise InvalidSelectionError("duplicate option token")
        minimum = self.request["min_count"]
        maximum = self.request["max_count"]
        if not minimum <= len(tokens) <= maximum:
            raise InvalidSelectionError(f"selection count must be between {minimum} and {maximum}")
        try:
            indices = [self.token_to_index[token] for token in tokens]
        except KeyError as exc:
            raise InvalidSelectionError("unknown option token") from exc
        self.consumed = True
        return indices


def build_decision_request(
    obs: dict[str, Any],
    revision: int,
    *,
    card_names: Mapping[int, str] | None = None,
    attack_names: Mapping[int, str] | None = None,
    target_token: Callable[[dict[str, Any]], str | None] | None = None,
) -> DecisionRequestState:
    current = obs.get("current")
    select = obs.get("select")
    if not isinstance(current, dict) or not isinstance(select, dict):
        raise UnsafeOptionError("observation has no current decision")
    if current.get("result") not in (-1, None):
        raise UnsafeOptionError("cannot build a decision for a finished match")
    select_type = _strict_int(select.get("type"), "select.type")
    if select_type not in SELECT_TYPE_NAMES:
        raise UnsafeOptionError(f"unknown select type: {select_type}")
    minimum = _strict_int(select.get("minCount"), "select.minCount")
    maximum = _strict_int(select.get("maxCount"), "select.maxCount")
    options = select.get("option")
    if not isinstance(options, list) or not all(isinstance(item, dict) for item in options):
        raise UnsafeOptionError("select.option must be a list of objects")
    if minimum < 0 or maximum < minimum or maximum > len(options):
        raise UnsafeOptionError("invalid selection bounds")
    allowed_types = COMPATIBLE_OPTION_TYPES[select_type]
    for option in options:
        option_type = _strict_int(option.get("type"), "option.type")
        if option_type not in allowed_types:
            raise UnsafeOptionError(f"option type {option_type} is invalid for select type {select_type}")
    names = card_names or {}
    attacks = attack_names or {}
    safe_options = [
        _safe_option(obs, option, index, names, attacks, target_token)
        for index, option in enumerate(options)
    ]
    context = select.get("context")
    context_value = context if type(context) is int else -1
    prompt = CONTEXT_PROMPTS.get(context_value, "合法な項目を選んでください。")
    if options and all(option.get("area") == 6 for option in options):
        prompt = "取るサイドを選んでください。番号は現在の候補順です。"
    elif options and all(option.get("type") == 8 for option in options):
        prompt = "つけるカードと、つけ先のポケモンの組み合わせを選んでください。番号は盤面にも表示されます。"
    request_id = str(uuid.uuid4())
    request = {
        "request_id": request_id,
        "state_revision": revision,
        "select_type": SELECT_TYPE_NAMES[select_type],
        "context": f"context_{context_value}",
        "prompt": prompt,
        "min_count": minimum,
        "max_count": maximum,
        "ordered": True,
        "options": safe_options,
    }
    token_to_index = {option["token"]: index for index, option in enumerate(safe_options)}
    return DecisionRequestState(request, token_to_index)


def validate_agent_action(obs: dict[str, Any], action: Any) -> list[int]:
    if not isinstance(action, list) or not all(type(index) is int for index in action):
        raise InvalidSelectionError("agent action must be list[int]")
    select = obs.get("select") or {}
    options = select.get("option") or []
    minimum = select.get("minCount")
    maximum = select.get("maxCount")
    if type(minimum) is not int or type(maximum) is not int:
        raise InvalidSelectionError("invalid engine selection bounds")
    if len(action) != len(set(action)):
        raise InvalidSelectionError("agent action contains duplicate indices")
    if not minimum <= len(action) <= maximum:
        raise InvalidSelectionError("agent action violates selection count")
    if any(index < 0 or index >= len(options) for index in action):
        raise InvalidSelectionError("agent action index is out of range")
    return action
