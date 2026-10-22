import os, json, sqlite3, secrets, hashlib, hmac, random, re, urllib.request, urllib.error, base64, uuid
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from http.cookies import SimpleCookie
from datetime import datetime, timezone

ROOT=Path(__file__).parent
DB=Path(os.environ.get('SMARTCLASS_DB',str(ROOT/'smartclass.db')))
DB.parent.mkdir(parents=True,exist_ok=True)
SECRET=os.environ.get('SMARTCLASS_SECRET','')
ADMIN_PASSWORD=os.environ.get('SMARTCLASS_ADMIN_PASSWORD','')
ADMIN_USER=os.environ.get('SMARTCLASS_ADMIN_USER','giaovien')
AI_KEY=os.environ.get('GEMINI_API_KEY','')
AI_MODEL=os.environ.get('GEMINI_MODEL','gemini-2.5-flash')
IMAGE_MODEL=os.environ.get('GEMINI_IMAGE_MODEL','gemini-2.5-flash-image')
MEDIA=ROOT/'media';MEDIA.mkdir(exist_ok=True)
PUBLIC_URL=os.environ.get('PUBLIC_URL','')
SESSIONS={}

def db():
 c=sqlite3.connect(DB,timeout=15); c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');return c

def init():
 with db() as c:
  c.executescript('''CREATE TABLE IF NOT EXISTS users(id INTEGER PRIMARY KEY,username TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,role TEXT NOT NULL,created TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS classes(id INTEGER PRIMARY KEY,name TEXT NOT NULL UNIQUE,grade TEXT DEFAULT '');
  CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY,code TEXT UNIQUE NOT NULL,name TEXT NOT NULL,class_id INTEGER REFERENCES classes(id));
  CREATE TABLE IF NOT EXISTS questions(id INTEGER PRIMARY KEY,subject TEXT NOT NULL,grade TEXT NOT NULL,topic TEXT NOT NULL,content TEXT NOT NULL,a TEXT NOT NULL,b TEXT NOT NULL,c TEXT NOT NULL,d TEXT NOT NULL,answer TEXT NOT NULL CHECK(answer IN ('A','B','C','D')),difficulty TEXT NOT NULL DEFAULT 'Nhận biết',explanation TEXT NOT NULL DEFAULT '',origin TEXT DEFAULT 'manual');
  CREATE TABLE IF NOT EXISTS exams(id INTEGER PRIMARY KEY,title TEXT NOT NULL,subject TEXT NOT NULL,grade TEXT NOT NULL,duration INTEGER NOT NULL DEFAULT 45,published INTEGER NOT NULL DEFAULT 0,created TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS exam_questions(exam_id INTEGER REFERENCES exams(id) ON DELETE CASCADE,question_id INTEGER REFERENCES questions(id),ord INTEGER NOT NULL,PRIMARY KEY(exam_id,question_id));
  CREATE TABLE IF NOT EXISTS attempts(id INTEGER PRIMARY KEY,exam_id INTEGER NOT NULL REFERENCES exams(id),student_name TEXT NOT NULL,access_code_hash TEXT NOT NULL,form_seed INTEGER NOT NULL,score REAL NOT NULL,correct INTEGER NOT NULL,total INTEGER NOT NULL,answers TEXT NOT NULL,feedback TEXT NOT NULL,created TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE INDEX IF NOT EXISTS attempts_exam_idx ON attempts(exam_id);
  CREATE TABLE IF NOT EXISTS games(id INTEGER PRIMARY KEY,title TEXT NOT NULL,topic TEXT NOT NULL,kind TEXT NOT NULL,question_ids TEXT NOT NULL,created TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS lesson_media(id INTEGER PRIMARY KEY,title TEXT NOT NULL,kind TEXT NOT NULL,content TEXT NOT NULL,filename TEXT DEFAULT '',created TEXT DEFAULT CURRENT_TIMESTAMP);''')
  row=c.execute('SELECT id FROM users WHERE username=?',(ADMIN_USER,)).fetchone()
  if not row and ADMIN_PASSWORD:
   salt=secrets.token_hex(16);v=hashlib.pbkdf2_hmac('sha256',ADMIN_PASSWORD.encode(),bytes.fromhex(salt),240000).hex()
   c.execute('INSERT INTO users(username,password_hash,role) VALUES(?,?,?)',(ADMIN_USER,salt+':'+v,'teacher'))
  if c.execute('SELECT COUNT(*) FROM questions').fetchone()[0]==0 and os.getenv('SMARTCLASS_DEMO','0')=='1':
   rows=[('Tin học','9','Cấu trúc rẽ nhánh','Trong Python, từ khóa nào bắt đầu câu lệnh điều kiện?','for','if','def','while','B','Nhận biết','if được dùng để kiểm tra điều kiện.'),('Tin học','9','Vòng lặp','Hàm nào tạo dãy số nguyên trong Python?','range','print','input','str','A','Nhận biết','range tạo các giá trị cho vòng lặp.'),('Tin học','9','Kiểu dữ liệu','Kiểu dữ liệu nào biểu diễn Đúng/Sai?','str','list','bool','int','C','Nhận biết','bool có hai giá trị True và False.'),('Tin học','9','Thuật toán','Tìm kiếm nhị phân yêu cầu điều gì?','Mảng đảo ngược','Dữ liệu được sắp xếp','Tất cả phần tử trùng nhau','Chỉ số chẵn','B','Thông hiểu','Tìm kiếm nhị phân cần dãy đã sắp xếp.'),('Tin học','9','Mảng','Chỉ số đầu tiên của list Python là bao nhiêu?','1','-1','0','2','C','Nhận biết','List được đánh chỉ số từ 0.'),('Tin học','9','Độ phức tạp','Thuật toán duyệt lần lượt n phần tử có thời gian O(?)','1','log n','n','n²','C','Thông hiểu','Duyệt n phần tử tuyến tính là O(n).')]
   for r in rows:c.execute('INSERT INTO questions(subject,grade,topic,content,a,b,c,d,answer,difficulty,explanation,origin) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',(*r,'demo'))

