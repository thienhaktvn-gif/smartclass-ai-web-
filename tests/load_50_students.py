"""Isolated 50-student two-phase concurrency test. Never targets production.

Usage: SANGGIAO_TEST_POSTGRES_URL=postgresql://... python tests/load_50_students.py
"""
import concurrent.futures
import json
import os
import statistics
import threading
import time
import uuid
from http.server import ThreadingHTTPServer
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from pathlib import Path
import tempfile
import app

STUDENTS=50
TIMEOUT=65

def request(base,path,payload=None,cookie=None,csrf=None):
 headers={}
 if payload is not None:headers['Content-Type']='application/json'
 if cookie:headers['Cookie']=cookie
 if csrf:headers['X-CSRF-Token']=csrf
 req=Request(base+path,data=json.dumps(payload,ensure_ascii=False).encode('utf-8') if payload is not None else None,headers=headers)
 started=time.perf_counter()
 try:
  with urlopen(req,timeout=TIMEOUT) as response:
   data=json.loads(response.read())
   return {'status':response.status,'data':data,'duration':round(time.perf_counter()-started,3),'cookies':response.headers.get('Set-Cookie')}
 except HTTPError as e:
  return {'status':e.code,'data':e.read().decode('utf-8','replace')[:240],'duration':round(time.perf_counter()-started,3)}
 except Exception as e:
  return {'status':0,'data':type(e).__name__+': '+str(e)[:180],'duration':round(time.perf_counter()-started,3)}

def wave(items,fn):
 barrier=threading.Barrier(len(items))
 def worker(item):
  try:barrier.wait(timeout=10)
  except threading.BrokenBarrierError:pass
  return item,fn(item)
 with concurrent.futures.ThreadPoolExecutor(max_workers=len(items)) as pool:
  futures=[pool.submit(worker,i) for i in items]
  return dict(f.result() for f in concurrent.futures.as_completed(futures))

def summary(name,data):
 latencies=[v['duration'] for v in data.values()]
 failures={k:{'status':v['status'],'response':str(v['data'])[:180]} for k,v in data.items() if v['status']!=200}
 ordered=sorted(latencies)
 metric={'phase':name,'requested':len(data),'success':len(data)-len(failures),
  'failed':len(failures),'p50_s':round(statistics.median(latencies),3),
  'p95_s':ordered[min(len(ordered)-1,int(len(ordered)*.95))],
  'max_s':max(latencies),'failure_examples':list(failures.items())[:8]}
 print('LOAD_50_RESULT '+json.dumps(metric,ensure_ascii=False),flush=True)
 return failures

def main():
 os.environ['SMARTCLASS_STORAGE_BACKEND']='postgres'
 url=os.environ.get('SANGGIAO_TEST_POSTGRES_URL')
 if not url:raise RuntimeError('Requires isolated SANGGIAO_TEST_POSTGRES_URL, never DATABASE_URL for production.')
 os.environ['DATABASE_URL']=url
 name='load_'+uuid.uuid4().hex[:12]
 app.ADMIN_USER='load_admin';app.ADMIN_PASSWORD='LoadAdminPassword123'
 app.TENANT.set(None);app.init()
 with app.db() as c:
  c.execute('INSERT INTO users(username,password_hash,role) VALUES(?,?,?)',(name,app.hashpw('LoadTeacherPassword123'),'teacher'))
 app.TENANT.set(app.tenant_for(name));app.init();app.TENANT.set(None)
 class TestServer(ThreadingHTTPServer):
  request_queue_size=128
 server=TestServer(('127.0.0.1',0),app.H)
 thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
 base='http://127.0.0.1:'+str(server.server_port)
 try:
  login=request(base,'/api/login',{'username':name,'password':'LoadTeacherPassword123','portal':'teacher'})
  assert login['status']==200,login
  cookie=login['cookies'].split(';',1)[0];csrf=login['data']['csrf']
  questions=[{'content':'Câu hỏi kiểm thử đồng thời số '+str(i)+'?', 'options':{'A':'Phương án A','B':'Phương án B','C':'Phương án C','D':'Phương án D'},'answer':'B'} for i in range(1,21)]
  publish=request(base,'/api/exams/word/publish',{'title':'Kiểm thử 50 học sinh','items':questions,'subject':'Tin học','grade':'9','duration':20},cookie,csrf)
  assert publish['status']==201,publish
  eid=publish['data']['id']
  share=request(base,'/api/online/share',{'exam_id':eid},cookie,csrf)
  assert share['status']==200,share
  code=share['data']['exam_code']
  ids=list(range(1,STUDENTS+1))
  started=wave(ids,lambda i:request(base,'/api/online/start',{'exam_code':code,'student_name':f'Học sinh thử {i:03d}','student_code':f'HS{i:03d}'}))
  start_fail=summary('start',started)
  # Every student answers every question, concurrently.
  tokens={i:result['data']['attempt_token'] for i,result in started.items() if result['status']==200}
  item_forms={i:result['data']['items'] for i,result in started.items() if result['status']==200}
  def submit(i):
   answers={str(q['id']):'A' for q in item_forms[i]}
   return request(base,'/api/online/submit',{'attempt_token':tokens[i],'answers':answers})
  submitted=wave(list(tokens),submit) if tokens else {}
  submit_fail=summary('submit',submitted) if submitted else {'none':'No successful starts'}
  results=request(base,f'/api/online/results?exam_id={eid}',cookie=cookie)
  count=len(results['data'].get('items',[])) if results['status']==200 else -1
  print('LOAD_50_FINAL '+json.dumps({'entered':len(tokens),'submitted':len(submitted)-len(submit_fail),
    'graded_rows':count,'unique_codes':len({r['student_code'] for r in results['data'].get('items',[])}) if results['status']==200 else 0,
    'database':'isolated local PostgreSQL','production_touched':False},ensure_ascii=False),flush=True)
  if start_fail or submit_fail or count!=STUDENTS:
   raise AssertionError(f'50 concurrent students NOT fully successful: starts failed={len(start_fail)}, submits failed={len(submit_fail)}, persisted={count}/{STUDENTS}')
 finally:
  server.shutdown();server.server_close();thread.join(timeout=6)

if __name__=='__main__':main()
