# Controlled improvement

Observed failure → reproducible benchmark/test → proposed code or memory `proposal` → staged experiment → compare measurements → review → owner approval → scoped apply. No unrestricted self-modification, automatic skill activation, permission escalation or weight promotion exists.

This phase used that loop concretely: a 20-case utility benchmark exposed 0% model success despite 100% control-patch success; two completion-only training pilots improved JSON form but not reliable tool choice. Those failures are preserved rather than replaced by optimistic claims. The selected Core checkpoint was not changed.

`nexora-code` and `nexora-project-memory` are new validated project skills with inputs/outputs, permissions, workflow, examples, validation and failure handling. Skills guide agents; they are not neural weights. The runtime can discover skills, while activation of newly proposed executable tools remains a manual, reviewed code change. No unattended deployment or automatic training on task history is implemented.
