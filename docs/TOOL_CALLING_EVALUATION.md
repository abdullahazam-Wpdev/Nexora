# Strict tool proposals and evaluation

`nexora/tool_protocol.py` defines eleven registered tools: read/create file,
propose patch, run tests, browse, search, retrieve, calculator, request approval,
refuse and retry. Each has strict typed arguments, required fields, limits and
forbidden extras. Relative paths reject traversal; browser proposals reject
credential/private-literal URLs. A valid proposal always says
`execution_authorized:false`. A request to approve is not an approval.

`/api/tools/validate` checks proposals. `/execute` can perform bounded calculator,
indexed retrieval and read-only file inspection inside an owner-registered
repository, or report refusal. Mutating/test/browser/search/retry proposals must
use the existing scoped workflows; this endpoint does not silently execute them
or grant privileges. There is no shell tool. Network checks still require the
existing browser protections at actual execution time.

The fixed suite has 22 authored requests with explicit supplied parameters;
model output is checked for tool identity, schema and exact arguments without
automatically executing privileged actions. SmolLM2: **0/22** schema/tool success.
Qwen produced only **4 recorded cases**, with **2** valid/correct choices, before
its service hit the normal cap; the other 18 are not run. This incomplete result
is not a 22-case accuracy estimate. Exact four-instruction Qwen probes were
blocked by that failure, not reported as passing or 0/4.

New Core v2 pilot: **5/11** tool identity with strict schema, **1/11** complete
correct argument objects, **0/8** exact instructions. Old 16-case reproduction
and 80-step results are separate protocols. Actual calculator, permission
separation, scoped file rules, missing arguments, unsafe/unregistered tool
rejection and retry limits have deterministic tests. Model policy refusal,
recovery after real errors and unnecessary-call quality are not comprehensively
validated; they remain separate acceptance targets.
