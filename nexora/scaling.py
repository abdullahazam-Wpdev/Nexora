"""Planning-only GPU sizing. Does not allocate, download, provision or launch training."""

from dataclasses import asdict
from nexora.model import Config

FUTURE_CONFIGS = {
    "medium-gpu-candidate": Config(
        vocab_size=8192,
        dim=512,
        layers=8,
        heads=8,
        context=512,
        tie_embeddings=True,
        init_std=0.02,
    ),
    "large-multigpu-candidate": Config(
        vocab_size=32000,
        dim=1024,
        layers=24,
        heads=16,
        context=2048,
        tie_embeddings=True,
        init_std=0.02,
    ),
}


def estimate(config, tokens):
    # Current architecture: QKV+O=4d², SwiGLU=9d², two norms/block plus final norm.
    parameters = (
        13 * config.dim**2 * config.layers
        + (1 if config.tie_embeddings else 2) * config.vocab_size * config.dim
        + 2 * config.dim * config.layers
        + config.dim
    )
    return {
        "config": asdict(config),
        "parameters": parameters,
        "fp32_adamw_state_bytes_lower_bound": 16 * parameters,
        "training_flops_heuristic": 6 * parameters * tokens,
        "tokens": tokens,
        "exclusions": "Activations, attention workspaces, temporary buffers, allocator overhead, dataset and checkpoint buffers are excluded; not a measured VRAM requirement.",
    }


if __name__ == "__main__":
    import json

    print(
        json.dumps(
            {
                name: estimate(c, 20 * estimate(c, 1)["parameters"])
                for name, c in FUTURE_CONFIGS.items()
            },
            indent=2,
        )
    )
