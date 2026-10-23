"""Non-destructive regression tests for current SQLite backend."""
import os
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

class DatabaseTests(unittest.TestCase):
    def test_teacher_isolation_and_classes(self):
        with tempfile.TemporaryDirectory() as temp:
            os.environ['SMARTCLASS_DB'] = str(Path(temp) / 'school.db')
            import importlib
            import app
            importlib.reload(app)
            try:
                app.TENANT.set(None)
                app.init()
                with app.db() as conn:
                    conn.execute('INSERT INTO classes(name,grade) VALUES(?,?)', ('Class 9A', '9'))
                teacher = app.tenant_for('teacher-test')
                self.assertNotEqual(str(teacher), str(app.DB))
                app.TENANT.set(teacher)
                app.init()
                with app.db() as conn:
                    count = conn.execute('SELECT COUNT(*) FROM classes').fetchone()[0]
                    self.assertEqual(count, 0)
                    conn.execute('INSERT INTO classes(name,grade) VALUES(?,?)', ('Class 8B', '8'))
                app.TENANT.set(None)
                with app.db() as conn:
                    names = [x[0] for x in conn.execute('SELECT name FROM classes')]
                    self.assertEqual(names, ['Class 9A'])
            finally:
                app.TENANT.set(None)

if __name__ == '__main__':
    unittest.main()
