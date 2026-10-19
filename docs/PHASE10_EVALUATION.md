# Phase10 evaluation

Starting baseline:107 tests passed18.94s; final116 tests passed32.14s.
Ruff F checks,pip check,frontend typecheck and production build passed.
No npm lint script exists; that command is unavailable, not passed.

| Acceptance area | Evidence/result |
|---|---|
| Physical RAM | 7.4789GiB measured; initial swap nearly full |
| Selected Core | 984192params, strict checkpoint load, validation4.403331668723472, test perplexity65.27542139274378, exp(loss) verified |
| Sustainable reference |26 Smol generation calls,900MiB cap,no observed OOM; weak model, not professional |
| New final coding |0 passed,23 failed,8 blocked of31 after saved-proposal rescore |
| Runtime controls |23 passed;3 TS controls failed profile budget;5 unsupported profiles |
| Minimal multi-file control |Real Podman tests, exact approval, post-apply retest; supplied control, not model success |
| Rollback and security |Stale/cancelled approval, owner conflicts, partial recovery, failed applied-tree rollback, real timeout, scoped imports and strict schemas covered |
| Public research |Real GitHub search→3 isolated browser reads→3 intact-hash literal citations; no proprietary scraping |
| Answer support gate |20/20 deterministic fixtures;12 deliberately unsupported rejected; not semantic truth/hallucination rate |
| Bounded training |2 independent80-step pilots; each8/8 tool identities,0/8 exact args,4/24 instructions; no promotion |
| Hosted generation |Blocked: NVIDIA key not configured; public catalog reachable |
| Stronger local assistant |Blocked: no demonstrated capable candidate under normal limit; Qwen remains disabled |
| Frontend |Minimal-edit option, disabled Qwen, corrected Phase10 counts and Library browser checks passed |

Raw events,timing,model IDs,hashes and negative outcomes are under evidence/phase10.
No regenerated proposals were used after discovering Python import-path harness failure.
Three TS harness failures remain blocks. A final benchmark now consumed is not reusable
for tuning. No claim of coding improvement, broad instruction following, factual
citation accuracy, perfect OOM protection or autonomous professional task completion.
