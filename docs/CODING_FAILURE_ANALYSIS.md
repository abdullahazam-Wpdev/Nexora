# Coding failure analysis

Original requests, provider names, retries, model outputs/test events and source
backups remain under artifacts/agent-tasks and workspace-code. Phase 9's public
fixture records include baseline.json, coding-*.json and html-rescore.json.
Earlier Phase 8 invalid syntax outputs were not always retained as complete
files; where unavailable they cannot be reconstructed honestly. New attempts
retain proposal-N files before syntax validation, including rejected candidates.

| First incorrect decision | Evidence | Targeted change |
| --- | --- | --- |
| Overloaded prompt/irrelevant imports | SmolLM2 wrong signatures, nonexistent math.add, recursion | Preserve concise opt-in; compare to standard, do not assume role superiority |
| Tiny context truncation loses goal | Original legacy prompt took the last 5,000 characters | Reject over-budget selected source explicitly rather than silently removing the goal |
| Wrong patch JSON shape | Qwen emitted `files:{path:solution.py}` | Server-built allowed-path JSON schema, independent patch/path validation |
| Incomplete function body or unchanged buggy source | Qwen emitted return statements or copied input | Syntax/profile validation, no-change rejection and actual hidden acceptance |
| Repeated oversized prefill/structured workloads | Cgroup OOM under 900 MiB | Smaller batch/context/output, measured owner-approved larger-cap study; quarantine after repeated failures |
| Vacuous acceptance test | Plain `Name` text passed an assertion that only checked encountered labels | Require both label and input; independently rerun stored candidates; remove false pass |
| Private Flatpak /tmp invisible to host Podman | Initial new tests could not mount fixtures | Bounded symlink-free copy to shared artifact staging; readable permissions; cleanup after execution |
| Stale/partial multi-file apply | Crash/concurrent-owner-edit risk | Intent journal, per-file source check, rollback touched files, preserve conflicting owner edits |

The simpler single-file full-source protocol is supported when only one file is
in scope; multiple files retain explicit JSON maps. This was selected from the
existing development/regression behavior, not by adding task-specific expected
answers. Repeated mixed-suite measurements are post-diagnostic regressions,
**not pristine untouched final evaluations**. Their broader score remains poor.
No prompt was supplied the acceptance code/control patch, and no model-generated
shell command executes on the host.

Failing candidates never edit registered originals. Only verified candidates with
an exact approved hash apply. Supplied controls are labeled separately. Multi-file
apply is a recoverable journaled operation, not an OS-atomic transaction spanning
several paths. A conflicting external edit triggers rollback/manual review.
