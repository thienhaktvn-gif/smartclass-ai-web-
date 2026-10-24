"""HTTP regression for incremental, idempotent 16-subject demo seeding.
All writes use a disposable SQLite database; production is untouched.
"""
import json
import tempfile
import threading
import unittest
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request,urlopen
import app
from bank16 import FACTS

class Bank16HttpTest(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory()
  self.original=(app.DB,app.TENANT_DIR,app.ADMIN_USER,app.ADMIN_PASSWORD)
  app.DB=Path(self.temp.name)/'main.sqlite'
  app.TENANT_DIR=Path(self.temp.name)/'tenants'
  app.TENANT_DIR.mkdir()
  app.ADMIN_USER='teacher_sample'
  app.ADMIN_PASSWORD='test-only-pass'
  app.TENANT.set(None)
  app.init()
  self.server=ThreadingHTTPServer(('127.0.0.1',0),app.H)
  self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
  self.thread.start()
  status,login,cookie=self.call('/api/login',{'username':'teacher_sample','password':'test-only-pass'})
  self.assertEqual(status,200,login)
  self.cookie=cookie.split(';',1)[0]
  self.csrf=login['csrf']

 def tearDown(self):
  self.server.shutdown()
  self.server.server_close()
  self.thread.join(timeout=3)
  app.DB,app.TENANT_DIR,app.ADMIN_USER,app.ADMIN_PASSWORD=self.original
  app.TENANT.set(None)
  self.temp.cleanup()

 def call(self,path,data=None,auth=False):
  headers={}
  if data is not None:headers['Content-Type']='application/json'
  if auth:
   headers['Cookie']=self.cookie
   headers['X-CSRF-Token']=self.csrf
  request=Request('http://127.0.0.1:'+str(self.server.server_port)+path,
                  data=json.dumps(data).encode() if data is not None else None,
                  headers=headers)
  try:
   with urlopen(request,timeout=20) as response:
    return response.status,json.load(response),response.headers.get('Set-Cookie','')
  except HTTPError as error:
   return error.code,json.load(error),''

 def test_chunked_seed_and_repeat_is_safe(self):
  subjects=list(FACTS)
  self.assertEqual(len(subjects),16)
  for subject in subjects:
   code,reply,_=self.call('/api/bank16/seed',{'subject':subject},True)
   self.assertEqual(code,200,reply)
   self.assertEqual(reply['created']['questions'],16)
   self.assertEqual(reply['created']['essays'],3)
   self.assertEqual(reply['created']['draft_exams'],1)
  for subject in subjects:
   code,reply,_=self.call('/api/bank16/seed',{'subject':subject},True)
   self.assertEqual(code,200,reply)
   self.assertTrue(reply['already'])
   self.assertEqual(reply['created']['questions'],0)
  app.TENANT.set(app.tenant_for('teacher_sample'))
  try:
   with app.db() as conn:
    self.assertEqual(conn.execute('SELECT COUNT(*) FROM questions WHERE origin=?',('demo-16x19',)).fetchone()[0],256)
    self.assertEqual(conn.execute('SELECT COUNT(*) FROM essay_questions WHERE origin=?',('demo-16x19',)).fetchone()[0],48)
    self.assertEqual(conn.execute('SELECT COUNT(*) FROM exams WHERE published=0 AND title LIKE ?',('%[MINH HỌA]',)).fetchone()[0],16)
  finally:app.TENANT.set(None)

 def test_missing_subject_rejected(self):
  code,_,_=self.call('/api/bank16/seed',{},True)
  self.assertEqual(code,400)
  code,_,_=self.call('/api/bank16/seed',{'subject':'unlisted'},True)
  self.assertEqual(code,400)

 def test_unauthenticated_seed_denied(self):
  code,_,_=self.call('/api/bank16/seed',{'subject':'Toán'})
  self.assertIn(code,(401,403))

if __name__=='__main__':unittest.main()
