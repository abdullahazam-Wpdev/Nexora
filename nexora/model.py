"""NEXORA Core: randomly initialized decoder with RoPE, RMSNorm and SwiGLU."""

from dataclasses import dataclass
import torch
from torch import nn
from torch.nn import functional as F


@dataclass
class Config:
    vocab_size: int = 384
    dim: int = 64
    layers: int = 2
    heads: int = 4
    context: int = 64
    tie_embeddings: bool = False
    init_std: float | None = None

    def __post_init__(self):
        if min(self.vocab_size, self.dim, self.layers, self.heads, self.context) < 1:
            raise ValueError("All model dimensions must be positive")
        if self.init_std is not None and self.init_std <= 0:
            raise ValueError("init_std must be positive")
        if self.dim % self.heads or (self.dim // self.heads) % 2:
            raise ValueError("Head dimension must be even and divide model dimension")


class Attention(nn.Module):
    def __init__(self, c):
        super().__init__()
        self.heads = c.heads
        self.qkv = nn.Linear(c.dim, c.dim * 3, bias=False)
        self.out = nn.Linear(c.dim, c.dim, bias=False)
        self.register_buffer(
            "freq",
            1
            / (
                10000
                ** (torch.arange(0, c.dim // c.heads, 2).float() / (c.dim // c.heads))
            ),
        )

    def rotate(self, x):
        a = torch.arange(x.size(-2), device=x.device)[:, None] * self.freq[None, :]
        even, odd = x[..., ::2], x[..., 1::2]
        return torch.stack(
            (even * a.cos() - odd * a.sin(), even * a.sin() + odd * a.cos()), -1
        ).flatten(-2)

    def forward(self, x):
        b, t, d = x.shape
        q, k, v = (
            self.qkv(x)
            .reshape(b, t, 3, self.heads, d // self.heads)
            .permute(2, 0, 3, 1, 4)
            .unbind(0)
        )
        y = F.scaled_dot_product_attention(
            self.rotate(q), self.rotate(k), v, is_causal=True
        )
        return self.out(y.transpose(1, 2).reshape(b, t, d))


class Block(nn.Module):
    def __init__(self, c):
        super().__init__()
        self.n1, self.n2 = nn.RMSNorm(c.dim), nn.RMSNorm(c.dim)
        self.attn = Attention(c)
        self.gate = nn.Linear(c.dim, c.dim * 3, bias=False)
        self.up = nn.Linear(c.dim, c.dim * 3, bias=False)
        self.down = nn.Linear(c.dim * 3, c.dim, bias=False)

    def forward(self, x):
        x = x + self.attn(self.n1(x))
        y = self.n2(x)
        return x + self.down(F.silu(self.gate(y)) * self.up(y))


class Core(nn.Module):
    def __init__(self, c):
        super().__init__()
        self.config = c
        self.embedding = nn.Embedding(c.vocab_size, c.dim)
        self.blocks = nn.Sequential(*[Block(c) for _ in range(c.layers)])
        self.norm = nn.RMSNorm(c.dim)
        self.head = nn.Linear(c.dim, c.vocab_size, bias=False)
        if c.init_std is not None:
            self.apply(
                lambda module: (
                    nn.init.normal_(module.weight, mean=0, std=c.init_std)
                    if isinstance(module, (nn.Linear, nn.Embedding))
                    else None
                )
            )
            for block in self.blocks:
                nn.init.normal_(
                    block.attn.out.weight, std=c.init_std / (2 * c.layers) ** 0.5
                )
                nn.init.normal_(
                    block.down.weight, std=c.init_std / (2 * c.layers) ** 0.5
                )
        if c.tie_embeddings:
            self.head.weight = self.embedding.weight

    def forward(self, ids):
        if ids.shape[1] > self.config.context:
            raise ValueError("Context limit exceeded")
        return self.head(self.norm(self.blocks(self.embedding(ids))))

    @torch.no_grad()
    def generate(self, ids, count=32):
        self.eval()
        for _ in range(count):
            logits = self(ids[:, -self.config.context :])[:, -1]
            ids = torch.cat((ids, logits.argmax(-1, keepdim=True)), 1)
        return ids
