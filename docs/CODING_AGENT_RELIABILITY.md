# Coding-agent reliability

Scoped existing files now include JSON/YAML/Markdown in addition to Python/JS/TS/PHP
source reads. Execution still requires a reviewed profile; accepting a YAML/PHP path
does not supply its parser/interpreter. No arbitrary host execution or package install.

Optional `patch_format: edits` accepts only1..8 exact replacements: path,old,new.
Every nonempty anchor must occur exactly once in the approved current source; unknown
paths, no-ops and ambiguous anchors fail. UI offers this experimental format explicitly;
default complete-file protocol remains unchanged for the frozen final run. Syntax/profile
checks, bounded feedback/retry and hidden acceptance remain required. JSON is parsed;
Python local imports permit only explicitly scoped top-level module names plus existing
stdlib allowlist, with execution remaining networkless/read-only/rootless.

After exact-hash approval and original-hash checks, journaled multi-file apply now
copies the actual applied scoped files into isolated staging and reruns owner acceptance.
Failure rolls touched files back and records interrupted status. This preserves owner
concurrent edits; a multi-file apply is journaled, not a filesystem-atomic transaction.
Tests cover minimal edits, stale sources, cancellation, partial recovery, concurrent edits,
real sandbox timeout/module imports, post-apply failure rollback and permission rejection.

Real two-file API demonstration is a supplied control, not model-generated intelligence.
Final model task success did not improve: 0 passes on31 fixtures,8 blocked. Keep approvals.
The shared proposer and safe patch machinery cannot manufacture model capability.