def gemini(parts,model=None,timeout=70,config=None):
 if not AI_KEY:raise RuntimeError('Chưa cấu hình GEMINI_API_KEY trên máy chủ.')
 model=model or AI_MODEL
 if not re.fullmatch(r'[a-zA-Z0-9_.-]{3,80}',model):raise RuntimeError('Tên model không hợp lệ.')
 url='https://generativelanguage.googleapis.com/v1beta/models/'+model+':generateContent'
 payload={'contents':[{'role':'user','parts':parts}]}
 if config:payload['generationConfig']=config
 req=urllib.request.Request(url,data=json.dumps(payload).encode(),headers={'x-goog-api-key':AI_KEY,'Content-Type':'application/json'},method='POST')
 try:
  with urllib.request.urlopen(req,timeout=timeout) as r:return json.load(r)
 except urllib.error.HTTPError as e:
  if e.code in (401,403):raise RuntimeError('Gemini từ chối khóa API hoặc quyền model.')
  if e.code==429:raise RuntimeError('Gemini đã hết hạn mức hoặc bị giới hạn tốc độ.')
  raise RuntimeError(f'Gemini trả lỗi HTTP {e.code}. Kiểm tra model và hạn mức.')
 except (urllib.error.URLError,TimeoutError):raise RuntimeError('Không kết nối được Gemini.')

def gemini_text(prompt):
 r=gemini([{'text':prompt}],config={'responseMimeType':'application/json'})
 parts=[p.get('text','') for c in r.get('candidates',[]) for p in c.get('content',{}).get('parts',[])]
 if not parts:raise RuntimeError('Gemini không trả nội dung văn bản.')
 return json.loads(''.join(parts).strip().removeprefix('```json').removeprefix('```').removesuffix('```').strip())

