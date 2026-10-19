"""Real API streaming and owner-approved multi-file control execution, no private chats."""
import json,sys
from pathlib import Path
import httpx
ROOT=Path(__file__).resolve().parent.parent;sys.path.insert(0,str(ROOT))
from nexora.config import STORE
from nexora.workspace_code import Task,create,execute
from nexora.artifacts import atomic_json
report={}
with httpx.Client(base_url='http://127.0.0.1:8000',timeout=30) as client:
    status=client.get('/api/assistant/status').json();assert status['qwen_enabled'] is False;report['assistant_status']=status
    ident=client.post('/api/cowork/threads').json()['id'];frames=[]
    with client.stream('POST','/api/cowork/threads/'+ident+'/messages/stream',json={'provider':'ollama','text':'Say hello briefly.'}) as response:
        response.raise_for_status()
        for line in response.iter_lines():
            if line.startswith('data: '):frames.append(json.loads(line[6:]))
    assert any(e['type']=='delta' for e in frames)
    final=next(e['result'] for e in frames if e['type']=='result');assert final['role']=='assistant'
    saved=client.get('/api/cowork/threads/'+ident).json();assert saved[-1]['text']==final['text']
    report['streaming']={'delta_frames':sum(e['type']=='delta' for e in frames),'final':final,'persistent':True,'fixture_thread_id':ident}
    repo=STORE/'phase9/api-multi-control';repo.mkdir(parents=True,exist_ok=False)
    (repo/'one.py').write_text('def f(x):return 0\n');(repo/'two.py').write_text('def g(x):return 0\n')
    registered=client.post('/api/agent/repositories',json={'path':str(repo)}).json()
    task=create(STORE,Task(repository_id=registered['id'],files=['one.py','two.py'],goal='Verify the two-file control apply path',acceptance="from pathlib import Path\nns={}\nexec(Path('one.py').read_text(),ns)\nexec(Path('two.py').read_text(),ns)\nassert ns['f'](3)==3 and ns['g'](3)==4",profile='python'))
    result=execute(STORE,task['id'],proposer=lambda *args:{'one.py':'def f(x):return x\n','two.py':'def g(x):return x+1\n'})
    assert result['status']=='awaiting_approval'
    url='/api/workspace-code/tasks/'+task['id']
    assert client.post(url+'/approve',json={'candidate_sha256':'0'*64}).status_code==409
    approved=client.post(url+'/approve',json={'candidate_sha256':result['candidate_sha256']});approved.raise_for_status();assert approved.json()['status']=='completed'
    report['multi_file_control']={'task_id':task['id'],'status':'completed','model_generated':False,'verification':result['verification'],'diff':result['diff'],'wrong_approval_rejected':True}
atomic_json(ROOT/'docs/evidence/phase9/live-integration.json',report)
print('Real token stream persisted; multi-file control tested, wrong hash rejected, approved apply completed')
