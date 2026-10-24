"""Role separation regression: only the configured admin may read account directory."""
import json
import tempfile
import threading
import unittest
from pathlib import Path
from http.server import ThreadingHTTPServer
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import app

class RoleSeparationTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory()
  self.orig=(app.DB,app.TENANT_DIR,app.ADMIN_USER,app.ADMIN_PASSWORD)
  app.DB=Path(self.tmp.name)/'root.db'
  app.TENANT_DIR=Path(self.tmp.name)/'tenant'
  app.TENANT_DIR.mkdir()
  app.ADMIN_USER='admin_case'
  app.ADMIN_PASSWORD='TestAdminPass123'
  app.TENANT.set(None);app.init()
  app.TENANT.set(None)
  with app.db() as conn:
   conn.execute('INSERT INTO users(username,password_hash,role) VALUES(?,?,?)',('teacher_case',app.hashpw('TestTeacherPass123'),'teacher'))
  self.server=ThreadingHTTPServer(('127.0.0.1',0),app.H)
  self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()

 def tearDown(self):
  self.server.shutdown();self.server.server_close();self.thread.join(timeout=5)
  app.DB,app.TENANT_DIR,app.ADMIN_USER,app.ADMIN_PASSWORD=self.orig
  app.TENANT.set(None);self.tmp.cleanup()

 def request(self,path,payload=None,cookie='',csrf=''):
  headers={}
  if cookie:headers['Cookie']=cookie
  if csrf:headers['X-CSRF-Token']=csrf
  if payload is not None:headers['Content-Type']='application/json'
  req=Request(f'http://127.0.0.1:{self.server.server_port}{path}',
     data=json.dumps(payload).encode() if payload is not None else None,headers=headers)
  try:
   with urlopen(req,timeout=15) as response:return response.status,json.load(response),response.headers.get('Set-Cookie','')
  except HTTPError as error:return error.code,json.load(error),''

 def login(self,username,password):
  status,_,cookie=self.request('/api/login',{'username':username,'password':password})
  self.assertEqual(status,200)
  return cookie.split(';',1)[0]

 def test_admin_dashboard_restricted(self):
  admin=self.login('admin_case','TestAdminPass123')
  teacher=self.login('teacher_case','TestTeacherPass123')
  status,profile,_=self.request('/api/me',cookie=admin)
  self.assertEqual(status,200);self.assertEqual(profile['role'],'admin')
  status,profile,_=self.request('/api/me',cookie=teacher)
  self.assertEqual(status,200);self.assertEqual(profile['role'],'teacher')
  status,accounts,_=self.request('/api/admin/teachers',cookie=admin)
  self.assertEqual(status,200,accounts);self.assertEqual(accounts['total'],2)
  self.assertNotIn('password_hash',str(accounts))
  status,_,_=self.request('/api/admin/teachers',cookie=teacher)
  self.assertEqual(status,403)
  status,_,_=self.request('/api/admin/teachers')
  self.assertEqual(status,401)

 def test_separate_admin_teacher_login_portals(self):
  status,_,_=self.request('/api/login',{'username':'teacher_case','password':'TestTeacherPass123','portal':'admin'})
  self.assertEqual(status,403)
  status,_,_=self.request('/api/login',{'username':'admin_case','password':'TestAdminPass123','portal':'teacher'})
  self.assertEqual(status,403)
  status,_,cookie=self.request('/api/login',{'username':'admin_case','password':'TestAdminPass123','portal':'admin'})
  self.assertEqual(status,200)
  self.assertTrue(cookie.startswith('scsession='))
  status,_,cookie=self.request('/api/login',{'username':'teacher_case','password':'TestTeacherPass123','portal':'teacher'})
  self.assertEqual(status,200)
  self.assertTrue(cookie.startswith('scsession='))


 def test_admin_reset_requires_role_and_forces_change(self):
  admin=self.login('admin_case','TestAdminPass123')
  teacher=self.login('teacher_case','TestTeacherPass123')
  _,admin_profile,_=self.request('/api/me',cookie=admin)
  _,teacher_profile,_=self.request('/api/me',cookie=teacher)
  body={'username':'teacher_case','confirm':'teacher_case'}
  status,_,_=self.request('/api/admin/password-reset',body,cookie=teacher,csrf=teacher_profile['csrf'])
  self.assertEqual(status,403)
  status,_,_=self.request('/api/admin/password-reset',body,cookie=admin)
  self.assertEqual(status,401)
  status,_,_=self.request('/api/admin/password-reset',{'username':'admin_case','confirm':'admin_case'},cookie=admin,csrf=admin_profile['csrf'])
  self.assertEqual(status,400)
  status,data,_=self.request('/api/admin/password-reset',body,cookie=admin,csrf=admin_profile['csrf'])
  self.assertEqual(status,200,data)
  temporary=data['temporaryPassword']
  self.assertGreaterEqual(len(temporary),12)
  self.assertNotIn('password_hash',str(data))
  status,_,_=self.request('/api/me',cookie=teacher)
  self.assertEqual(status,200)
  self.assertIsNone(self.request('/api/me',cookie=teacher)[1]['user'])
  status,_,_=self.request('/api/login',{'username':'teacher_case','password':'TestTeacherPass123'})
  self.assertEqual(status,401)
  forced=self.login('teacher_case',temporary)
  _,profile,_=self.request('/api/me',cookie=forced)
  self.assertTrue(profile['mustChangePassword'])
  status,_,_=self.request('/api/questions',cookie=forced)
  self.assertEqual(status,403)
  status,_,_=self.request('/api/questions',{'subject':'Toán'},cookie=forced,csrf=profile['csrf'])
  self.assertEqual(status,403)
  status,_,_=self.request('/api/password/change',{'current_password':'incorrect','new_password':'NewSecureTeacher456'},cookie=forced,csrf=profile['csrf'])
  self.assertEqual(status,401)
  status,_,_=self.request('/api/password/change',{'current_password':temporary,'new_password':'NewSecureTeacher456'},cookie=forced,csrf=profile['csrf'])
  self.assertEqual(status,200)
  status,who,_=self.request('/api/me',cookie=forced)
  self.assertIsNone(who['user'])
  updated=self.login('teacher_case','NewSecureTeacher456')
  _,who,_=self.request('/api/me',cookie=updated)
  self.assertEqual(who['role'],'teacher')
  self.assertFalse(who['mustChangePassword'])
  status,_,_=self.request('/api/login',{'username':'teacher_case','password':temporary})
  self.assertEqual(status,401)
  status,_,_=self.request('/api/admin/password-reset',body,cookie=admin,csrf=admin_profile['csrf'])
  self.assertEqual(status,200)

if __name__=='__main__':unittest.main()