def safe_game(row):
 return {'id':row['id'],'title':row['title'],'topic':row['topic'],'kind':row['kind'],'count':len(json.loads(row['question_ids'])),'created':row['created']}

def hashpw(p):
 salt=secrets.token_hex(16);return salt+':'+hashlib.pbkdf2_hmac('sha256',p.encode(),bytes.fromhex(salt),240000).hex()
def checkpw(p,v):
 try:
  salt,he=v.split(':');return hmac.compare_digest(hashlib.pbkdf2_hmac('sha256',p.encode(),bytes.fromhex(salt),240000).hex(),he)
 except:return False

def public_question(q):
 return {k:q[k] for k in ('id','content','a','b','c','d','difficulty')}
def shuffled(qs,seed):
 rng=random.Random(seed);a=list(qs);rng.shuffle(a);out=[]
 for q in a:
  opts=[{'label':z,'text':q[z.lower()]} for z in 'ABCD'];rng.shuffle(opts)
  out.append({'id':q['id'],'content':q['content'],'options':[{'key':'ABCD'[i],'text':o['text']} for i,o in enumerate(opts)],'_correct':'ABCD'[next(i for i,o in enumerate(opts) if o['label']==q['answer'])]})
 return out

class H(BaseHTTPRequestHandler):
 def log_message(self,fmt,*args):print('HTTP:',fmt%args)
 def sendj(self,code,data,headers=None):
  b=json.dumps(data,ensure_ascii=False).encode();self.send_response(code);self.send_header('Content-Type','application/json; charset=utf-8');self.send_header('Content-Length',str(len(b)));self.send_header('Cache-Control','no-store');self.send_header('X-Content-Type-Options','nosniff');self.send_header('X-Frame-Options','DENY');self.send_header('Referrer-Policy','same-origin');
  if headers:
   for k,v in headers.items():self.send_header(k,v)
  self.end_headers();self.wfile.write(b)
 def err(self,code,msg):self.sendj(code,{'error':msg})
 def body(self):
  try:
   n=int(self.headers.get('Content-Length','0'))
   if n>70000 or n<1:raise ValueError()
   v=json.loads(self.rfile.read(n));return v if isinstance(v,dict) else None
  except:return None
 def session(self):
  try:
   c=SimpleCookie();c.load(self.headers.get('Cookie',''));tok=c['scsession'].value
   rec=SESSIONS.get(tok)
   if rec and rec['created']+43200>datetime.now(timezone.utc).timestamp():return rec
  except:pass
  return None
 def auth(self):
  u=self.session()
  if not u or self.headers.get('X-CSRF-Token','')!=u['csrf']:self.err(401,'Cần đăng nhập hợp lệ.');return None
  return u
 def do_GET(self):
  p=urlparse(self.path).path
  if p=='/api/health':return self.sendj(200,{'ok':True,'aiConfigured':bool(AI_KEY),'aiProvider':'Gemini','imageConfigured':bool(AI_KEY),'videoConfigured':False,'storage':'sqlite','persistent':os.getenv('SMARTCLASS_PERSISTENT','0')=='1'})
  if p in ('/','/index.html') or p.startswith('/auth/') or p in ('/dashboard','/teacher','/student'):
   b=(ROOT/'index.html').read_bytes();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(b)));self.send_header('X-Content-Type-Options','nosniff');self.end_headers();return self.wfile.write(b)
  if p in ('/app.js','/style.css'):
   b=(ROOT/p[1:]).read_bytes();self.send_response(200);self.send_header('Content-Type','text/javascript; charset=utf-8' if p.endswith('.js') else 'text/css; charset=utf-8');self.send_header('Content-Length',str(len(b)));self.end_headers();return self.wfile.write(b)
  if p=='/api/me':
   s=self.session();return self.sendj(200,{'user':s['username'],'csrf':s['csrf']} if s else {'user':None})
  if p=='/api/exams/public':
   with db() as c:rr=c.execute('SELECT id,title,subject,grade,duration FROM exams WHERE published=1 ORDER BY id DESC').fetchall()
   return self.sendj(200,{'items':[dict(x) for x in rr]})
  if p.startswith('/api/exams/public/'):
   try:eid=int(p.rsplit('/',1)[-1])
   except:return self.err(400,'Mã đề không hợp lệ.')
   with db() as c:
    e=c.execute('SELECT id,title,subject,grade,duration FROM exams WHERE id=? AND published=1',(eid,)).fetchone()
    if not e:return self.err(404,'Đề chưa được công bố.')
    qs=c.execute('SELECT q.* FROM exam_questions eq JOIN questions q ON q.id=eq.question_id WHERE eq.exam_id=? ORDER BY eq.ord',(eid,)).fetchall()
   return self.sendj(200,{'exam':dict(e),'count':len(qs)})
  if p=='/api/games/public':
   with db() as c:rows=c.execute('SELECT * FROM games ORDER BY id DESC LIMIT 100').fetchall()
   return self.sendj(200,{'items':[safe_game(r) for r in rows]})
  if p.startswith('/api/games/public/'):
   try:gid=int(p.rsplit('/',1)[-1])
   except:return self.err(400,'Mã trò chơi sai.')
   with db() as c:
    g=c.execute('SELECT * FROM games WHERE id=?',(gid,)).fetchone()
    if not g:return self.err(404,'Không tìm thấy trò chơi.')
    ids=json.loads(g['question_ids'])
    q=c.execute('SELECT * FROM questions WHERE id IN ('+','.join('?' for _ in ids)+')',ids).fetchall() if ids else []
   rng=random.SystemRandom();q=list(q);rng.shuffle(q)
   return self.sendj(200,{'game':safe_game(g),'items':[public_question(x) for x in q]})
  if p.startswith('/media/'):
   name=p.split('/')[-1]
   if not re.fullmatch(r'[a-f0-9]{32}\.(png|jpg|webp)',name):return self.err(404,'Không tìm thấy hình ảnh.')
   s=self.session()
   if not s:return self.err(401,'Hãy đăng nhập giáo viên.')
   target=MEDIA/name
   if not target.is_file():return self.err(404,'Không tìm thấy hình ảnh.')
   b=target.read_bytes();self.send_response(200);self.send_header('Content-Type',{'png':'image/png','jpg':'image/jpeg','webp':'image/webp'}[name.rsplit('.',1)[1]]);self.send_header('Content-Length',str(len(b)));self.send_header('Cache-Control','private, no-store');self.end_headers();return self.wfile.write(b)
  if p.startswith('/api/'):
   s=self.session()
   if not s:return self.err(401,'Vui lòng đăng nhập giáo viên.')
   with db() as c:
    if p=='/api/games':return self.sendj(200,{'items':[safe_game(r) for r in c.execute('SELECT * FROM games ORDER BY id DESC LIMIT 100')]})
    if p=='/api/media':return self.sendj(200,{'items':[dict(r) for r in c.execute('SELECT * FROM lesson_media ORDER BY id DESC LIMIT 100')]})
    if p=='/api/overview':
     data={k:c.execute('SELECT COUNT(*) FROM '+table).fetchone()[0] for k,table in [('questions','questions'),('exams','exams'),('attempts','attempts'),('students','students')]}
     return self.sendj(200,data)
    if p=='/api/questions':return self.sendj(200,{'items':[dict(x) for x in c.execute('SELECT * FROM questions ORDER BY id DESC LIMIT 500')]})
    if p=='/api/exams':return self.sendj(200,{'items':[dict(x) for x in c.execute('SELECT e.*, COUNT(eq.question_id) num_questions FROM exams e LEFT JOIN exam_questions eq ON e.id=eq.exam_id GROUP BY e.id ORDER BY e.id DESC')]})
    if p=='/api/attempts':return self.sendj(200,{'items':[dict(x) for x in c.execute('SELECT a.id,a.exam_id,e.title exam,a.student_name,a.score,a.correct,a.total,a.feedback,a.created FROM attempts a JOIN exams e ON e.id=a.exam_id ORDER BY a.id DESC LIMIT 300')]})
   return self.err(404,'Không tồn tại API.')
  return self.err(404,'Không tìm thấy trang.')
 def do_POST(self):
  p=urlparse(self.path).path;d=self.body()
  if d is None:return self.err(400,'Dữ liệu JSON không hợp lệ hoặc quá lớn.')
  if p=='/api/login':
   name=str(d.get('username',''))[:100];pw=str(d.get('password',''))
   with db() as c:u=c.execute('SELECT * FROM users WHERE username=?',(name,)).fetchone()
   if not u or not checkpw(pw,u['password_hash']):return self.err(401,'Sai tài khoản hoặc mật khẩu.')
   tok=secrets.token_urlsafe(32);csrf=secrets.token_urlsafe(24);SESSIONS[tok]={'username':name,'csrf':csrf,'created':datetime.now(timezone.utc).timestamp()}
   secure='; Secure' if self.headers.get('X-Forwarded-Proto','')=='https' or PUBLIC_URL.startswith('https://') else ''
   return self.sendj(200,{'user':name,'csrf':csrf},{'Set-Cookie':f'scsession={tok}; HttpOnly; SameSite=Lax; Path=/; Max-Age=43200{secure}'})
  if p=='/api/games/answer':
   try:gid=int(d.get('game_id'));qid=int(d.get('question_id'));choice=str(d.get('choice','')).upper()
   except:return self.err(400,'Câu trả lời không hợp lệ.')
   if choice not in ('A','B','C','D'):return self.err(400,'Chọn A, B, C hoặc D.')
   with db() as c:
    game=c.execute('SELECT question_ids FROM games WHERE id=?',(gid,)).fetchone()
    if not game or qid not in json.loads(game['question_ids']):return self.err(404,'Câu hỏi không nằm trong trò chơi.')
    q=c.execute('SELECT answer,explanation FROM questions WHERE id=?',(qid,)).fetchone()
    if not q:return self.err(404,'Câu hỏi không tồn tại.')
   return self.sendj(200,{'correct':choice==q['answer'],'answer':q['answer'],'explanation':q['explanation']})
  if p=='/api/exams/submit':
   try:eid=int(d.get('exam_id')); name=str(d.get('student_name','')).strip()[:80];code=str(d.get('access_code','')).strip();answers=d.get('answers',{})
   except:return self.err(400,'Thông tin bài làm không hợp lệ.')
   if not name or len(name)<2 or not isinstance(answers,dict) or len(code)<4:return self.err(400,'Nhập tên và mã dự thi ít nhất 4 ký tự.')
   with db() as c:
    e=c.execute('SELECT * FROM exams WHERE id=? AND published=1',(eid,)).fetchone()
    if not e:return self.err(404,'Đề chưa công bố.')
    qs=c.execute('SELECT q.* FROM exam_questions eq JOIN questions q ON q.id=eq.question_id WHERE eq.exam_id=? ORDER BY eq.ord',(eid,)).fetchall()
    seed=int.from_bytes(hmac.new(SECRET.encode(),f'{eid}:{name}:{code}'.encode(),hashlib.sha256).digest()[:8],'big') if SECRET else int.from_bytes(hashlib.sha256(f'{eid}:{name}:{code}'.encode()).digest()[:8],'big')
    forms=shuffled(qs,seed);correct=0;report=[]
    for q in forms:
     selected=str(answers.get(str(q['id']),'')).upper();ok=selected==q['_correct'];correct+=ok
     orig=next(x for x in qs if x['id']==q['id'])
     report.append({'question':q['content'],'selected':selected,'correct':q['_correct'],'ok':ok,'explanation':orig['explanation']})
    total=len(forms);score=round(correct/total*10,2) if total else 0
    fb=('Hoàn thành rất tốt. ' if score>=8 else 'Đã nắm được phần cơ bản. ' if score>=5 else 'Nên ôn tập lại các khái niệm nền tảng. ')+f'Đúng {correct}/{total} câu. Hãy xem giải thích ở các câu chưa đúng.'
    c.execute('INSERT INTO attempts(exam_id,student_name,access_code_hash,form_seed,score,correct,total,answers,feedback) VALUES(?,?,?,?,?,?,?,?,?)',(eid,name,hashlib.sha256((code+name).encode()).hexdigest(),seed,score,correct,total,json.dumps(answers),fb))
   return self.sendj(200,{'score':score,'correct':correct,'total':total,'feedback':fb,'review':report,'ai':False})
  if p=='/api/exams/form':
   try:eid=int(d.get('exam_id'));name=str(d.get('student_name','')).strip()[:80];code=str(d.get('access_code','')).strip()
   except:return self.err(400,'Dữ liệu không hợp lệ.')
   if len(name)<2 or len(code)<4:return self.err(400,'Cần họ tên và mã dự thi từ 4 ký tự.')
   with db() as c:
    e=c.execute('SELECT id,title,subject,grade,duration FROM exams WHERE id=? AND published=1',(eid,)).fetchone()
    if not e:return self.err(404,'Không tìm thấy đề công bố.')
    qs=c.execute('SELECT q.* FROM exam_questions eq JOIN questions q ON q.id=eq.question_id WHERE eq.exam_id=? ORDER BY eq.ord',(eid,)).fetchall()
   seed=int.from_bytes(hmac.new(SECRET.encode(),f'{eid}:{name}:{code}'.encode(),hashlib.sha256).digest()[:8],'big') if SECRET else int.from_bytes(hashlib.sha256(f'{eid}:{name}:{code}'.encode()).digest()[:8],'big')
   form=shuffled(qs,seed)
   return self.sendj(200,{'exam':dict(e),'items':[{'id':q['id'],'content':q['content'],'options':q['options']} for q in form]})
  s=self.auth()
  if not s:return
  if p=='/api/logout':
   cookie=SimpleCookie();cookie.load(self.headers.get('Cookie',''))
   if 'scsession' in cookie:SESSIONS.pop(cookie['scsession'].value,None)
   return self.sendj(200,{'ok':True},{'Set-Cookie':'scsession=; Max-Age=0; HttpOnly; SameSite=Lax; Path=/'})
  if p=='/api/questions':
   required=['subject','grade','topic','content','a','b','c','d','answer']
   if any(not str(d.get(k,'')).strip() for k in required):return self.err(400,'Hãy điền đầy đủ câu hỏi và đáp án.')
   if str(d['answer']).upper() not in 'ABCD' or len(str(d['answer']))!=1:return self.err(400,'Đáp án phải là A, B, C hoặc D.')
   with db() as c:
    cur=c.execute('INSERT INTO questions(subject,grade,topic,content,a,b,c,d,answer,difficulty,explanation,origin) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',tuple(str(d[k]).strip()[:2000] for k in required[:-1])+(d['answer'].upper(),str(d.get('difficulty','Nhận biết'))[:40],str(d.get('explanation',''))[:1000],'manual'))
   return self.sendj(201,{'id':cur.lastrowid})
  if p=='/api/exams':
   title=str(d.get('title','')).strip()[:130];ids=d.get('question_ids',[])
   if not title or not isinstance(ids,list) or not 1<=len(ids)<=100:return self.err(400,'Nhập tên đề và chọn 1–100 câu hỏi.')
   try:ids=list(dict.fromkeys(int(x) for x in ids)); duration=int(d.get('duration',45))
   except:return self.err(400,'Dữ liệu câu hỏi hoặc thời lượng sai.')
   if not 1<=duration<=240:return self.err(400,'Thời gian từ 1 đến 240 phút.')
   with db() as c:
    qs=c.execute(f'SELECT id FROM questions WHERE id IN ({",".join("?" for _ in ids)})',ids).fetchall()
    if len(qs)!=len(ids):return self.err(400,'Có câu hỏi không tồn tại.')
    rng=random.SystemRandom();rng.shuffle(ids)
    cur=c.execute('INSERT INTO exams(title,subject,grade,duration,published) VALUES(?,?,?,?,?)',(title,str(d.get('subject','Tin học'))[:80],str(d.get('grade','9'))[:20],duration,1 if d.get('published') else 0))
    c.executemany('INSERT INTO exam_questions(exam_id,question_id,ord) VALUES(?,?,?)',[(cur.lastrowid,q,i) for i,q in enumerate(ids)])
    eid=cur.lastrowid
   return self.sendj(201,{'id':eid})
  if p=='/api/games':
   title=str(d.get('title','')).strip()[:130];topic=str(d.get('topic','')).strip()[:130];kind=str(d.get('kind','quiz'))
   try:ids=list(dict.fromkeys(int(x) for x in d.get('question_ids',[])))
   except:return self.err(400,'Danh sách câu hỏi không hợp lệ.')
   if not title or not topic or kind not in ('quiz','truefalse') or not 1<=len(ids)<=30:return self.err(400,'Cần tên, chủ đề và 1–30 câu hỏi.')
   with db() as c:
    found=c.execute('SELECT COUNT(*) FROM questions WHERE id IN ('+','.join('?' for _ in ids)+')',ids).fetchone()[0]
    if found!=len(ids):return self.err(400,'Câu hỏi không tồn tại.')
    cur=c.execute('INSERT INTO games(title,topic,kind,question_ids) VALUES(?,?,?,?)',(title,topic,kind,json.dumps(ids)))
   return self.sendj(201,{'id':cur.lastrowid})
  if p=='/api/ai/storyboard':
   topic=str(d.get('topic','')).strip()[:200]
   if not topic:return self.err(400,'Hãy nhập chủ đề bài giảng.')
   try:
    result=gemini_text('Bạn là giáo viên. Tạo kịch bản video giáo dục 60-90 giây bằng tiếng Việt, phù hợp học sinh, không dùng thông tin cá nhân. JSON object gồm title (chuỗi), narration (chuỗi), scenes (mảng 4-6 phần tử, mỗi phần tử có visual, voiceover, seconds). Chủ đề: '+topic)
    if not isinstance(result,dict) or not isinstance(result.get('scenes'),list):raise ValueError()
    content=json.dumps(result,ensure_ascii=False)
    with db() as c:cur=c.execute('INSERT INTO lesson_media(title,kind,content) VALUES(?,?,?)',(str(result.get('title',topic))[:130],'storyboard',content))
    return self.sendj(200,{'id':cur.lastrowid,'storyboard':result,'note':'Đây là kịch bản, KHÔNG phải tệp video. Chức năng tạo video thật chưa được kết nối.'})
   except (RuntimeError,ValueError,KeyError,TypeError) as e:return self.err(502,str(e) if isinstance(e,RuntimeError) else 'Gemini trả kịch bản không hợp lệ.')
  if p=='/api/ai/image':
   prompt=str(d.get('prompt','')).strip()[:600]
   if len(prompt)<8:return self.err(400,'Mô tả ảnh ít nhất 8 ký tự.')
   try:
    response=gemini([{'text':'Tạo một minh họa giáo dục an toàn, rõ nét, không có chữ, không có thông tin nhận dạng học sinh: '+prompt}],model=IMAGE_MODEL,timeout=110,config={'responseModalities':['TEXT','IMAGE']})
    parts=[p for x in response.get('candidates',[]) for p in x.get('content',{}).get('parts',[])]
    item=next((p['inlineData'] for p in parts if 'inlineData' in p),None)
    if not item:raise RuntimeError('Model không trả ảnh. Hãy kiểm tra quyền truy cập và model tạo ảnh Gemini.')
    mime=item.get('mimeType','image/png');ext={'image/png':'png','image/jpeg':'jpg','image/webp':'webp'}.get(mime)
    if not ext:raise RuntimeError('Định dạng ảnh không được hỗ trợ.')
    b=base64.b64decode(item['data'],validate=True)
    if not b or len(b)>8_000_000:raise RuntimeError('Tệp ảnh không hợp lệ hoặc quá lớn.')
    filename=uuid.uuid4().hex+'.'+ext;(MEDIA/filename).write_bytes(b)
    with db() as c:cur=c.execute('INSERT INTO lesson_media(title,kind,content,filename) VALUES(?,?,?,?)',(prompt[:130],'image',prompt,filename))
    return self.sendj(200,{'id':cur.lastrowid,'url':'/media/'+filename,'note':'Ảnh do Gemini tạo. Chỉ lưu trên ổ đĩa máy chủ hiện tại.'})
   except (RuntimeError,ValueError,KeyError,TypeError) as e:return self.err(502,str(e) if isinstance(e,RuntimeError) else 'Gemini trả ảnh không hợp lệ.')
  if p=='/api/ai/generate':
   if not AI_KEY:return self.err(503,'AI chưa cấu hình. Chức năng ngân hàng đề thủ công và chấm trắc nghiệm vẫn hoạt động.')
   subject=str(d.get('subject','Tin học'))[:70];grade=str(d.get('grade','9'))[:20];topic=str(d.get('topic','Thuật toán'))[:130]
   try:n=int(d.get('count',5))
   except:n=5
   if not 1<=n<=10:return self.err(400,'Chỉ tạo 1–10 câu mỗi lần.')
   try:
    data=gemini_text('Tạo '+str(n)+' câu hỏi trắc nghiệm tiếng Việt cho giáo viên, môn '+subject+', lớp '+grade+', chủ đề '+topic+'. Đảm bảo đáp án và giải thích chính xác. Chỉ trả JSON object với questions là danh sách câu hỏi có content,a,b,c,d,answer (A/B/C/D),difficulty,explanation. Không chứa tên học sinh.')
    found=data.get('questions',[]);out=[]
    if not isinstance(found,list):raise ValueError()
    for x in found[:n]:
     if not isinstance(x,dict) or not all(str(x.get(k,'')).strip() for k in ('content','a','b','c','d','answer')) or str(x['answer']).upper() not in ('A','B','C','D'):continue
     out.append({k:str(x.get(k,''))[:2000] for k in ('content','a','b','c','d','answer','difficulty','explanation')})
    if not out:return self.err(502,'Gemini chưa tạo được câu hỏi hợp lệ.')
    return self.sendj(200,{'items':out,'notice':'Câu hỏi Gemini cần được giáo viên duyệt trước khi sử dụng.'})
   except (RuntimeError,ValueError,KeyError,TypeError) as e:return self.err(502,str(e) if isinstance(e,RuntimeError) else 'Gemini trả dữ liệu không hợp lệ.')
  return self.err(404,'Không tìm thấy chức năng.')

if __name__=='__main__':
 if not SECRET:print('CẢNH BÁO: đặt SMARTCLASS_SECRET dài ngẫu nhiên trước khi sử dụng trên internet.')
 if not ADMIN_PASSWORD:print('CẢNH BÁO: chưa đặt SMARTCLASS_ADMIN_PASSWORD, không thể đăng nhập quản trị mới.')
 init();port=int(os.environ.get('PORT','10000'));print(f'SmartClass AI Web listening on {port}',flush=True);ThreadingHTTPServer(('0.0.0.0',port),H).serve_forever()
