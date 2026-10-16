"""Small licensed corpus expansion with immutable source-held-out evaluation suites."""

import argparse
import hashlib
import json
import re
import unicodedata
import urllib.request
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse
from nexora.artifacts import atomic_json, identifier, lock, sha256
from nexora.config import STORE
from nexora.data_engine import SECRET, canonical, clean_rst, shingles, load_dataset

PIPELINE = "frozen-source-expansion-v1"


def download_reviewed(catalog_path, approved=False, store=None):
    store = Path(store or STORE)
    catalog = json.loads(Path(catalog_path).read_text())
    if (
        not approved
        or catalog.get("status") != "reviewed"
        or not catalog.get("reviewer")
        or catalog.get("license") != "PSF-2.0"
    ):
        raise ValueError(
            "Explicit approval and a reviewed PSF source catalog are required"
        )
    identifier(catalog["id"])
    cap = min(catalog["max_total_bytes"], 1_000_000)
    total = 0
    records = []
    raw = {}
    notices = {}
    for source in catalog["sources"]:
        identifier(source["id"])
        url = source["url"]
        parsed = urlparse(url)
        if (
            parsed.scheme != "https"
            or parsed.netloc != "raw.githubusercontent.com"
            or not parsed.path.startswith("/python/cpython/v3.13.0/")
        ):
            raise ValueError("Source outside version-pinned reviewed allowlist")
        folder = store / "raw" / catalog["id"]
        folder.mkdir(parents=True, exist_ok=True)
        p = folder / source["id"]
        if p.exists():
            content = p.read_bytes()
        else:
            with urllib.request.urlopen(
                urllib.request.Request(
                    url, headers={"User-Agent": "NEXORA-local-research/0.3"}
                ),
                timeout=30,
            ) as response:
                if response.geturl() != url:
                    raise ValueError("Redirect requires renewed review")
                content = response.read(min(source["max_bytes"], cap - total) + 1)
        if len(content) > source["max_bytes"] or total + len(content) > cap:
            raise ValueError("Reviewed download byte budget exceeded")
        digest = hashlib.sha256(content).hexdigest()
        if source.get("sha256") and digest != source["sha256"]:
            raise ValueError("Reviewed source hash mismatch")
        text = content.decode("utf-8", errors="strict")
        p.write_bytes(content)
        total += len(content)
        record = {**source, "sha256": digest, "bytes": len(content)}
        records.append(record)
        raw[source["id"]] = text
        if source.get("role") == "license":
            notices[source["id"]] = text
    if not notices:
        raise ValueError("Full upstream license notices are required")
    acquisition = {
        "catalog": catalog,
        "sources": records,
        "downloaded_or_cached_bytes": total,
        "changes": "RST paragraph extraction, Unicode normalization, quality/privacy filtering, held-out protection and exact/near deduplication; no PSF endorsement.",
    }
    atomic_json(store / "raw" / catalog["id"] / "acquisition.json", acquisition)
    return acquisition, raw, notices


def extracted(source, text):
    for paragraph in re.split(r"\n\s*\n", clean_rst(text)):
        for offset in range(0, len(paragraph), 2000):
            value = unicodedata.normalize(
                "NFC", paragraph[offset : offset + 2000]
            ).strip()
            if SECRET.search(value):
                continue
            value = "".join(
                c
                for c in value
                if c in "\n\t" or not unicodedata.category(c).startswith("C")
            )
            if (
                not 80 <= len(value) <= 4000
                or sum(c.isalpha() for c in value) / max(1, len(value)) < 0.25
            ):
                continue
            yield {
                "id": hashlib.sha256(canonical(value).encode()).hexdigest(),
                "source_id": source["id"],
                "text": value,
                "sha256": hashlib.sha256(value.encode()).hexdigest(),
                "url": source["url"],
                "raw_sha256": source["sha256"],
            }


