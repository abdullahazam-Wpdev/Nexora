import json
import sys
import time
from pathlib import Path

root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root))
from nexora.cowork_sandbox import run_python
from nexora.config import STORE

folder = STORE / "coworkspace"
folder.mkdir(exist_ok=True)
source = folder / "sandbox-verification.py"
source.write_text("""import socket,os
print("answer",6*7)
print("uid",os.getuid())
try:
 socket.create_connection(("1.1.1.1",443),timeout=1)
 print("UNEXPECTED_NETWORK")
except OSError:
 print("network_blocked")
try:
 open("/workspace/unexpected.txt","w").write("bad")
 print("UNEXPECTED_WRITE")
except OSError:
 print("write_blocked")
""")
result = run_python(folder, source)
assert (
    "answer 42" in result
    and "uid 65534" in result
    and "network_blocked" in result
    and "write_blocked" in result
), result
source.write_text("while True: pass\n")
start = time.monotonic()
cancel = run_python(folder, source)
elapsed = time.monotonic() - start
assert "Execution time limit reached" in cancel, cancel
assert elapsed < 25, elapsed
source.unlink()
report = {"normal": result, "time_limit": cancel, "cancellation_seconds": elapsed}
(STORE / "cowork-verification").mkdir(exist_ok=True)
(STORE / "cowork-verification/sandbox.json").write_text(json.dumps(report, indent=2))
print(json.dumps(report, indent=2))
