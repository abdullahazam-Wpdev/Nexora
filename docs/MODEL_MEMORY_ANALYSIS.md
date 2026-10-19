# Model memory analysis

Measured physical RAM: 8,030,429,184 bytes (7.4789 GiB), four physical/eight logical CPUs,
no dedicated NVIDIA GPU. Initial available RAM 1,162,104,832 bytes; swap almost fully
used. RAM is not 32 GB. Do not infer memory headroom from installed swap.

Phase9's approved 1152MiB Qwen run **completed**. Three 900MiB runs OOMed. Its
397,821,516-byte Q4_K_M weights do not equal runtime RAM. Verified model metadata:
24 layers, dimension896,14 attention heads,2 KV heads, head dimension64. An f16 KV
estimate at512 tokens is 2*24*512*2*64*2 = 6,291,456 bytes; at1024 it is12,582,912.
KV alone does not explain the cap hit. Earlier observed compute buffers approximately
298.5MiB, model mappings/cache, allocator/backend and service overhead also contribute.
We cannot isolate fragmentation as a cause or prove all prior background concurrency
absent. The direct failure evidence is service cgroup OOM under900MiB. Increasing the
cap did not establish sustained operation under the normal limit. No repeat OOM trial.

Current Smol run: sampled host Ollama/runner RSS sum peak
**377,528,320 bytes**; service cgroup lifetime peak
492,204,032 bytes (including cache and earlier requests). Service MemoryMax943,718,400,
MemorySwapMax0, CPU quota200%, one model, keepalive0, two inference threads,context768,
num_batch16. Host ps sampling fixes the prior Flatpak-zero-RSS reporting mistake.
Sampling began after evaluation start; RSS sum may double-count shared pages. This
is neither PSS nor isolated model allocation. Full samples/swap/available RAM in
inference-memory.json. Background swap changes do not prove model swap use (service
swap is disabled). Median decode 84.64 tokens/s, first delta 0.771s,26 calls.

`compute_budget.py` uses a nonblocking flock shared across processes and500MiB
available-memory admission floor. Research/legacy/tool/instruction training and
managed Core/reference/sidecar/shared assistant calls participate. Legacy coding now
uses the same pinned reference adapter. Direct external Ollama/FCC clients are outside
this application's admission gate; do not run them alongside training. Running a
training job causes new managed inference to return429; low memory returns503.
These are admission/step checks, not a total-system RAM guarantee or thermal daemon.
