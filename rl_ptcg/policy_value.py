"""PyTorch policy/value model over public state and legal options."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Sequence

import torch
from torch import nn


DEFAULT_MATCHUP_NAMES = (
    "unknown", "alakazam", "archaludon", "lucario", "starmie",
    "great_tusk", "dragapult", "marnie", "iono", "cynthia", "okidogi",
)


def is_card_feature(name: str) -> bool:
    return name.endswith("_id") and name != "attack_id"


def numeric_scale(name: str) -> float:
    if any(token in name for token in ("hp", "damage")):
        return 400.0
    if "turn" in name:
        return 60.0
    if "attack_id" in name:
        return 2048.0
    if any(token in name for token in ("count", "index", "ordinal", "number", "serial", "cost")):
        return 60.0
    if any(token in name for token in ("type", "context", "area", "condition")):
        return 64.0
    return 1.0


@dataclass(frozen=True)
class ModelConfig:
    state_feature_names: tuple[str, ...]
    option_feature_names: tuple[str, ...]
    card_vocab_size: int = 4096
    card_embedding_dim: int = 12
    hidden_dim: int = 256
    option_hidden_dim: int = 128
    matchup_names: tuple[str, ...] = DEFAULT_MATCHUP_NAMES
    matchup_embedding_dim: int = 16
    deck_embedding_dim: int = 24
    dropout: float = 0.05
    rule_prior_scale: float = 1.0
    residual_logit_cap: float = 1.0

    def to_dict(self) -> dict:
        value = asdict(self)
        value["state_feature_names"] = list(self.state_feature_names)
        value["option_feature_names"] = list(self.option_feature_names)
        value["matchup_names"] = list(self.matchup_names)
        return value

    @classmethod
    def from_dict(cls, value: dict) -> "ModelConfig":
        copied = dict(value)
        copied["state_feature_names"] = tuple(copied["state_feature_names"])
        copied["option_feature_names"] = tuple(copied["option_feature_names"])
        if "matchup_names" in copied:
            copied["matchup_names"] = tuple(copied["matchup_names"])
        return cls(**copied)


class FeatureEncoder(nn.Module):
    def __init__(self, names: Sequence[str], card_embedding: nn.Embedding, card_dim: int):
        super().__init__()
        self.names = tuple(names)
        self.card_positions = tuple(i for i, name in enumerate(self.names) if is_card_feature(name))
        self.numeric_positions = tuple(i for i, name in enumerate(self.names) if not is_card_feature(name))
        self.card_embedding = card_embedding
        self.slot_embedding = nn.Embedding(max(1, len(self.card_positions)), card_dim)
        scales = [numeric_scale(self.names[i]) for i in self.numeric_positions]
        self.register_buffer("numeric_scales", torch.tensor(scales, dtype=torch.float32), persistent=False)
        self.output_dim = len(self.numeric_positions) * 2 + len(self.card_positions) * card_dim

    def forward(self, values: torch.Tensor) -> torch.Tensor:
        pieces = []
        if self.numeric_positions:
            numeric = values[..., self.numeric_positions]
            present = numeric.ne(-1.0)
            scaled = torch.where(present, numeric / self.numeric_scales, torch.zeros_like(numeric))
            pieces.extend((scaled.clamp(-4.0, 4.0), present.to(values.dtype)))
        if self.card_positions:
            raw = values[..., self.card_positions]
            present = raw.ge(0.0)
            ids = torch.where(present, raw.round() + 1.0, torch.zeros_like(raw)).long()
            ids = ids.clamp(0, self.card_embedding.num_embeddings - 1)
            embedded = self.card_embedding(ids)
            slots = self.slot_embedding.weight
            view_shape = [1] * (embedded.ndim - 2) + [len(self.card_positions), slots.shape[-1]]
            embedded = (embedded + slots.view(*view_shape)) * present.unsqueeze(-1)
            pieces.append(embedded.flatten(-2))
        return torch.cat(pieces, dim=-1)


class PolicyValueNet(nn.Module):
    def __init__(self, config: ModelConfig):
        super().__init__()
        self.config = config
        self.card_embedding = nn.Embedding(config.card_vocab_size + 1, config.card_embedding_dim, padding_idx=0)
        self.state_features = FeatureEncoder(
            config.state_feature_names, self.card_embedding, config.card_embedding_dim
        )
        self.option_features = FeatureEncoder(
            config.option_feature_names, self.card_embedding, config.card_embedding_dim
        )
        self.matchup_embedding = nn.Embedding(len(config.matchup_names), config.matchup_embedding_dim)
        self.deck_projection = nn.Sequential(
            nn.Linear(config.card_embedding_dim, config.deck_embedding_dim),
            nn.SiLU(),
        )
        self.state_net = nn.Sequential(
            nn.Linear(self.state_features.output_dim + config.matchup_embedding_dim + config.deck_embedding_dim,
                      config.hidden_dim),
            nn.LayerNorm(config.hidden_dim),
            nn.SiLU(),
            nn.Dropout(config.dropout),
            nn.Linear(config.hidden_dim, config.hidden_dim),
            nn.SiLU(),
        )
        self.option_net = nn.Sequential(
            nn.Linear(self.option_features.output_dim + 2, config.option_hidden_dim),
            nn.LayerNorm(config.option_hidden_dim),
            nn.SiLU(),
            nn.Linear(config.option_hidden_dim, config.option_hidden_dim),
            nn.SiLU(),
        )
        joint_dim = config.hidden_dim + config.option_hidden_dim
        self.policy_head = nn.Sequential(
            nn.Linear(joint_dim, config.option_hidden_dim),
            nn.SiLU(),
            nn.Linear(config.option_hidden_dim, 1),
        )
        self.value_head = nn.Sequential(
            nn.Linear(config.hidden_dim, config.option_hidden_dim),
            nn.SiLU(),
            nn.Linear(config.option_hidden_dim, 1),
            nn.Tanh(),
        )

    def encode_deck(self, opponent_deck: torch.Tensor | None, batch_size: int, device) -> torch.Tensor:
        if opponent_deck is None:
            return torch.zeros(batch_size, self.config.deck_embedding_dim, device=device)
        present = opponent_deck.ge(0)
        ids = torch.where(present, opponent_deck + 1, torch.zeros_like(opponent_deck)).long()
        ids = ids.clamp(0, self.card_embedding.num_embeddings - 1)
        embedded = self.card_embedding(ids) * present.unsqueeze(-1)
        denominator = present.sum(dim=1, keepdim=True).clamp_min(1).to(embedded.dtype)
        return self.deck_projection(embedded.sum(dim=1) / denominator)

    def encode_state(
        self, state: torch.Tensor, matchup_ids: torch.Tensor | None = None,
        opponent_deck: torch.Tensor | None = None,
    ) -> torch.Tensor:
        if matchup_ids is None:
            matchup_ids = torch.zeros(state.shape[0], dtype=torch.long, device=state.device)
        matchup = self.matchup_embedding(matchup_ids.long())
        deck = self.encode_deck(opponent_deck, state.shape[0], state.device)
        return self.state_net(torch.cat((self.state_features(state), matchup, deck), dim=-1))

    def predict_value(
        self, state: torch.Tensor, matchup_ids: torch.Tensor | None = None,
        opponent_deck: torch.Tensor | None = None,
    ) -> torch.Tensor:
        return self.value_head(self.encode_state(state, matchup_ids, opponent_deck)).squeeze(-1)

    def forward(
        self,
        state: torch.Tensor,
        options: torch.Tensor,
        option_mask: torch.Tensor,
        rule_features: torch.Tensor,
        matchup_ids: torch.Tensor | None = None,
        opponent_deck: torch.Tensor | None = None,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        state_hidden = self.encode_state(state, matchup_ids, opponent_deck)
        option_input = torch.cat((self.option_features(options), rule_features), dim=-1)
        option_hidden = self.option_net(option_input)
        repeated_state = state_hidden.unsqueeze(1).expand(-1, options.shape[1], -1)
        delta = self.policy_head(torch.cat((repeated_state, option_hidden), dim=-1)).squeeze(-1)
        delta = self.config.residual_logit_cap * torch.tanh(delta)
        logits = self.config.rule_prior_scale * rule_features[..., 0] + delta
        logits = logits.masked_fill(~option_mask, torch.finfo(logits.dtype).min)
        value = self.value_head(state_hidden).squeeze(-1)
        return logits, value


def selection_nll(
    logits: torch.Tensor,
    option_mask: torch.Tensor,
    selected_indices: Sequence[Sequence[int]],
    row_weights: torch.Tensor | None = None,
) -> torch.Tensor:
    losses = []
    weights = []
    for row, indices in enumerate(selected_indices):
        remaining = option_mask[row].clone()
        for index in indices:
            if index < 0 or index >= logits.shape[1] or not bool(remaining[index]):
                continue
            masked = logits[row].masked_fill(~remaining, torch.finfo(logits.dtype).min)
            losses.append(-torch.log_softmax(masked, dim=0)[index])
            weights.append(
                row_weights[row].to(logits.device) if row_weights is not None
                else logits.new_tensor(1.0)
            )
            remaining[index] = False
    if not losses:
        return logits.sum() * 0.0
    stacked_weights = torch.stack(weights)
    return (torch.stack(losses) * stacked_weights).sum() / stacked_weights.sum().clamp_min(1e-8)


def greedy_selection(logits: torch.Tensor, counts: Sequence[int]) -> list[list[int]]:
    output = []
    for row, count in enumerate(counts):
        if count <= 0:
            output.append([])
            continue
        output.append(torch.topk(logits[row], k=min(int(count), logits.shape[1])).indices.tolist())
    return output
