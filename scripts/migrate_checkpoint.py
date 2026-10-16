import argparse, json
from nexora.research import fork_checkpoint

p = argparse.ArgumentParser(
    description="Non-destructively fork a verified v2/v3 checkpoint for the v3 trainer"
)
p.add_argument("parent_run")
p.add_argument("--id")
a = p.parse_args()
print(json.dumps(fork_checkpoint(a.parent_run, a.id), indent=2))
