import json
import logging
import sqlite3
import subprocess
import sys
import threading
from contextlib import contextmanager
from pathlib import Path
import psutil
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from nexora.config import ROOT, STORE
from nexora.datasets import prepare

log=logging.getLogger('nexora')
app=FastAPI(title='NEXORA AI OS',version='0.1.0')
@contextmanager
def db():
    con=sqlite3.connect(STORE/'nexora.db')
    con.row_factory=sqlite3.Row
    con.execute('PRAGMA foreign_keys=ON')
    try:
        yield con
        con.commit()
    finally: con.close()
with db() as con: con.executescript((ROOT/'migrations/001_initial.sql').read_text())

def audit(action,detail):
    with db() as con: con.execute('INSERT INTO audit(actor,action,detail) VALUES(?,?,?)',('local-owner',action,detail))

@app.middleware('http')
async def local_write_guard(request:Request,call_next):
    # Browser mutations must originate from this local UI or direct CLI clients.
    if request.method in {'POST','PUT','PATCH','DELETE'}:
        origin=request.headers.get('origin')
        if origin and origin not in {'http://127.0.0.1:3000','http://localhost:3000','http://127.0.0.1:8000','http://localhost:8000'}:
            from fastapi.responses import JSONResponse
            return JSONResponse({'detail':'Untrusted browser origin'},status_code=403)
    return await call_next(request)

@app.get('/api/health')
def health():
    vm=psutil.virtual_memory(); disk=psutil.disk_usage(str(STORE))
    return {'status':'ok','cpu_percent':psutil.cpu_percent(),'threads':psutil.cpu_count(),'memory_total':vm.total,'memory_available':vm.available,'disk_total':disk.total,'disk_free':disk.free,'storage_path':str(STORE),'device':'CPU','database':'SQLite','podman':'not installed in this environment'}

@app.get('/api/experiments')
def experiments():
    return [json.loads(p.read_text()) for p in STORE.glob('*/result.json')]

@app.get('/api/datasets')
def datasets():
    items=[]
    for p in STORE.glob('*/dataset.json'):
        d=json.loads(p.read_text());d.pop('splits',None);items.append({'id':p.parent.name,**d})
    with db() as con:
        items.extend({'id':r['id'],**json.loads(r['manifest'])} for r in con.execute('SELECT * FROM datasets'))
    return items

class DatasetInput(BaseModel):
    name:str=Field(min_length=1,max_length=80,pattern=r'^[a-zA-Z0-9_-]+$')
    texts:list[str]=Field(min_length=10,max_length=1000)
    approved:bool=False
    license:str
    provenance:str=Field(max_length=2000)
@app.post('/api/datasets',status_code=201)
def ingest(body:DatasetInput):
    if sum(map(len,body.texts))>1_000_000: raise HTTPException(413,'Dataset exceeds local ingestion limit')
    try: manifest=prepare(body.texts,approved=body.approved,license=body.license,provenance=body.provenance)
    except ValueError as e: raise HTTPException(422,str(e))
    try:
        with db() as con: con.execute('INSERT INTO datasets(id,manifest) VALUES(?,?)',(body.name,json.dumps(manifest)))
    except sqlite3.IntegrityError: raise HTTPException(409,'Dataset name already exists')
    audit('dataset.ingest',body.name)
    return {'id':body.name,'documents':manifest['documents']}

class Generation(BaseModel):
    prompt:str=Field(min_length=1,max_length=256)
    max_tokens:int=Field(default=32,ge=1,le=64)
@app.post('/api/generate')
def generate(body:Generation):
    if not (STORE/'tiny-core/result.json').exists(): raise HTTPException(409,'Train the tiny model first')
    from nexora.train import infer
    return infer(body.prompt,body.max_tokens)

training_lock=threading.Lock()
process=None
class Training(BaseModel):
    steps:int=Field(default=160,ge=1,le=500)
    resume:bool=False
@app.get('/api/training')
def training_status():
    return {'running':process is not None and process.poll() is None}
@app.post('/api/training',status_code=202)
def train(body:Training):
    global process
    with training_lock:
        if process is not None and process.poll() is None: raise HTTPException(409,'A training job is already running')
        if body.resume and not (STORE/'tiny-core/resume.pt').exists(): raise HTTPException(409,'No resumable checkpoint')
        if psutil.virtual_memory().available<500*1024**2: raise HTTPException(409,'Less than 500 MiB RAM available')
        args=[sys.executable,'-m','nexora.train','--steps',str(body.steps)]
        if body.resume: args.append('--resume')
        with open(STORE/'training.log','a') as out:
            process=subprocess.Popen(args,cwd=ROOT,stdout=out,stderr=subprocess.STDOUT)
        audit('training.start',json.dumps(body.model_dump()))
        return {'status':'started','pid':process.pid}

@app.get('/api/projects')
def projects():
    with db() as con:return [dict(r) for r in con.execute('SELECT * FROM projects')]
class Memory(BaseModel):
    content:str=Field(min_length=1,max_length=4000)
@app.get('/api/memory')
def memory():
    with db() as con:return [dict(r) for r in con.execute('SELECT * FROM memory ORDER BY id DESC LIMIT 100')]
@app.post('/api/memory',status_code=201)
def add_memory(body:Memory):
    with db() as con:
        cursor=con.execute('INSERT INTO memory(project_id,content) VALUES(?,?)',('local',body.content));ident=cursor.lastrowid
    audit('memory.create',str(ident));return {'id':ident}
@app.get('/api/audit')
def events():
    with db() as con:return [dict(r) for r in con.execute('SELECT * FROM audit ORDER BY id DESC LIMIT 100')]
@app.get('/api/integrations')
def integrations():
    return [{'provider':'NEXORA Core','purpose':'local inference','status':'local','cost':'free','permissions':'local model artifacts','authentication':'localhost only'}, {'provider':'External APIs','status':'not configured','cost':'none incurred','permissions':'none granted','authentication':'future environment variables'}]
