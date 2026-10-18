#!/usr/bin/env python3
"""Extract public metadata from installed FCC source using AST, never settings/secrets."""

import ast
import hashlib
import json
from pathlib import Path

root = Path(__file__).resolve().parent.parent
package = next(
    (root / ".tools/fcc-venv/lib").glob("python*/site-packages/free_claude_code")
)
providers = package / "config/provider_catalog.py"
models = package / "api/model_catalog.py"
rows = []
for node in ast.walk(ast.parse(providers.read_text())):
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "ProviderDescriptor"
    ):
        row = {}
        for kw in node.keywords:
            if kw.arg in {
                "provider_id",
                "display_name",
                "website_url",
                "local",
                "credential_env",
            } and isinstance(kw.value, ast.Constant):
                row[kw.arg] = kw.value.value
        rows.append(row)
aliases = []
for node in ast.walk(ast.parse(models.read_text())):
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "ModelResponse"
    ):
        row = {
            kw.arg: kw.value.value
            for kw in node.keywords
            if kw.arg in {"id", "display_name"} and isinstance(kw.value, ast.Constant)
        }
        if row.get("id"):
            aliases.append(row)
result = {
    "source": "https://github.com/alishahryar1/free-claude-code",
    "license": "AGPL-3.0",
    "provider_source_sha256": hashlib.sha256(providers.read_bytes()).hexdigest(),
    "alias_source_sha256": hashlib.sha256(models.read_bytes()).hexdigest(),
    "providers": rows,
    "aliases": aliases,
    "note": "Installed-source metadata snapshot; aliases are routing names, not installed Claude weights. Available upstream models depend on configured providers and live discovery.",
}
(root / "catalogs/fcc/catalog.json").write_text(json.dumps(result, indent=2) + "\n")
print(f"Exported {len(rows)} provider descriptors and {len(aliases)} routing aliases")
