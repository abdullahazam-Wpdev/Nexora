import importlib
import pytest
from fastapi.testclient import TestClient
@pytest.fixture
def client(tmp_path,monkeypatch):
    import nexora.config as config
    monkeypatch.setattr(config,'STORE',tmp_path)
    import nexora.api as api
    importlib.reload(api)
    return TestClient(api.app)

def test_health_projects_and_memory(client):
    assert client.get('/api/health').json()['status']=='ok'
    assert client.get('/api/projects').json()[0]['id']=='local'
    assert client.post('/api/memory',json={'content':'Reproduce experiments before promoting checkpoints.'}).status_code==201
    assert len(client.get('/api/memory').json())==1
    assert client.get('/api/audit').json()[0]['action']=='memory.create'

def test_origin_and_inference_guards(client):
    assert client.post('/api/memory',headers={'Origin':'https://untrusted.example'},json={'content':'bad'}).status_code==403
    assert client.post('/api/generate',json={'prompt':'hello'}).status_code==409
    assert client.post('/api/generate',json={'prompt':'hello','max_tokens':10000}).status_code==422
    assert client.post('/api/training',json={'resume':True}).status_code==409

def test_dataset_ingestion(client):
    body={'name':'fixture','texts':[f'Unique local numerical fixture document {i}.' for i in range(20)],'license':'CC0-1.0','provenance':'test-owned numerical fixtures','approved':False}
    assert client.post('/api/datasets',json=body).status_code==422
    body['approved']=True
    assert client.post('/api/datasets',json=body).status_code==201
    assert client.post('/api/datasets',json=body).status_code==409
    assert client.get('/api/datasets').json()[0]['documents']==20
