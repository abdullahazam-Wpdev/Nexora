# Phase 8 reliability and permission checks

Existing boundary tests cover registered paths/symlinks, strict Python AST
profile, rootless networkless Podman, owner approval hashes, changed-source
rejection, cancellation, checkpoint integrity/recovery, hosted consent and
separate memory namespaces. Phase 8 adds real isolated-form browser execution,
plan tamper rejection, wrong approval/cancel rejection, interrupted PID recovery,
private/metadata/file/credential URL rejection, screenshot SHA-256 verification,
FTS namespace separation, document deletion/deduplication and training shape caps.

Retrieved text is never parsed into additional browser tools: the fixed plan is
owner-reviewed and hash-bound. Coding output remains subject to AST validation,
networkless sandbox assertions and exact apply approval. This architecture limits
what injected instructions could execute; tests do not prove universal resistance
to prompt injection or semantic deception by arbitrary models/pages.

Browsers are fresh contexts, not personal profiles. Interactive access is only
the fixed test page. API endpoints bind localhost and are intended for a trusted
single owner, not public/multi-user hosting. Browser process memory has measured
monitoring and available-RAM checks, not a hard cgroup ceiling. URL checks remain
susceptible to DNS rebinding/time-of-check limitations; do not expose this API to
untrusted networks. Cancellation waits for bounded in-flight actions. Local
artifacts are not encrypted. Global API rate limiting/authentication is not added;
existing inference gates and per-task budgets do not replace it.

No NVIDIA hosted call ran, no account login or personal Chrome profile was used,
no money was spent and no external model weights were added during Phase 8.
Published evidence consists only of reviewed authored fixtures, source references
and measured pilot results. Private SQLite state and checkpoints remain ignored.
