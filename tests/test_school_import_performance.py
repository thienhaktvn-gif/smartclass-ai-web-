"""Regression checks for fast, non-destructive Excel school imports and batch moves."""
import base64, io, json, tempfile, threading, unittest
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.request import Request,urlopen
from urllib.error import HTTPError
from openpyxl import Workbook
import app

class SchoolImportPerformanceTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.saved=(app.DB,app.TENANT_DIR,app.ADMIN_USER,app.ADMIN_PASSWORD)
  app.DB=Path(self.tmp.name)/'root.sqlite'
  app.TENANT_DIR=Path(self.tmp.name)/'tenants'
  app.TENANT_DIR.mkdir()
  app.ADMIN_USER='teacher_bulk'
  app.ADMIN_PASSWORD='temporary-fixture'
  app.TENANT.set(None)
  app.init()
  self.server=ThreadingHTTPServer(('127.0.0.1',0),app.H)
  self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
  self.thread.start()
  status,session,cookie=self.call('login',{'username':'teacher_bulk','password':'temporary-fixture'},False)
  self.assertEqual(status,200,session)
  self.cookie=cookie.split(';')[0]
  self.csrf=session['csrf']

 def tearDown(self):
  self.server.shutdown();self.server.server_close();self.thread.join(timeout=4)
  app.DB,app.TENANT_DIR,app.ADMIN_USER,app.ADMIN_PASSWORD=self.saved
  app.TENANT.set(None)
  self.tmp.cleanup()

 def call(self,path,payload,auth=True):
  headers={'Content-Type':'application/json'}
  if auth:headers.update({'Cookie':self.cookie,'X-CSRF-Token':self.csrf})
  req=Request('http://127.0.0.1:'+str(self.server.server_port)+'/api/'+path,
              data=json.dumps(payload).encode(),headers=headers)
  try:
   with urlopen(req,timeout=30) as resp:return resp.status,json.load(resp),resp.headers.get('Set-Cookie','')
  except HTTPError as err:return err.code,json.load(err),''

 def make_sheet(self):
  book=Workbook();ws=book.active;ws.append(['Mã học sinh','Họ và tên','Lớp'])
  for i in range(120):ws.append(['HS%05d'%i,'Học sinh thử nghiệm %d'%i,'8A' if i%2==0 else '8B'])
  buf=io.BytesIO();book.save(buf)
  return base64.b64encode(buf.getvalue()).decode()

 def test_preview_import_repeat_and_move(self):
  encoded=self.make_sheet()
  status,preview,_=self.call('students/import',{'file':encoded,'preview':True})
  self.assertEqual(status,200,preview)
  self.assertEqual(preview['total'],120)
  for run in range(2):
   status,data,_=self.call('students/import',{'file':encoded,'confirm':'NHAP_TOAN_TRUONG'})
   self.assertEqual(status,200,data)
   self.assertEqual(data['created'],120 if run==0 else 0)
   self.assertEqual(data['updated'],0 if run==0 else 120)
   self.assertEqual(data['classes_created'],2 if run==0 else 0)
  app.TENANT.set(app.tenant_for('teacher_bulk'))
  try:
   with app.db() as conn:
    self.assertEqual(conn.execute('SELECT COUNT(*) FROM students').fetchone()[0],120)
    rows=conn.execute('SELECT id FROM students ORDER BY id LIMIT 50').fetchall()
    ids=[r['id'] for r in rows]
    target=conn.execute('SELECT id FROM classes WHERE name=?',('8B',)).fetchone()['id']
  finally:app.TENANT.set(None)
  status,data,_=self.call('students/move',{'ids':ids,'class_id':target})
  self.assertEqual(status,200,data)
  self.assertEqual(data['moved'],50)
  app.TENANT.set(app.tenant_for('teacher_bulk'))
  try:
   with app.db() as conn:
    matched=conn.execute('SELECT COUNT(*) FROM students WHERE id IN ('+','.join('?' for _ in ids)+') AND class_id=?',ids+[target]).fetchone()[0]
    self.assertEqual(matched,50)
  finally:app.TENANT.set(None)

if __name__=='__main__':unittest.main()