def freeze_suite(name, validation, test, *, notices, sources, store=None):
    store = Path(store or STORE)
    identifier(name)
    folder = store / "evaluation_suites" / name
    pairs = {
        k: [d["sha256"] for d in v]
        for k, v in {"validation": validation, "test": test}.items()
    }
    if not validation or not test:
        raise ValueError("Both held-out splits must be nonempty")
    if {canonical(d["text"]) for d in validation} & {
        canonical(d["text"]) for d in test
    }:
        raise ValueError("Held-out documents overlap")
    if {d["source_id"] for d in validation} & {d["source_id"] for d in test}:
        raise ValueError("Held-out source groups overlap")
    version = hashlib.sha256(
        json.dumps(
            {"documents": pairs, "sources": sources, "notices": notices}, sort_keys=True
        ).encode()
    ).hexdigest()
    with lock(store / ".datasets.lock"):
        if (folder / "suite.json").exists():
            suite = json.loads((folder / "suite.json").read_text())
            if suite["version"] != version:
                raise ValueError(
                    "Frozen evaluation suite cannot be changed; create a new explicit suite name"
                )
            for file, digest in suite["files"].items():
                if sha256(folder / file) != digest:
                    raise ValueError("Frozen evaluation integrity mismatch")
            return suite
        folder.mkdir(parents=True, exist_ok=False)
        files = {}
        for split, items in {"validation": validation, "test": test}.items():
            p = folder / (split + ".jsonl")
            p.write_text(
                "".join(json.dumps(d, ensure_ascii=False) + "\n" for d in items)
            )
            files[p.name] = sha256(p)
        suite = {
            "id": name,
            "version": version,
            "files": files,
            "sources": sources,
            "license": "PSF-2.0",
            "notices": notices,
            "counts": {
                k: len(v) for k, v in {"validation": validation, "test": test}.items()
            },
            "policy": "Freeze before experiments; final test is evaluated only after validation-based candidate selection. Do not tune on test samples.",
        }
        atomic_json(folder / "suite.json", suite)
    return suite


def publish_expansion(name, train, suite, *, notices, provenance, reviewer, store=None):
    store = Path(store or STORE)
    identifier(name)
    suite_folder = store / "evaluation_suites" / suite["id"]
    splits = {
        k: [
            json.loads(line)
            for line in (suite_folder / (k + ".jsonl")).read_text().splitlines()
        ]
        for k in ("validation", "test")
    }
    for k in splits:
        if sha256(suite_folder / (k + ".jsonl")) != suite["files"][k + ".jsonl"]:
            raise ValueError("Held-out file integrity mismatch")
    protected = splits["validation"] + splits["test"]
    sources = {d["source_id"] for d in protected}
    keys = {canonical(d["text"]) for d in protected}
    grams = set().union(*(shingles(d["text"]) for d in protected))
    seen = set()
    inverted = {}
    accepted = []
    shingle_sets = []
    rejected = Counter()
    for d in sorted(train, key=lambda d: (d["source_id"], d["sha256"])):
        if d["source_id"] in sources:
            rejected["heldout_source"] += 1
            continue
        key = canonical(d["text"])
        g = shingles(d["text"])
        if SECRET.search(d["text"]):
            rejected["sensitive_pattern"] += 1
            continue
        if key in keys or g & grams:
            rejected["heldout_contamination"] += 1
            continue
        if key in seen:
            rejected["exact_duplicate"] += 1
            continue
        # Exact inverted index: a >0.85 Jaccard duplicate must share a shingle.
        candidates = set().union(*(inverted.get(x, set()) for x in g)) if g else set()
        if any(
            len(g & shingle_sets[i]) / len(g | shingle_sets[i]) > 0.85
            for i in candidates
        ):
            rejected["near_duplicate"] += 1
            continue
        index = len(shingle_sets)
        shingle_sets.append(g)
        seen.add(key)
        accepted.append(d)
        for token in g:
            inverted.setdefault(token, set()).add(index)
    if not accepted:
        raise ValueError("No clean training documents remain")
    splits = {"train": accepted, **splits}
    identity = {
        "pipeline": PIPELINE,
        "documents": {k: [d["sha256"] for d in v] for k, v in splits.items()},
        "suite_version": suite["version"],
        "provenance": provenance,
        "notices": notices,
        "reviewer": reviewer,
    }
    version = hashlib.sha256(json.dumps(identity, sort_keys=True).encode()).hexdigest()
    dataset_id = identifier(name + "-" + version[:12])
    folder = store / "datasets" / dataset_id
    with lock(store / ".datasets.lock"):
        if (folder / "manifest.json").exists():
            return load_dataset(dataset_id, store)[0]
        folder.mkdir(parents=True, exist_ok=False)
        files = {}
        for split, items in splits.items():
            p = folder / (split + ".jsonl")
            p.write_text(
                "".join(json.dumps(d, ensure_ascii=False) + "\n" for d in items)
            )
            files[p.name] = sha256(p)
        report = {
            "input_train_documents": len(train),
            "accepted_train_documents": len(accepted),
            "rejected": dict(rejected),
            "split_documents": {k: len(v) for k, v in splits.items()},
            "split_sources": {
                k: sorted({d["source_id"] for d in v}) for k, v in splits.items()
            },
            "train_heldout_exact_overlap": 0,
            "train_heldout_12word_overlap": 0,
            "near_duplicate_threshold": 0.85,
            "chars": {k: sum(len(d["text"]) for d in v) for k, v in splits.items()},
        }
        manifest = {
            "id": dataset_id,
            "name": name,
            "version": version,
            "pipeline": PIPELINE,
            "approved": True,
            "license": "PSF-2.0",
            "provenance": provenance,
            "reviewer": reviewer,
            "notices": notices,
            "evaluation_suite": {
                "id": suite["id"],
                "version": suite["version"],
                "files": suite["files"],
            },
            "documents": sum(map(len, splits.values())),
            "files": files,
            "quality": report,
        }
        atomic_json(folder / "quality.json", report)
        atomic_json(folder / "manifest.json", manifest)
    return manifest


