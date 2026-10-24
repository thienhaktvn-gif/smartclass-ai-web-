"""Regression: teacher cookie remains valid independently of process memory."""
import json
import os
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import app


class PersistentTeacherSessionTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.old=(app.DB,app.TENANT_DIR,app.ADMIN_USER,app.ADMIN_PASSWORD)
  app.DB=Path(self.tmp.name)/'main.sqlite3'
  app.TENANT_DIR=Path(self.tmp.name)/'teachers'
  app.TENANT_DIR.mkdir()
  app.ADMIN_USER='teacher_test'
  app.ADMIN_PASSWORD='test-password-only'
  app.TENANT.set(None)
  app.init()
  self.server=ThreadingHTTPServer(('127.0.0.1',0),app.H)
  self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
  self.thread.start()

 def tearDown(self):
  self.server.shutdown()
  self.server.server_close()
  self.thread.join(timeout=5)
  app.DB,app.TENANT_DIR,app.ADMIN_USER,app.ADMIN_PASSWORD=self.old
  app.TENANT.set(None)
  self.tmp.cleanup()

 def call(self,path,body=None,cookie='',csrf=''):
  headers={}
  if cookie:headers['Cookie']=cookie
  if csrf:headers['X-CSRF-Token']=csrf
  if body is not None:headers['Content-Type']='application/json'
  request=Request(f'http://127.0.0.1:{self.server.server_port}{path}',
                  data=json.dumps(body).encode() if body is not None else None,
                  headers=headers)
  try:
   with urlopen(request,timeout=8) as response:
    return response.status,json.load(response),response.headers.get('Set-Cookie','')
  except HTTPError as error:
   return error.code,json.load(error),''

 def test_login_pagination_logout(self):
  status,login,cookie=self.call('/api/login',{'username':'teacher_test','password':'test-password-only'})
  self.assertEqual(status,200)
  cookie=cookie.split(';',1)[0]
  self.assertTrue(cookie.startswith('scsession='))
  self.assertEqual(self.call('/api/me',cookie=cookie)[1]['user'],'teacher_test')
  status,data,_=self.call('/api/questions/page?page=1&size=30',cookie=cookie)
  self.assertEqual(status,200,data)
  self.assertIn('items',data)
  self.assertEqual(self.call('/api/questions/page?page=2',cookie=cookie)[0],200)
  self.assertEqual(self.call('/api/logout',{},cookie=cookie,csrf=login['csrf'])[0],200)
  self.assertEqual(self.call('/api/questions/page',cookie=cookie)[0],401)

 def test_unauthenticated_denied(self):
  self.assertEqual(self.call('/api/questions/page')[0],401)


if __name__=='__main__':
 unittest.main()
