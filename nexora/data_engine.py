"""Versioned, rights-reviewed text preparation and bounded source acquisition."""

import argparse
import hashlib
import json
import re
import unicodedata
import urllib.request
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse
from nexora.artifacts import atomic_json, identifier, sha256, lock
from nexora.config import STORE

LICENSES = {"MIT", "Apache-2.0", "CC0-1.0", "public-domain", "PSF-2.0"}
SECRET = re.compile(
    r"(?i)(api[_-]?key\s*[=:]|password\s*[=:]|-----BEGIN .*PRIVATE KEY|\b[\w.+-]+@[\w.-]+\.[a-z]{2,}\b|\b(?:AKIA|ASIA)[A-Z0-9]{16}\b|\bgh[pousr]_[A-Za-z0-9]{20,}|\b(?:\d[ -]?){13,16}\b)"
)
VERSION = "text-v2.1"


def canonical(text):
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


def shingles(text, n=12):
    words = canonical(text).split()
    return {
        hashlib.sha256(" ".join(words[i : i + n]).encode()).hexdigest()
        for i in range(max(0, len(words) - n + 1))
    }


def clean_rst(text):
    text = unicodedata.normalize("NFC", text.replace("\r\n", "\n"))
    text = re.sub(r"^\.\. [^\n]*\n", "", text, flags=re.M)
    text = re.sub(r":\w+:`([^`]+)`", r"\1", text)
    text = re.sub(r"`([^`]+) <[^>]+>`_", r"\1", text)
    text = re.sub(r"^[=\-~^*#]{3,}\s*$", "", text, flags=re.M)
    return text


def build_dataset(
    name,
    documents,
    *,
    approved,
    license,
    provenance,
    reviewer="local-owner",
    notices=None,
    store=None,
):
    store = Path(store or STORE)
    identifier(name)
    if (
        not approved
        or license not in LICENSES
        or not provenance.strip()
        or not reviewer.strip()
    ):
        raise ValueError(
            "Dataset requires explicit approval, reviewed license, provenance and reviewer"
        )
    if (
        len(documents) > 5000
        or sum(len(d["text"].encode()) for d in documents) > 5_000_000
    ):
        raise ValueError("Dataset exceeds bounded local ingestion size")
    if license == "PSF-2.0" and not notices:
        raise ValueError(
            "PSF-2.0 ingestion requires retained license and copyright notices"
        )
    source_ids = sorted(
        {str(d["source_id"]) for d in documents},
        key=lambda x: hashlib.sha256(x.encode()).hexdigest(),
    )
    if len(source_ids) < 3:
        raise ValueError(
            "At least three independent source groups required for source-level holdouts"
        )
    held = max(1, int(len(source_ids) * 0.1))
    mapping = {
        s: ("validation" if i < held else "test" if i < held * 2 else "train")
        for i, s in enumerate(source_ids)
    }
    splits = {k: [] for k in ("train", "validation", "test")}
    rejected = Counter()
    seen = set()
    near = []
    source_records = {}
    # Train first: repeated text from held-out sources is removed, never moved into train.
    docs = sorted(
        documents,
        key=lambda d: (
            ("train", "validation", "test").index(mapping[str(d["source_id"])]),
            str(d["source_id"]),
            hashlib.sha256(d["text"].encode()).hexdigest(),
        ),
    )
    for d in docs:
        source = str(d["source_id"])
        text = unicodedata.normalize("NFC", d["text"]).strip()
        source_records[source] = {
            "split": mapping[source],
            "url": d.get("url"),
            "raw_sha256": d.get("raw_sha256"),
        }
        if SECRET.search(text):
            rejected["sensitive_pattern"] += 1
            continue
        text = "".join(
            ch
            for ch in text
            if ch == "\n" or ch == "\t" or not unicodedata.category(ch).startswith("C")
        )
        if (
            len(text) < 80
            or len(text) > 4000
            or sum(ch.isalpha() for ch in text) / max(1, len(text)) < 0.25
        ):
            rejected["quality"] += 1
            continue
        key = hashlib.sha256(canonical(text).encode()).hexdigest()
        if key in seen:
            rejected["duplicate"] += 1
            continue
        grams = shingles(text)
        if grams and any(
            len(grams & other) / len(grams | other) > 0.85 for other in near
        ):
            rejected["near_duplicate"] += 1
            continue
        seen.add(key)
        near.append(grams)
        splits[mapping[source]].append(
            {
                "id": key,
                "source_id": source,
                "text": text,
                "language_hint": "latin-script"
                if sum(ord(c) < 128 for c in text) / len(text) > 0.9
                else "mixed-or-non-latin",
                "sha256": hashlib.sha256(text.encode()).hexdigest(),
            }
        )
    if any(not v for v in splits.values()):
        raise ValueError("Every source-held-out split must contain quality documents")
    identity = {
        "pipeline": VERSION,
        "license": license,
        "provenance": provenance,
        "reviewer": reviewer,
        "notices": notices,
        "sources": source_records,
        "documents": {k: [d["sha256"] for d in v] for k, v in splits.items()},
    }
    version = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    dataset_id = identifier(name + "-" + version[:12])
    folder = store / "datasets" / dataset_id
    with lock(store / ".datasets.lock"):
        if (folder / "manifest.json").exists():
            return json.loads((folder / "manifest.json").read_text())
        folder.mkdir(parents=True, exist_ok=False)
        files = {}
        for split, items in splits.items():
            p = folder / (split + ".jsonl")
            p.write_text(
                "".join(json.dumps(d, ensure_ascii=False) + "\n" for d in items)
            )
            files[p.name] = sha256(p)
        report = {
            "input_documents": len(documents),
            "accepted_documents": sum(map(len, splits.values())),
            "rejected": dict(rejected),
            "split_documents": {k: len(v) for k, v in splits.items()},
            "split_sources": {
                k: sorted({d["source_id"] for d in v}) for k, v in splits.items()
            },
            "exact_document_overlap": 0,
            "near_duplicate_jaccard_threshold": 0.85,
            "language_detection": "Unicode script heuristic, not a language classifier",
            "private_data_filter": "Conservative pattern filter, not comprehensive DLP",
            "chars": {k: sum(len(d["text"]) for d in v) for k, v in splits.items()},
        }
        manifest = {
            "id": dataset_id,
            "name": name,
            "version": version,
            "pipeline": VERSION,
            "license": license,
            "provenance": provenance,
            "approved": True,
            "reviewer": reviewer,
            "notices": notices,
            "documents": report["accepted_documents"],
            "sources": source_records,
            "files": files,
            "quality": report,
        }
        atomic_json(folder / "quality.json", report)
        atomic_json(folder / "manifest.json", manifest)
    return manifest


