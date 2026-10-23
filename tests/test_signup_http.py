import json
import os
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.request import Request, urlopen
from urllib.error import HTTPError

class RegistrationHTTP(unittest.TestCase):
 @classmethod
 def setUpClass(cls):
  if not os.getenv('SANGGIAO_TEST_POSTGRES_URL'):
   raise unittest.SkipTest('Postgres not configured')
  os.environ['SMARTCLASS_STORAGE_BACKEND']='postgres'
  os.environ['DATABASE_URL']=os.environ['SANGGIAO_TEST_POSTGRES_URL']
  os.environ['SMARTCLASS_ALLOW_REGISTRATION']='1'
  import app
  cls.app=app
  app.TENANT.set(None)
  app.init()
  cls.server=ThreadingHTTPServer(('127.0.0.1',0),app.H)
  threading.Thread(target=cls.server.serve_forever,daemon=True).start()
 @classmethod
 def tearDownClass(cls):
  cls.server.shutdown()
  cls.server.server_close()
 def send(self,path,data=None,cookie=''):
  headers={'Content-Type':'application/json'}
  if cookie:headers['Cookie']=cookie
  body=json.dumps(data).encode() if data is not None else None
  req=Request('http://127.0.0.1:'+str(self.server.server_port)+path,data=body,headers=headers)
  try:
   with urlopen(req,timeout=10) as response:
    return response.status,json.loads(response.read()),response.headers.get('Set-Cookie','')
  except HTTPError as error:
   return error.code,json.loads(error.read()),''
 def test_signup_login_and_data(self):
  code,data,_=self.send('/api/register',{'username':'qa_http_teacher','password':'StrongTeacher123'})
  self.assertEqual(code,201,data)
  code,data,_=self.send('/api/register',{'username':'qa_http_teacher','password':'StrongTeacher123'})
  self.assertEqual(code,409,data)
  code,data,_=self.send('/api/login',{'username':'qa_http_teacher','password':'WrongTeacher123'})
  self.assertEqual(code,401,data)
  code,data,cookie=self.send('/api/login',{'username':'qa_http_teacher','password':'StrongTeacher123'})
  self.assertEqual(code,200,data)
  self.assertIn('scsession=',cookie)
  code,data,_=self.send('/api/classes',cookie=cookie)
  self.assertEqual(code,200,data)
  self.assertEqual(data['items'],[])
