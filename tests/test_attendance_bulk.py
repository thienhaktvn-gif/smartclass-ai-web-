"""Test atomic attendance save and idempotent update with disposable SQLite."""
import json
import tempfile
import threading
import unittest
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import app

class AttendanceBulkTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.orig=(app.DB,app.TENANT_DIR,app.ADMIN_USER,app.ADMIN_PASSWORD)
  app.DB=Path(self.tmp.name)/'test.sqlite3'
  app.TENANT_DIR=Path(self.tmp.name)/'tenant'
  app.TENANT_DIR.mkdir()
  app.ADMIN_USER='att_teacher'
  app.ADMIN_PASSWORD='temporary-test-password'
  app.TENANT.set(None)
  app.init()
  self.http=ThreadingHTTPServer(('127.0.0.1',0),app.H)
  self.thread=threading.Thread(target=self.http.serve_forever,daemon=True)
  self.thread.start()
  code,data,cookie=self.call('/api/login',{'username':'att_teacher','password':'temporary-test-password'},False)
  self.assertEqual(code,200,data)
  self.cookie=cookie.split(';',1)[0];self.csrf=data['csrf']
  app.TENANT.set(None)
  with app.db() as conn:
   class_id=conn.execute('INSERT INTO classes(name,grade) VALUES(?,?)',('8A','8')).lastrowid
   conn.executemany('INSERT INTO students(code,name,class_id) VALUES(?,?,?)',[(f'S{i:04}',f'Học sinh {i}',class_id) for i in range(120)])
   self.ids=[r['id'] for r in conn.execute('SELECT id FROM students ORDER BY id')]
  app.TENANT.set(None)

 def tearDown(self):
  self.http.shutdown();self.http.server_close();self.thread.join(timeout=5)
  app.DB,app.TENANT_DIR,app.ADMIN_USER,app.ADMIN_PASSWORD=self.orig
  app.TENANT.set(None);self.tmp.cleanup()

 def call(self,path,data,authorized=True):
  headers={'Content-Type':'application/json'}
  if authorized:headers.update({'Cookie':self.cookie,'X-CSRF-Token':self.csrf})
  request=Request(f'http://127.0.0.1:{self.http.server_port}{path}',data=json.dumps(data).encode(),headers=headers)
  try:
   with urlopen(request,timeout=30) as response:return response.status,json.load(response),response.headers.get('Set-Cookie','')
  except HTTPError as error:return error.code,json.load(error),''

 def test_save_120_and_update_is_idempotent(self):
  items=[{'student_id':sid,'status':'present','note':''} for sid in self.ids]
  code,result,_=self.call('/api/attendance',{'day':'2026-10-24','items':items})
  self.assertEqual(code,200,result);self.assertEqual(result['saved'],120)
  items[0]['status']='absent';items[0]['note']='Có phép báo sau'
  code,result,_=self.call('/api/attendance',{'day':'2026-10-24','items':items})
  self.assertEqual(code,200,result);self.assertEqual(result['saved'],120)
  app.TENANT.set(None)
  with app.db() as conn:
   self.assertEqual(conn.execute('SELECT COUNT(*) FROM attendance').fetchone()[0],120)
   rec=conn.execute('SELECT status,note FROM attendance WHERE student_id=?',(self.ids[0],)).fetchone()
   self.assertEqual(rec['status'],'absent')
   self.assertEqual(rec['note'],'Có phép báo sau')

 def test_reject_duplicate_students_without_partial_write(self):
  rows=[{'student_id':self.ids[0],'status':'present'},{'student_id':self.ids[0],'status':'absent'}]
  code,_,_=self.call('/api/attendance',{'day':'2026-10-24','items':rows})
  self.assertEqual(code,400)
  app.TENANT.set(None)
  with app.db() as conn:self.assertEqual(conn.execute('SELECT COUNT(*) FROM attendance').fetchone()[0],0)

if __name__=='__main__':unittest.main()