def load_dataset(dataset_id, store=None):
    folder = Path(store or STORE) / "datasets" / identifier(dataset_id)
    manifest = json.loads((folder / "manifest.json").read_text())
    if not manifest.get("approved") or manifest.get("license") not in LICENSES:
        raise ValueError("Unapproved dataset")
    for file, digest in manifest["files"].items():
        if (
            file not in {"train.jsonl", "validation.jsonl", "test.jsonl"}
            or sha256(folder / file) != digest
        ):
            raise ValueError("Dataset integrity verification failed")
    return manifest, {
        split: [
            json.loads(line)
            for line in (folder / (split + ".jsonl")).read_text().splitlines()
        ]
        for split in ("train", "validation", "test")
    }


def acquire(catalog_path, *, approve=False, store=None):
    """CLI only: fixed reviewed GitHub source URLs; no authenticated scraping/SSRF API."""
    store = Path(store or STORE)
    catalog = json.loads(Path(catalog_path).read_text())
    if (
        not approve
        or catalog.get("status") != "reviewed"
        or not catalog.get("reviewer")
    ):
        raise ValueError(
            "Reviewed source catalog and explicit --approve-download are required"
        )
    if catalog["license"] not in LICENSES:
        raise ValueError("Unsupported license")
    cap = min(int(catalog["max_total_bytes"]), 1_000_000)
    total = 0
    docs = []
    records = []
    notices = {}
    for source in catalog["sources"]:
        url = source["url"]
        parsed = urlparse(url)
        if (
            parsed.scheme != "https"
            or parsed.netloc != "raw.githubusercontent.com"
            or not parsed.path.startswith("/python/cpython/v3.13.0/")
        ):
            raise ValueError(
                "URL outside the reviewed, version-pinned source allowlist"
            )
        raw_dir = store / "raw" / catalog["id"]
        raw_dir.mkdir(parents=True, exist_ok=True)
        dest = raw_dir / identifier(source["id"])
        if dest.exists():
            raw = dest.read_bytes()
        else:
            with urllib.request.urlopen(
                urllib.request.Request(
                    url, headers={"User-Agent": "NEXORA-local-research/0.2"}
                ),
                timeout=30,
            ) as response:
                if response.geturl() != url:
                    raise ValueError("Source redirects require renewed review")
                raw = response.read(min(int(source["max_bytes"]), cap - total) + 1)
        if len(raw) > int(source["max_bytes"]) or total + len(raw) > cap:
            raise ValueError("Download exceeds reviewed byte budget")
        digest = hashlib.sha256(raw).hexdigest()
        if source.get("sha256") and source["sha256"] != digest:
            raise ValueError("Source hash changed; review required")
        text = raw.decode("utf-8", errors="strict")
        total += len(raw)
        dest.write_bytes(raw)
        records.append({**source, "sha256": digest, "bytes": len(raw)})
        if source.get("role") == "license":
            notices[source["id"]] = text
            continue
        for paragraph in re.split(r"\n\s*\n", clean_rst(text)):
            # Non-overlapping, bounded chunks; entire source remains in one split.
            for offset in range(0, len(paragraph), 2000):
                docs.append(
                    {
                        "text": paragraph[offset : offset + 2000],
                        "source_id": source["id"],
                        "url": url,
                        "raw_sha256": digest,
                    }
                )
    if not notices:
        raise ValueError("License notices must be acquired before ingestion")
    manifest = build_dataset(
        catalog["id"],
        docs,
        approved=True,
        license=catalog["license"],
        provenance=catalog["provenance"],
        reviewer=catalog["reviewer"],
        notices=notices,
        store=store,
    )
    atomic_json(
        store / "datasets" / manifest["id"] / "acquisition.json",
        {
            "catalog": catalog,
            "sources": records,
            "total_bytes": total,
            "changes": "Extracted RST paragraphs, normalized Unicode, filtered sensitive/low-quality and duplicate text, source-level holdouts; no endorsement by Python Software Foundation.",
        },
    )
    return manifest


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--catalog", required=True)
    p.add_argument("--approve-download", action="store_true")
    a = p.parse_args()
    print(json.dumps(acquire(a.catalog, approve=a.approve_download), indent=2))
