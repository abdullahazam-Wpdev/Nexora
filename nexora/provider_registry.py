"""Public capability metadata; never exposes keys or silently calls paid providers."""

PROVIDERS = [
    {
        "id": "ollama",
        "label": "SmolLM2 135M reference",
        "kind": "local",
        "adapter": "verified",
        "endpoint": "http://127.0.0.1:11434",
        "training": False,
    },
    {
        "id": "core",
        "label": "NEXORA Core",
        "kind": "local",
        "adapter": "verified research text prediction",
        "endpoint": "/api/generate",
        "training": True,
    },
    {
        "id": "localai",
        "label": "LocalAI",
        "kind": "local sidecar",
        "adapter": "verified CPU inference; start optional service",
        "endpoint": "http://127.0.0.1:8080/v1",
        "training": False,
    },
    {
        "id": "fcc",
        "label": "Free Claude Code proxy",
        "kind": "local sidecar",
        "adapter": "verified local Ollama routing; not Claude model weights",
        "endpoint": "http://127.0.0.1:8082",
        "training": False,
    },
    {
        "id": "nvidia-nim",
        "label": "NVIDIA NIM",
        "kind": "hosted",
        "adapter": "model discovery verified live against the real NVIDIA "
        "catalog with no key required (GET /v1/models is public); chat, "
        "streaming and embeddings are implemented but need your own "
        "NVIDIA_NIM_API_KEY. Check /api/nvidia/status for current state.",
        "docs": "https://docs.api.nvidia.com/",
        "key_env": "NVIDIA_NIM_API_KEY",
        "training": False,
    },
    {
        "id": "openai",
        "kind": "hosted",
        "adapter": "documentation only; not connected",
        "docs": "https://developers.openai.com/api/docs",
        "key_env": "OPENAI_API_KEY",
    },
    {
        "id": "anthropic",
        "kind": "hosted",
        "adapter": "documentation only; not connected",
        "docs": "https://platform.claude.com/docs/en/intro",
        "key_env": "ANTHROPIC_API_KEY",
    },
    {
        "id": "deepseek",
        "kind": "hosted",
        "adapter": "documentation only; not connected",
        "docs": "https://api-docs.deepseek.com/",
        "key_env": "DEEPSEEK_API_KEY",
    },
    {
        "id": "perplexity",
        "kind": "hosted",
        "adapter": "documentation only; not connected",
        "docs": "https://docs.perplexity.ai/",
        "key_env": "PERPLEXITY_API_KEY",
    },
    {
        "id": "kimi",
        "kind": "hosted",
        "adapter": "documentation only; not connected",
        "docs": "https://platform.kimi.ai/docs/overview",
        "key_env": "KIMI_API_KEY",
    },
    {
        "id": "xai",
        "kind": "hosted",
        "adapter": "documentation only; not connected",
        "docs": "https://docs.x.ai/overview",
        "key_env": "XAI_API_KEY",
    },
]

from nexora.openai_nim_models import MODELS

PROVIDERS.extend(MODELS)


def capabilities():
    import os

    from nexora.nvidia_nim import configured_key
    from nexora.config import STORE

    result = []
    for entry in PROVIDERS:
        row = dict(entry)
        ident = row["id"]
        if ident in {"ollama", "core", "localai", "fcc"}:
            row.update(
                chat=True,
                coding="limited/failed benchmarks; not professional",
                tool_calling=False,
                structured_output="not a guaranteed interface",
                local=True,
                cost="local CPU/RAM",
                quota="bounded local runtime; no external API quota",
            )
            if ident == "core":
                row.update(
                    model="selected independent NEXORA Core",
                    context_limit=128,
                    instruction_following="not demonstrated",
                    availability="checkpoint configured"
                    if (STORE / "selected-model.json").exists()
                    else "not configured",
                )
            else:
                row.update(
                    model="external SmolLM2 135M Q4 reference",
                    context_limit=768 if ident == "ollama" else None,
                    availability="check local runtime; not inferred from registration",
                )
        elif row.get("key_env"):
            row["availability"] = (
                "credential configured, generation unverified"
                if (
                    configured_key()
                    if row["key_env"] == "NVIDIA_NIM_API_KEY"
                    else os.environ.get(row["key_env"])
                )
                else "credential missing"
            )
            row["local"] = False
        if ident == "openai/gpt-oss-20b":
            row["availability"] = (
                "credential configured; generation unverified"
                if configured_key()
                else "credential missing"
            )
            row["local"] = False
        elif ident == "openai/whisper-large-v3":
            row["availability"] = (
                "speech service configured; not live verified"
                if os.environ.get("NEXORA_WHISPER_BASE") == "http://127.0.0.1:9000"
                else "speech service not configured"
            )
        row.setdefault(
            "availability", "documented integration; inspect live service status"
        )
        row.setdefault("cost", "not verified; account/deployment-specific")
        row["silent_paid_fallback"] = False
        result.append(row)
    return result
