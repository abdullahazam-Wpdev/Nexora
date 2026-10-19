# Instruction and tool-use pilots

All runs are independently initialized Core models, not external fine-tuning.
Selected Core is unchanged and no candidate is promoted.

| Pilot | Parameters | Steps | Completion targets trained | Validation loss | Test PPL | Tool identity | Exact tool+arguments | Exact instruction |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Original 8-tool design, balanced 80 steps | 336,864 | 80 | 3,200 | 0.384926 | 1.332723 | 5/16 | Empty arguments only | Not measured |
| Mixed instructions/arguments v1 | 387,552 | 80 | Recorded in JSON | 0.133386 | 32.809945 | 1/11 | 0/11 | 0/8 |
| Mixed explicit-parameter v2 | 387,552 | 80 | 3,649 | 0.111071 | 28.345566 | 5/11 | 1/11 | 0/8 |

The old 16-case tool target **did not improve beyond Phase 8's 6/16**. V2's
5/11 and Phase 8's 6/16 use different tasks/schemas and cannot be compared as one
accuracy metric. V1 omitted some required argument values from its requests;
V2 explicitly supplies those values, correcting underspecified supervision.
This changes the input protocol and makes argument copying feasible, so the
1/11→5/11 tool-choice difference is not clean evidence of general intelligence
improvement. V2 has 5/11 strict schemas but only 1/11 complete correct argument
objects. General exact instruction behavior remains 0/8.

Training-only times: tool-80 **2.229 s**, mixed-v1 **3.906 s**, mixed-v2 **3.712 s**.
V2 used **7.069 CPU s**, about **983 supervised tokens/s**, monitored peak RSS
**351.07 MiB**, maximum sampled CPU temperature **68°C**. V1 peak RSS was
373.21 MiB. V2 ran alongside the small reference tool probe; timing differences
must not be interpreted as a controlled throughput gain. All budgets remained
short and per-process monitored. Total padded positions are not supervised tokens.

The explicit repeat reproduced every checkpoint tensor and dataset hash. Its
model SHA-256 is `2d3c2710b0bb73fa3c09b8539675929f69b5b77ac7a8d9a9c4e1204a4094a14e`.
Exact run resources, raw generations, code/data/checkpoint identities and repeat
records are in evidence/phase9/. Checkpoints/tokenizers/manifests remain under
`artifacts/instruction-pilots/phase9-mixed-*` and `artifacts/tool-sft/phase9-tool-80`.
These masked perplexities are not comparable to selected Core pretraining PPL.
