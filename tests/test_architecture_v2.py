import pytest
import torch
from nexora.model import Config, Core


def test_new_config_validation():
    for kwargs in (
        {"heads": 0},
        {"dim": 0},
        {"layers": 0},
        {"context": 0},
        {"vocab_size": 0},
    ):
        with pytest.raises(ValueError):
            Config(**kwargs)


def test_tied_weights_and_initialization():
    torch.manual_seed(21)
    m = Core(
        Config(
            vocab_size=300,
            dim=64,
            layers=2,
            heads=4,
            tie_embeddings=True,
            init_std=0.02,
        )
    )
    assert m.head.weight is m.embedding.weight
    assert 0.015 < m.embedding.weight.std().item() < 0.025
    assert torch.isfinite(m(torch.ones((2, 12), dtype=torch.long))).all()


def test_legacy_checkpoint_still_loads():
    m = Core(Config(vocab_size=32, dim=32, layers=1, heads=4))
    n = Core(Config(vocab_size=32, dim=32, layers=1, heads=4))
    n.load_state_dict(m.state_dict(), strict=True)
    x = torch.tensor([[1, 2, 3]])
    torch.testing.assert_close(m(x), n(x), rtol=0, atol=0)
