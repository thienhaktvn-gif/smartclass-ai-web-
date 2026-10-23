"""PostgreSQL integration tests. Run only against disposable test database."""
import os
import unittest

class PostgreSQLIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if not os.environ.get("SANGGIAO_TEST_POSTGRES_URL"):
            raise unittest.SkipTest("No disposable PostgreSQL test URL")
        os.environ["SMARTCLASS_STORAGE_BACKEND"]="postgres"
        os.environ["DATABASE_URL"]=os.environ["SANGGIAO_TEST_POSTGRES_URL"]
        os.environ["SMARTCLASS_ADMIN_PASSWORD"]="QaDemoPass123!"
        os.environ["SMARTCLASS_ADMIN_USER"]="giaovien"
        import app
        cls.app=app
        app.TENANT.set(None)
        app.init()
    def test_registration_hash_and_tenant_setup(self):
        app=self.app
        name="qa_signup_teacher"
        app.TENANT.set(None)
        with app.db() as c:
            if not c.execute("SELECT id FROM users WHERE username=?",(name,)).fetchone():
                c.execute("INSERT INTO users(username,password_hash,role) VALUES(?,?,?)",(name,app.hashpw("SecureTeacher123"),"teacher"))
            row=c.execute("SELECT password_hash FROM users WHERE username=?",(name,)).fetchone()
            self.assertTrue(app.checkpw("SecureTeacher123",row["password_hash"]))
            self.assertFalse(app.checkpw("WrongTeacher123",row["password_hash"]))
        app.TENANT.set(app.tenant_for(name))
        try:
            app.init()
            with app.db() as c:
                self.assertEqual(c.execute("SELECT COUNT(*) FROM classes").fetchone()[0],0)
                self.assertGreater(c.execute("INSERT INTO classes(name,grade) VALUES(?,?)",("My class","9")).lastrowid,0)
        finally:
            app.TENANT.set(None)
        with app.db() as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM classes WHERE name=?",("My class",)).fetchone()[0],0)
    def test_admin_class_student_question_exam_and_tenant(self):
        app=self.app
        app.TENANT.set(None)
        with app.db() as c:
            row=c.execute("INSERT INTO classes(name,grade) VALUES(?,?)",("PostgreSQL QA Class","9"))
            cid=row.lastrowid
            self.assertIsInstance(cid,int)
            sid=c.execute("INSERT INTO students(code,name,class_id) VALUES(?,?,?)",("PGTEST001","QA Student",cid)).lastrowid
            self.assertGreater(sid,0)
            qid=c.execute("INSERT INTO questions(subject,grade,topic,content,a,b,c,d,answer) VALUES(?,?,?,?,?,?,?,?,?)",("Tin học","9","QA","QA question","1","2","3","4","A")).lastrowid
            self.assertGreater(qid,0)
            eid=c.execute("INSERT INTO exams(title,subject,grade,duration,published) VALUES(?,?,?,?,?)",("PG staging exam","Tin học","9",15,0)).lastrowid
            c.execute("INSERT INTO exam_questions(exam_id,question_id,ord) VALUES(?,?,?)",(eid,qid,1))
            self.assertEqual(c.execute("SELECT COUNT(*) FROM exam_questions WHERE exam_id=?",(eid,)).fetchone()[0],1)
            c.execute("INSERT INTO attendance(student_id,day,status,note) VALUES(?,?,?,?)",(sid,"2026-10-23","present","QA"))
            c.execute("INSERT INTO attendance(student_id,day,status,note) VALUES(?,?,?,?) ON CONFLICT(student_id,day) DO UPDATE SET status=excluded.status,note=excluded.note",(sid,"2026-10-23","late","QA updated"))
            self.assertEqual(c.execute("SELECT status FROM attendance WHERE student_id=?",(sid,)).fetchone()[0],"late")
            attempt=c.execute("INSERT INTO attempts(exam_id,student_name,access_code_hash,form_seed,score,correct,total,answers,feedback) VALUES(?,?,?,?,?,?,?,?,?)",(eid,"QA Student","hash",123,10.0,1,1,'{"1":"A"}',"QA done")).lastrowid
            self.assertGreater(attempt,0)
            self.assertEqual(c.execute("SELECT score FROM attempts WHERE id=?",(attempt,)).fetchone()[0],10.0)
            c.execute("INSERT OR IGNORE INTO classes(name,grade) VALUES(?,?)",("PostgreSQL QA Class","9"))
        app.TENANT.set(app.tenant_for("integration_teacher"))
        try:
            app.init()
            with app.db() as c:
                self.assertEqual(c.execute("SELECT COUNT(*) FROM classes").fetchone()[0],0)
                other=c.execute("INSERT INTO classes(name,grade) VALUES(?,?)",("Private teacher class","8")).lastrowid
                self.assertGreater(other,0)
        finally:
            app.TENANT.set(None)
        with app.db() as c:
            self.assertEqual(c.execute("SELECT COUNT(*) FROM classes WHERE name=?",("Private teacher class",)).fetchone()[0],0)

if __name__=="__main__":unittest.main()
