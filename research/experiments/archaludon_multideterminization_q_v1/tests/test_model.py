import torch

from research.experiments.archaludon_multideterminization_q_v1.multidet_q.config import REPO_ROOT, load_config
from research.experiments.archaludon_multideterminization_q_v1.multidet_q.dataset import load_dataset
from research.experiments.archaludon_multideterminization_q_v1.multidet_q.model import (
    ExpectedQModel,
    ModelConfig,
    group_loss,
    load_checkpoint,
    save_checkpoint,
)
from research.experiments.archaludon_multideterminization_q_v1.multidet_q.search_runtime import _load_api
from research.experiments.archaludon_multideterminization_q_v1.multidet_q.semantic_encoder import SemanticVocab, build_vocab


def _row():
    public_state = {"select": {"context": 0}, "players": [], "turn": 0, "turn_action_count": 0, "first_player_relative": -1, "stadium": [], "looking_visible": []}
    candidates = [
        {"canonical_identity": "a", "is_baseline": True, "selected_options": [], "order_sensitive": False, "target_q": -1.0},
        {"canonical_identity": "b", "is_baseline": False, "selected_options": [{"semantic_payload": {"option_type": 7, "fields": {"index": 0}}, "execution_payload": {"source_card_id": 1}}], "order_sensitive": False, "target_q": 1.0},
    ]
    return {"public_state": public_state, "context": 0, "candidates": candidates}


def test_variable_group_forward_loss_backward_and_checkpoint(tmp_path):
    torch.manual_seed(2)
    model = ExpectedQModel(ModelConfig(SemanticVocab(max_card_id=20, max_attack_id=20)))
    row = _row()
    scores = model.score_group(row)
    longer = dict(row)
    longer["candidates"] = row["candidates"] + [dict(row["candidates"][0], canonical_identity="c")]
    assert scores.shape == (2,)
    assert model.score_group(longer).shape == (3,)
    target = torch.tensor([-1.0, 1.0])
    loss = group_loss(scores, target, huber_beta=0.25, temperature=0.20, listwise_weight=0.50)
    loss.backward()
    assert torch.isfinite(loss)
    path = tmp_path / "model.pt"
    save_checkpoint(path, model, seed=1, metrics={"x": 1})
    reloaded, payload = load_checkpoint(path)
    assert payload["seed"] == 1
    for name, value in model.state_dict().items():
        assert torch.equal(value, reloaded.state_dict()[name])


def test_existing_dataset_one_batch_train_smoke():
    dataset_path = REPO_ROOT / "_local_generated" / "archaludon_multideterminization_q_v1" / "dataset_through_round_00.json"
    if dataset_path.is_file():
        rows = load_dataset(load_config())["rows"]
        training = [row for row in rows if row.get("split") == "training"]
    else:
        first = dict(_row(), split="training", branch_group_id="fixture-a")
        second = dict(first, branch_group_id="fixture-b", candidates=first["candidates"] + [dict(first["candidates"][0], canonical_identity="c")])
        training = [first, second]

    by_candidate_count = {}
    for row in training:
        by_candidate_count.setdefault(len(row["candidates"]), row)
    assert len(by_candidate_count) >= 2
    smoke_rows = list(by_candidate_count.values())[:2]

    config = load_config()
    model = ExpectedQModel(ModelConfig(build_vocab(_load_api())))
    optimizer = torch.optim.AdamW(model.parameters(), lr=config.learning_rate, weight_decay=config.weight_decay)
    optimizer.zero_grad(set_to_none=True)
    losses = []
    for row in smoke_rows:
        predicted = model.score_group(row)
        target = torch.tensor([float(candidate["target_q"]) for candidate in row["candidates"]], dtype=torch.float32)
        assert predicted.shape == target.shape
        losses.append(
            group_loss(
                predicted,
                target,
                huber_beta=config.huber_beta,
                temperature=config.listwise_temperature,
                listwise_weight=config.listwise_loss_weight,
            )
        )
    loss = torch.stack(losses).mean()
    assert bool(torch.isfinite(loss).all())
    loss.backward()
    gradient_norm = torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
    assert bool(torch.isfinite(gradient_norm).all())
    optimizer.step()
    assert all(bool(torch.isfinite(parameter).all()) for parameter in model.parameters())
