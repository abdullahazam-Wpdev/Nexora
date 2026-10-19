"""Repeat deterministic SFT without overwriting the first public result."""
import json,sys
from pathlib import Path
import torch
from safetensors.torch import load_file
ROOT=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(ROOT))
from nexora.instruction_pilot import run
from nexora.config import STORE
from nexora.artifacts import atomic_json
path=ROOT/'docs/evidence/phase9/instruction-pilot-explicit.json'
original=path.read_bytes()
try:
 result=run('phase9-mixed-explicit-repeat-80',80,True)
 atomic_json(ROOT/'docs/evidence/phase9/instruction-pilot-repeat.json',result)
finally:path.write_bytes(original)
left=load_file(str(STORE/'instruction-pilots/phase9-mixed-explicit-80/model.safetensors'));right=load_file(str(STORE/'instruction-pilots/phase9-mixed-explicit-repeat-80/model.safetensors'))
exact=all(torch.equal(value,right[key]) for key,value in left.items())
report={'all_checkpoint_tensors_identical':exact,'original':json.loads(original)['checkpoint_sha256'],'repeat':result['checkpoint_sha256'],'dataset_identical':json.loads(original)['dataset_sha256']==result['dataset_sha256']}
atomic_json(ROOT/'docs/evidence/phase9/pilot-reproducibility.json',report);print(report)
