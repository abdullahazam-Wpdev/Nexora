"""Allow REA 6.7.0's demo helper to use the verified project-local Xvfb."""

import hashlib
from pathlib import Path

root = Path(__file__).resolve().parents[1]
helper = root / ".tools/rea/node_modules/rea-agents/scripts/hopper-demo-x11.py"
original = 'parser.add_argument("--xvfb", default="/usr/bin/Xvfb")'
replacement = (
    f'parser.add_argument("--xvfb", default={str(root / ".tools/xvfb/usr/bin/Xvfb")!r})'
)
text = helper.read_text()
if replacement in text:
    print("REA Xvfb path patch already applied")
elif text.count(original) == 1:
    before = hashlib.sha256(helper.read_bytes()).hexdigest()
    if before != "ea5a3cab38843fc5405695de12ae2f711f1d2065ab347096624aab0d6f45e836":
        raise SystemExit("REA helper digest changed; review before patching")
    helper.write_text(text.replace(original, replacement))
    print(f"Patched local Xvfb path; original helper SHA-256: {before}")
else:
    raise SystemExit("Unexpected REA helper; review before patching")
