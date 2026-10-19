# Bounded task execution

Two durable engines share the principle that model output proposes work and
independent checks determine success:

| Engine | Lifecycle | Artifacts and limits |
| --- | --- | --- |
| Python coding | inspect → structured plan/constraints → optional public reference → model proposal → isolated test → diff review → exact apply approval | `agent-tasks/`, 90 seconds, two attempts, 24 recorded tool/stage actions, 10-second sandbox attempt |
| Browser | request → fixed dependency plan → exact plan approval → navigation/actions/observations → DOM assertion → screenshot → report | `computer-tasks/`, 35 seconds, five-second actions, two approved attempts |

Coding source registration authorizes inspection of a designated project; only
approval of the verified candidate hash allows one atomic original-file replace.
Original source is retained for rollback. Browser approval applies only to the
visible fixed plan. Neither engine exposes host shell execution or lets retrieved
content grant permissions. The runtime roles are deterministic planner,
researcher, tester and reviewer stages around one proposer model; they are not
five independently intelligent model instances.

Persistence uses atomic JSON and local locks. Coding recovery retains the
previous apply journal and original hash checks. Browser recovery detects dead
workers and requires a new approval for replay. Cancellation is cooperative;
in-flight bounded model/network/browser calls may finish before it is observed.
Resource/time limits are per operation/profile, not a global distributed scheduler.
Retries and tool budgets do not imply guaranteed successful problem solving.

Experimental `prompt_style: concise` is available in the Code panel/API for
SmolLM2; default remains `standard`. It reduces context/output caps to 768/128,
retains source and a short failure message, and does not include the full
retrieved documentation in its tiny prompt. Research evidence is retained
separately. Sandbox, acceptance checks and approval rules are unchanged.
