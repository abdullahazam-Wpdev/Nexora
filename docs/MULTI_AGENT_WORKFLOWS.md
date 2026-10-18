# Role-based collaboration

Planner → optional Researcher → Coder → Tester → Reviewer → owner approval is a real, persisted workflow. The demonstration includes all five roles, an actual public documentation read, a real local model proposal, real container assertions and a reviewed one-file apply. Role/tool permissions are closed by the implementation, not selected from untrusted Markdown. `GET /api/agent/roles` reports the stages.

Only Coder invokes the shared model backend; Planner, Tester and Reviewer are deterministic orchestration/validation stages. This is deliberately not advertised as five autonomous reasoning agents. The two-attempt, token, time and sandbox budgets prevent unbounded agent loops. No role can promote weights, spend money or execute an arbitrary host command.

The natural-language proposer remains weak: 0/20 on the harder utility benchmark. A stronger verified backend and richer evaluations are required before broadening its permissions.
