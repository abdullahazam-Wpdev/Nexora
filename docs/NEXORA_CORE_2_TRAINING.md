# NEXORA Core Phase10 bounded training

Two random-initialized80-step pilots,2 CPU threads,96dim/2layers/4heads/context192,
completion-only loss,AdamW0.002,seed42. Original selected checkpoint unchanged.

| Run | Parameters | Validation loss | Held-out perplexity | Schema/tool identity | Exact args | Instruction exact | Train s | Peak RSS MiB |
|---|---:|---:|---:|---|---|---|---:|---:|
| phase10-narrow-80 | 329184 | 1.431816 | 12.435087 | 8/8 | 0/8 | 4/24 | 4.880 | 312.58 |
| phase10-diverse-80 | 332256 | 1.405022 | 3.511444 | 8/8 | 0/8 | 4/24 | 3.565 | 311.89 |

Narrow training uses8 deduplicated examples; diverse uses96. Validation24/test32 have
disjoint parameter ranges and exact prompts; both trials share identical test requests.
Both use the same generated families, so semantic/template overlap remains. Independent
train-only tokenizers produce different vocabularies/parameter totals, so cross-run loss
is not directly comparable. Eight tool cases cover only calculator/read_file, not11tools.
Four exact instruction responses are repeated permission refusals; inspect per-case evidence.
All8 tool argument sets are wrong. No professional reasoning or broad instruction claim.

Original deterministic project fixtures,CC0-1.0,owner-authorized Phase10 research,source
IDs/licenses/revisions/approval/splits in each private dataset manifest. Exact dedup and
cross-split prompt checks run before training. No service outputs or external weights.
Maximum80steps/45s/650MiB process guard and500MiB available floor; no promotion.
Dataset/tokenizer/safetensors/result paths: artifacts/instruction-pilots/phase10-narrow-80/
and phase10-diverse-80/. Loaded saved tensors exactly match originals.

Selected984192parameter checkpoint independently reloaded: validation loss4.403331668723, test loss4.178615570217, test perplexity65.275421392744. Full3777/12809 targets; exp(loss) verified.
Selected language perplexity and synthetic instruction perplexity are different tasks.
Changing training code invalidates the existing exact-code resume gate; retain old commit
for prior-run resumption or fork a new run. Checkpoint inference compatibility is retained.

Experiment-time source snapshot: evidence/phase10/training-source.py, matching the actual recorded code SHA. Later formatting/denominator print fixes are not represented as unchanged bytes.