def expand(catalog_path, base_id, *, approve=False, store=None):
    store = Path(store or STORE)
    acquisition, raw, notices = download_reviewed(catalog_path, approve, store)
    catalog = acquisition["catalog"]
    base, documents = load_dataset(base_id, store)
    test = []
    extra = []
    held_sources = {}
    for source in acquisition["sources"]:
        if source.get("role") == "license":
            continue
        records = list(extracted(source, raw[source["id"]]))
        if source["split"] == "test":
            test.extend(records)
            held_sources[source["id"]] = source["sha256"]
        elif source["split"] == "train":
            extra.extend(records)
        elif source["split"] == "validation":
            held_sources[source["id"]] = source["sha256"]
    # Preserve original validation documents exactly. Legacy controlflow test is never trained on.
    suite = freeze_suite(
        catalog["suite_id"],
        documents["validation"],
        test,
        notices=notices,
        sources=held_sources,
        store=store,
    )
    baseline = publish_expansion(
        "phase3-base",
        documents["train"],
        suite,
        notices=notices,
        provenance="Phase2 approved training sources with protected Phase3 holdouts; legacy test excluded.",
        reviewer=catalog["reviewer"],
        store=store,
    )
    expanded = publish_expansion(
        "phase3-expanded",
        documents["train"] + extra,
        suite,
        notices=notices,
        provenance=catalog["provenance"],
        reviewer=catalog["reviewer"],
        store=store,
    )
    result = {
        "base_dataset": baseline["id"],
        "expanded_dataset": expanded["id"],
        "suite": {k: v for k, v in suite.items() if k != "notices"},
        "base_quality": baseline["quality"],
        "expanded_quality": expanded["quality"],
        "acquisition_sources": acquisition["sources"],
        "bytes": acquisition["downloaded_or_cached_bytes"],
    }
    atomic_json(store / "phase3-data.json", result)
    return result


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--catalog", required=True)
    p.add_argument("--base", required=True)
    p.add_argument("--approve-download", action="store_true")
    a = p.parse_args()
    print(json.dumps(expand(a.catalog, a.base, approve=a.approve_download), indent=2))
