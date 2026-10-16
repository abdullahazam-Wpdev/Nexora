import os
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
STORE = Path(os.environ.get('NEXORA_STORAGE', str(ROOT / 'artifacts'))).expanduser().resolve()
STORE.mkdir(parents=True, exist_ok=True)
