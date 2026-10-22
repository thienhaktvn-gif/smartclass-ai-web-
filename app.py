import os, json, sqlite3, secrets, hashlib, hmac, random, re, urllib.request, urllib.error, base64, uuid, io
from pathlib import Path
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
from http.cookies import SimpleCookie
from datetime import datetime, timezone
from contextvars import ContextVar
import time, threading
from openpyxl import Workbook, load_workbook

SUBJECT_CATALOG=['Toán', 'Ngữ văn', 'Tiếng Anh', 'Vật lí', 'Hóa học', 'Sinh học', 'Lịch sử', 'Địa lí', 'Giáo dục công dân', 'Tin học', 'Công nghệ', 'Khoa học tự nhiên', 'Âm nhạc', 'Mĩ thuật', 'Giáo dục thể chất', 'Hoạt động trải nghiệm']

ROOT=Path(__file__).parent
DB=Path(os.environ.get('SMARTCLASS_DB',str(ROOT/'smartclass.db')))
DB.parent.mkdir(parents=True,exist_ok=True)
SECRET=os.environ.get('SMARTCLASS_SECRET','')
ADMIN_PASSWORD=os.environ.get('SMARTCLASS_ADMIN_PASSWORD','')
ADMIN_USER=os.environ.get('SMARTCLASS_ADMIN_USER','giaovien')
AI_KEY=os.environ.get('GEMINI_API_KEY','')
AI_MODEL=os.environ.get('GEMINI_MODEL','gemini-3.8-flash')
IMAGE_MODEL=os.environ.get('GEMINI_IMAGE_MODEL','gemini-nano-banana-2.1')
VIDEO_MODEL=os.environ.get('GEMINI_VIDEO_MODEL','gemini-omni-1.1-flash')
MEDIA=ROOT/'media';MEDIA.mkdir(exist_ok=True)
PUBLIC_URL=os.environ.get('PUBLIC_URL','')
SESSIONS={}
TENANT=ContextVar('smartclass_tenant', default=None)
TENANT_DIR=DB.parent/'smartclass_teachers'
TENANT_DIR.mkdir(parents=True,exist_ok=True)
RATE={}
RATE_LOCK=threading.Lock()
def throttle(key,limit,window):
 now=time.monotonic()
 with RATE_LOCK:
  a=[t for t in RATE.get(key,[]) if now-t<window]
  if len(a)>=limit:return False
  a.append(now);RATE[key]=a
  return True

def tenant_for(name):
 if not name or name==ADMIN_USER:return None
 return TENANT_DIR/(hashlib.sha256(name.encode('utf8')).hexdigest()+'.sqlite3')


def db():
 c=sqlite3.connect(TENANT.get() or DB,timeout=15); c.row_factory=sqlite3.Row;c.execute('PRAGMA foreign_keys=ON');return c

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
   CREATE TABLE IF NOT EXISTS attendance(id INTEGER PRIMARY KEY,student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,day TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('present','absent','late','excused')),note TEXT DEFAULT '',UNIQUE(student_id,day));
   CREATE TABLE IF NOT EXISTS demo_meta(k TEXT PRIMARY KEY,v TEXT NOT NULL);
  CREATE TABLE IF NOT EXISTS games(id INTEGER PRIMARY KEY,title TEXT NOT NULL,topic TEXT NOT NULL,kind TEXT NOT NULL,question_ids TEXT NOT NULL,created TEXT DEFAULT CURRENT_TIMESTAMP);
  CREATE TABLE IF NOT EXISTS lesson_media(id INTEGER PRIMARY KEY,title TEXT NOT NULL,kind TEXT NOT NULL,content TEXT NOT NULL,filename TEXT DEFAULT '',created TEXT DEFAULT CURRENT_TIMESTAMP);''')
  row=c.execute('SELECT id FROM users WHERE username=?',(ADMIN_USER,)).fetchone()
  if TENANT.get() is None and not row and ADMIN_PASSWORD:
   salt=secrets.token_hex(16);v=hashlib.pbkdf2_hmac('sha256',ADMIN_PASSWORD.encode(),bytes.fromhex(salt),240000).hex()
   c.execute('INSERT INTO users(username,password_hash,role) VALUES(?,?,?)',(ADMIN_USER,salt+':'+v,'teacher'))
  if TENANT.get() is None and c.execute('SELECT COUNT(*) FROM questions').fetchone()[0]==0 and os.getenv('SMARTCLASS_DEMO','0')=='1':
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

def gemini_interaction(model, prompt, media_type, timeout=120):
 if not AI_KEY:raise RuntimeError('Chưa cấu hình GEMINI_API_KEY trên Render.')
 if not re.fullmatch(r'[a-zA-Z0-9_.-]{3,80}', model):raise RuntimeError('Tên model không hợp lệ.')
 if media_type not in ('image','video'):raise ValueError('Loại nội dung không hợp lệ')
 payload={'model':model,'input':prompt,'response_format':{'type':media_type}}
 if media_type=='video':payload['response_format']['resolution']='360p'
 req=urllib.request.Request('https://generativelanguage.googleapis.com/v1beta/interactions', data=json.dumps(payload).encode(),headers={'x-goog-api-key':AI_KEY,'Content-Type':'application/json'},method='POST')
 try:
  with urllib.request.urlopen(req,timeout=timeout) as response: result=json.load(response)
 except urllib.error.HTTPError as exc:
  try: detail=json.loads(exc.read(8192).decode()).get('error',{}).get('message','')
  except Exception:detail=''
  if exc.code==429:raise RuntimeError('Google API giới hạn tạo '+('ảnh' if media_type=='image' else 'video')+' (HTTP 429). Kiểm tra quota model trong Google AI Studio. '+str(detail)[:220])
  if exc.code in (401,403):raise RuntimeError('API Key không được cấp quyền tạo '+('ảnh' if media_type=='image' else 'video')+' (HTTP '+str(exc.code)+').')
  if exc.code==404:raise RuntimeError('Model '+model+' không khả dụng cho dự án hoặc endpoint (HTTP 404).')
  raise RuntimeError('Gemini '+media_type+' HTTP '+str(exc.code)+': '+str(detail)[:250])
 except (urllib.error.URLError,TimeoutError) as exc:raise RuntimeError('Hết thời gian hoặc không kết nối được dịch vụ tạo '+media_type+'.') from exc
 if result.get('status') not in (None,'completed'):
  raise RuntimeError('Google đang xử lý tác vụ '+media_type+'; phản hồi hiện chưa có tệp hoàn chỉnh. Trạng thái: '+str(result.get('status'))[:50])
 for step in result.get('steps',[]):
  for item in step.get('content',[]):
   if item.get('type')==media_type and item.get('data'):
    mime=item.get('mime_type','image/png' if media_type=='image' else 'video/mp4')
    try:raw=base64.b64decode(item['data'],validate=True)
    except Exception:raise RuntimeError('Google trả nội dung base64 không hợp lệ.')
    return raw,mime
 raise RuntimeError('Model không trả '+media_type+' trực tiếp. Kiểm tra quyền truy cập và cấu trúc phản hồi API.')

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
   if n>2500000 or n<1:raise ValueError()
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
  ss=self.session(); TENANT.set(tenant_for(ss['username']) if ss else None)
  p=urlparse(self.path).path
  if p=='/api/registration-status':return self.sendj(200,{'enabled':os.environ.get('SMARTCLASS_ALLOW_REGISTRATION','0')=='1'})
  if p=='/api/subjects':return self.sendj(200,{'items':SUBJECT_CATALOG,'label':'Danh mục môn học dùng chung'})
  if p=='/api/health':return self.sendj(200,{'ok':True,'aiConfigured':bool(AI_KEY),'aiProvider':'Gemini','imageConfigured':bool(AI_KEY),'videoConfigured':bool(AI_KEY),'storage':'sqlite','persistent':os.getenv('SMARTCLASS_PERSISTENT','0')=='1'})
  if p in ('/','/index.html') or p.startswith('/auth/') or p in ('/dashboard','/teacher','/student','/planner','/games'):
   b=(ROOT/'index.html').read_bytes();self.send_response(200);self.send_header('Content-Type','text/html; charset=utf-8');self.send_header('Content-Length',str(len(b)));self.send_header('X-Content-Type-Options','nosniff');self.end_headers();return self.wfile.write(b)
  if p in ('/app.js','/style.css','/ui-motion.js','/learning-addons.js','/portal-enhance.js','/multisubject.js','/accounts.js','/onboarding-fix.js','/showcase-demo.js','/gemini-studio.js'):
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
   if not re.fullmatch(r'[a-f0-9]{32}\.(png|jpg|webp|mp4)',name):return self.err(404,'Không tìm thấy hình ảnh.')
   s=self.session()
   if not s:return self.err(401,'Hãy đăng nhập giáo viên.')
   target=MEDIA/name
   if not target.is_file():return self.err(404,'Không tìm thấy hình ảnh.')
   b=target.read_bytes();self.send_response(200);self.send_header('Content-Type',{'png':'image/png','jpg':'image/jpeg','webp':'image/webp','mp4':'video/mp4'}[name.rsplit('.',1)[1]]);self.send_header('Content-Length',str(len(b)));self.send_header('Cache-Control','private, no-store');self.end_headers();return self.wfile.write(b)
  if p=='/api/students/export':
   if not self.session():return self.err(401,'Vui lòng đăng nhập giáo viên.')
   query=urlparse(self.path).query
   from urllib.parse import parse_qs
   try:cid=int(parse_qs(query).get('class_id',['0'])[0])
   except:return self.err(400,'Mã lớp không hợp lệ.')
   with db() as c:
    cl=c.execute('SELECT name,grade FROM classes WHERE id=?',(cid,)).fetchone()
    if not cl:return self.err(404,'Không tìm thấy lớp.')
    rows=c.execute('SELECT code,name FROM students WHERE class_id=? ORDER BY code',(cid,)).fetchall()
   wb=Workbook();ws=wb.active;ws.title='Danh sach hoc sinh';ws.append(['Mã học sinh','Họ và tên','Lớp'])
   for r in rows:ws.append([r['code'],r['name'],cl['name']])
   ws.column_dimensions['A'].width=22;ws.column_dimensions['B'].width=35;ws.column_dimensions['C'].width=25
   f=io.BytesIO();wb.save(f);data=f.getvalue();self.send_response(200)
   self.send_header('Content-Type','application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
   self.send_header('Content-Disposition',f'attachment; filename="smartclass_lop_{cid}.xlsx"')
   self.send_header('Content-Length',str(len(data)));self.send_header('Cache-Control','no-store');self.end_headers();return self.wfile.write(data)
  if p.startswith('/api/'):
   s=self.session()
   if not s:return self.err(401,'Vui lòng đăng nhập giáo viên.')
   with db() as c:
    if p=='/api/classes':
     rows=c.execute('SELECT c.*,COUNT(s.id) student_count FROM classes c LEFT JOIN students s ON s.class_id=c.id GROUP BY c.id ORDER BY c.id DESC').fetchall()
     return self.sendj(200,{'items':[dict(x) for x in rows]})
    if p=='/api/students':
     return self.sendj(200,{'items':[dict(x) for x in c.execute('SELECT s.*,c.name class_name FROM students s LEFT JOIN classes c ON c.id=s.class_id ORDER BY c.name,s.name')]})
    if p=='/api/attendance':
     from urllib.parse import parse_qs
     q=parse_qs(urlparse(self.path).query)
     day=q.get('day',[''])[0];cid=q.get('class_id',['0'])[0]
     if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',day):return self.err(400,'Ngày không hợp lệ.')
     try:cid=int(cid)
     except:return self.err(400,'Lớp không hợp lệ.')
     items=c.execute('SELECT s.id student_id,s.code,s.name,a.status,a.note FROM students s LEFT JOIN attendance a ON a.student_id=s.id AND a.day=? WHERE s.class_id=? ORDER BY s.name',(day,cid)).fetchall()
     return self.sendj(200,{'items':[dict(x) for x in items], 'day':day})
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
  ss=self.session(); TENANT.set(tenant_for(ss['username']) if ss else None)
  p=urlparse(self.path).path;d=self.body()
  if d is None:return self.err(400,'Dữ liệu JSON không hợp lệ hoặc quá lớn.')
  if p=='/api/register':
   if os.environ.get('SMARTCLASS_ALLOW_REGISTRATION','0')!='1':return self.err(403,'Đăng ký hiện tạm khóa. Quản trị cần bật SMARTCLASS_ALLOW_REGISTRATION=1 sau khi cấu hình nơi lưu dữ liệu bền vững.')
   address=self.client_address[0]
   if not throttle('register:'+address,5,3600):return self.err(429,'Bạn đã tạo quá nhiều yêu cầu đăng ký.')
   name=str(d.get('username','')).strip().lower(); pw=str(d.get('password',''))
   if not re.fullmatch(r'[a-z][a-z0-9_.-]{4,31}',name):return self.err(400,'Tên đăng nhập gồm 5–32 ký tự không dấu, bắt đầu bằng chữ cái.')
   if name==ADMIN_USER:return self.err(409,'Tên đăng nhập không khả dụng.')
   if len(pw)<12 or len(pw)>128 or not re.search('[A-Z]',pw) or not re.search('[a-z]',pw) or not re.search('[0-9]',pw):return self.err(400,'Mật khẩu cần 12–128 ký tự, gồm chữ hoa, chữ thường và chữ số.')
   TENANT.set(None)
   with db() as c:
    if c.execute('SELECT 1 FROM users WHERE username=?',(name,)).fetchone():return self.err(409,'Tên đăng nhập đã được sử dụng.')
    c.execute('INSERT INTO users(username,password_hash,role) VALUES(?,?,?)',(name,hashpw(pw),'teacher'))
   TENANT.set(tenant_for(name));init();TENANT.set(None)
   return self.sendj(201,{'ok':True,'message':'Tạo tài khoản thành công. Mời đăng nhập.'})
  if p=='/api/login':
   if not throttle('login:'+self.client_address[0],15,900):return self.err(429,'Có quá nhiều lần thử đăng nhập. Vui lòng thử lại sau.')
   name=str(d.get('username','')).strip().lower()[:100];pw=str(d.get('password',''))
   TENANT.set(None)
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
  if p=='/api/planner/docx':
   from docx import Document
   from docx.shared import Cm, Pt
   from docx.enum.text import WD_ALIGN_PARAGRAPH
   textfields=['school','teacher','subject','grade','title','periods','knowledge','skills','qualities','digital','digital_evidence','resources','warmup','explore','practice','apply']
   vals={k:str(d.get(k,'')).strip()[:8000] for k in textfields}
   if not vals['title'] or not vals['subject']:return self.err(400,'Vui lòng nhập môn học và tên bài dạy.')
   doc=Document();sec=doc.sections[0];sec.top_margin=Cm(2);sec.bottom_margin=Cm(2);sec.left_margin=Cm(2.5);sec.right_margin=Cm(2)
   normal=doc.styles['Normal'];normal.font.name='Times New Roman';normal.font.size=Pt(13)
   top=doc.add_paragraph(f"Trường: {vals['school']}\nGiáo viên: {vals['teacher']}")
   heading=doc.add_heading('KẾ HOẠCH BÀI DẠY',0);heading.alignment=WD_ALIGN_PARAGRAPH.CENTER
   doc.add_heading(vals['title'],level=1)
   doc.add_paragraph(f"Môn học: {vals['subject']}     Lớp: {vals['grade']}     Thời gian thực hiện: {vals['periods']} tiết")
   doc.add_heading('I. MỤC TIÊU',level=1)
   for title,key in [('1. Kiến thức','knowledge'),('2. Năng lực','skills'),('3. Phẩm chất','qualities'),('4. Năng lực số dự kiến phát triển','digital'),('Minh chứng đánh giá năng lực số','digital_evidence')]:
    doc.add_heading(title,level=2);doc.add_paragraph(vals[key] or '(Giáo viên bổ sung)')
   doc.add_heading('II. THIẾT BỊ DẠY HỌC VÀ HỌC LIỆU',level=1);doc.add_paragraph(vals['resources'])
   doc.add_heading('III. TIẾN TRÌNH DẠY HỌC',level=1)
   for title,key in [('Hoạt động 1. Mở đầu','warmup'),('Hoạt động 2. Hình thành kiến thức','explore'),('Hoạt động 3. Luyện tập','practice'),('Hoạt động 4. Vận dụng','apply')]:
    doc.add_heading(title,level=2);doc.add_paragraph(vals[key] or '(Giáo viên bổ sung mục tiêu, nội dung, sản phẩm, tổ chức thực hiện)')
   doc.add_paragraph('Lưu ý: Mẫu hỗ trợ soạn theo Phụ lục IV CV5512; giáo viên tự rà soát nội dung và yêu cầu chuyên môn.')
   buffer=io.BytesIO();doc.save(buffer);raw=buffer.getvalue();self.send_response(200)
   self.send_header('Content-Type','application/vnd.openxmlformats-officedocument.wordprocessingml.document')
   self.send_header('Content-Disposition','attachment; filename="Ke_hoach_bai_day_5512.docx"')
   self.send_header('Content-Length',str(len(raw)));self.send_header('Cache-Control','no-store');self.end_headers();return self.wfile.write(raw)
  if p=='/api/classes':
   name=str(d.get('name','')).strip()[:100];grade=str(d.get('grade','')).strip()[:25]
   if len(name)<2:return self.err(400,'Tên lớp cần ít nhất 2 ký tự.')
   try:
    with db() as c:cur=c.execute('INSERT INTO classes(name,grade) VALUES(?,?)',(name,grade));idx=cur.lastrowid
    return self.sendj(201,{'id':idx})
   except sqlite3.IntegrityError:return self.err(409,'Lớp đã tồn tại.')
  if p=='/api/students':
   name=str(d.get('name','')).strip()[:100];code=str(d.get('code','')).strip()[:40]
   try:cid=int(d.get('class_id',0))
   except:return self.err(400,'Chọn lớp hợp lệ.')
   if len(name)<2 or not re.fullmatch(r'[A-Za-z0-9_.-]{2,40}',code):return self.err(400,'Tên hoặc mã học sinh không hợp lệ (mã chỉ dùng chữ, số, dấu -_.).')
   try:
    with db() as c:
     if not c.execute('SELECT 1 FROM classes WHERE id=?',(cid,)).fetchone():return self.err(404,'Không tìm thấy lớp.')
     cur=c.execute('INSERT INTO students(code,name,class_id) VALUES(?,?,?)',(code,name,cid));idx=cur.lastrowid
    return self.sendj(201,{'id':idx})
   except sqlite3.IntegrityError:return self.err(409,'Mã học sinh đã tồn tại.')
  if p=='/api/students/delete':
   try:sid=int(d.get('id'))
   except:return self.err(400,'Mã học sinh không hợp lệ.')
   with db() as c:
    c.execute('DELETE FROM attendance WHERE student_id=?',(sid,));cur=c.execute('DELETE FROM students WHERE id=?',(sid,))
   return self.sendj(200,{'deleted':cur.rowcount})
  if p=='/api/attendance':
   day=str(d.get('day',''));rows=d.get('items',[])
   if not re.fullmatch(r'\d{4}-\d{2}-\d{2}',day) or not isinstance(rows,list) or len(rows)>150:return self.err(400,'Dữ liệu điểm danh không hợp lệ.')
   try:datetime.strptime(day,'%Y-%m-%d')
   except:return self.err(400,'Ngày không hợp lệ.')
   allowed=('present','absent','late','excused')
   parsed=[]
   for r in rows:
    try:sid=int(r['student_id']);status=str(r['status']);note=str(r.get('note',''))[:200]
    except:return self.err(400,'Dữ liệu học sinh không hợp lệ.')
    if status not in allowed:return self.err(400,'Trạng thái điểm danh không hợp lệ.')
    parsed.append((sid,day,status,note))
   with db() as c:
    found=c.execute('SELECT COUNT(*) FROM students WHERE id IN ('+','.join('?' for _ in parsed)+')',[a[0] for a in parsed]).fetchone()[0] if parsed else 0
    if found!=len(set(a[0] for a in parsed)) or found!=len(parsed):return self.err(400,'Có mã học sinh không hợp lệ hoặc trùng.')
    c.executemany('INSERT INTO attendance(student_id,day,status,note) VALUES(?,?,?,?) ON CONFLICT(student_id,day) DO UPDATE SET status=excluded.status,note=excluded.note',parsed)
   return self.sendj(200,{'saved':len(parsed),'day':day})
  if p=='/api/students/import':
   try:
    cid=int(d.get('class_id'));raw=base64.b64decode(str(d.get('file','')),validate=True)
    if len(raw)>1200000:return self.err(400,'Tệp Excel tối đa 1,2 MB.')
    wb=load_workbook(io.BytesIO(raw),read_only=True,data_only=True)
    ws=wb.active;entries=[]
    for row in list(ws.iter_rows(min_row=2,max_col=2,values_only=True))[:300]:
     code=str(row[0] or '').strip();name=str(row[1] or '').strip()
     if not code and not name:continue
     if not re.fullmatch(r'[A-Za-z0-9_.-]{2,40}',code) or not 2<=len(name)<=100:raise ValueError('Mã/họ tên không hợp lệ trong Excel.')
     entries.append((code,name,cid))
    wb.close()
    if not entries:return self.err(400,'Không có học sinh hợp lệ trong Excel.')
    if len(set(x[0] for x in entries))!=len(entries):return self.err(400,'Mã học sinh trùng trong Excel.')
    with db() as c:
     if not c.execute('SELECT 1 FROM classes WHERE id=?',(cid,)).fetchone():return self.err(404,'Không tìm thấy lớp.')
     c.executemany('INSERT INTO students(code,name,class_id) VALUES(?,?,?) ON CONFLICT(code) DO UPDATE SET name=excluded.name,class_id=excluded.class_id',entries)
    return self.sendj(200,{'imported':len(entries)})
   except (ValueError,KeyError,TypeError,base64.binascii.Error,sqlite3.Error,Exception) as e:return self.err(400,'Không đọc được Excel. Hãy dùng mẫu xuất từ SmartClassAI, tối đa 300 học sinh.')
  if p=='/api/demo/multisubject':
   # Teacher-only demo fixture. Never pass demo scores off as genuine learning outcomes.
   sample=[('Toán', '8', 'Đại số', 'Giá trị của 3² là bao nhiêu?', '6', '9', '12', '8', 'B', 'Nhận biết', '3² = 3 × 3 = 9.', 'demo-multisubject'), ('Ngữ văn', '8', 'Tiếng Việt', 'Từ nào sau đây là từ láy?', 'Học sinh', 'Lấp lánh', 'Sách vở', 'Bàn ghế', 'B', 'Nhận biết', 'Lấp lánh là từ láy.', 'demo-multisubject'), ('Tiếng Anh', '8', 'Ngữ pháp', 'Choose the correct form: She ___ to school every day.', 'go', 'goes', 'going', 'gone', 'B', 'Nhận biết', 'She goes: ngôi thứ ba số ít ở hiện tại đơn.', 'demo-multisubject'), ('Vật lí', '8', 'Chuyển động', 'Đơn vị SI của vận tốc là gì?', 'm/s', 'kg', 'N', 'J', 'A', 'Nhận biết', 'Vận tốc có đơn vị SI là mét trên giây.', 'demo-multisubject'), ('Hóa học', '8', 'Chất và nguyên tử', 'Kí hiệu hóa học của nguyên tố oxi là gì?', 'Ox', 'O', 'Om', 'H', 'B', 'Nhận biết', 'O là kí hiệu nguyên tố oxi.', 'demo-multisubject'), ('Sinh học', '8', 'Tế bào', 'Bộ phận nào giúp tế bào thực vật quang hợp?', 'Nhân', 'Lục lạp', 'Màng sinh chất', 'Không bào', 'B', 'Nhận biết', 'Lục lạp có diệp lục thực hiện quang hợp.', 'demo-multisubject'), ('Lịch sử', '8', 'Lịch sử Việt Nam', 'Chiến thắng Bạch Đằng năm 938 gắn với ai?', 'Ngô Quyền', 'Trần Hưng Đạo', 'Lê Lợi', 'Quang Trung', 'A', 'Nhận biết', 'Ngô Quyền lãnh đạo chiến thắng Bạch Đằng năm 938.', 'demo-multisubject'), ('Địa lí', '8', 'Địa lí tự nhiên', 'Lớp khí bao quanh Trái Đất được gọi là gì?', 'Thủy quyển', 'Khí quyển', 'Thạch quyển', 'Sinh quyển', 'B', 'Nhận biết', 'Khí quyển là lớp khí bao quanh Trái Đất.', 'demo-multisubject'), ('Giáo dục công dân', '8', 'Quyền và nghĩa vụ', 'Hành vi nào thể hiện tôn trọng người khác?', 'Lắng nghe ý kiến', 'Chế giễu bạn', 'Ngắt lời', 'Lan truyền tin đồn', 'A', 'Nhận biết', 'Lắng nghe là biểu hiện tôn trọng.', 'demo-multisubject'), ('Tin học', '8', 'An toàn số', 'Mật khẩu nào an toàn hơn?', '123456', 'password', 'Một mật khẩu dài và riêng biệt', 'Ngày sinh', 'C', 'Nhận biết', 'Mật khẩu dài, khó đoán và riêng cho từng tài khoản an toàn hơn.', 'demo-multisubject'), ('Công nghệ', '8', 'Thiết kế kĩ thuật', 'Bước đầu của quy trình thiết kế kĩ thuật là gì?', 'Chế tạo hàng loạt', 'Xác định vấn đề', 'Đóng gói sản phẩm', 'Quảng cáo', 'B', 'Nhận biết', 'Cần xác định vấn đề trước khi đề xuất giải pháp.', 'demo-multisubject'), ('Khoa học tự nhiên', '8', 'Kĩ năng thực nghiệm', 'Dụng cụ nào thường dùng để đo nhiệt độ?', 'Thước', 'Cân', 'Nhiệt kế', 'Đồng hồ', 'C', 'Nhận biết', 'Nhiệt kế dùng để đo nhiệt độ.', 'demo-multisubject'), ('Âm nhạc', '8', 'Nhạc lí', 'Một nốt đen thông thường có trường độ bằng mấy nốt móc đơn?', '1', '2', '3', '4', 'B', 'Nhận biết', 'Một nốt đen bằng hai nốt móc đơn.', 'demo-multisubject'), ('Mĩ thuật', '8', 'Màu sắc', 'Ba màu cơ bản truyền thống trong hội họa là gì?', 'Đỏ, vàng, xanh lam', 'Đen, trắng, xám', 'Lục, tím, nâu', 'Cam, lục, tím', 'A', 'Nhận biết', 'Bộ màu cơ bản truyền thống: đỏ, vàng, xanh lam.', 'demo-multisubject'), ('Giáo dục thể chất', '8', 'An toàn luyện tập', 'Trước khi vận động mạnh nên làm gì?', 'Bỏ khởi động', 'Khởi động phù hợp', 'Uống thật nhiều nước một lúc', 'Tập ngay tối đa', 'B', 'Nhận biết', 'Khởi động giúp chuẩn bị cơ thể cho vận động.', 'demo-multisubject'), ('Hoạt động trải nghiệm', '8', 'Kĩ năng hợp tác', 'Khi làm việc nhóm, cách nào giúp hợp tác hiệu quả?', 'Không chia sẻ nhiệm vụ', 'Phân công rõ và lắng nghe', 'Chỉ nghe một người', 'Không phản hồi', 'B', 'Nhận biết', 'Phân công và lắng nghe giúp nhóm hợp tác.', 'demo-multisubject')]
   made=0
   with db() as c:
    for row in sample:
     exists=c.execute('SELECT id FROM questions WHERE subject=? AND content=? AND origin=?',(row[0],row[3],'demo-multisubject')).fetchone()
     if exists:continue
     c.execute('INSERT INTO questions(subject,grade,topic,content,a,b,c,d,answer,difficulty,explanation,origin) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',row)
     made+=1
    for subject in SUBJECT_CATALOG:
     qids=[v[0] for v in c.execute('SELECT id FROM questions WHERE subject=? AND origin=? ORDER BY id LIMIT 10',(subject,'demo-multisubject')).fetchall()]
     if not qids:continue
     title='Ôn tập '+subject+' [MINH HỌA]'
     if c.execute('SELECT 1 FROM exams WHERE title=?',(title,)).fetchone():continue
     eid=c.execute('INSERT INTO exams(title,subject,grade,duration,published) VALUES(?,?,?,?,0)',(title,subject,'8',15)).lastrowid
     c.executemany('INSERT INTO exam_questions(exam_id,question_id,ord) VALUES(?,?,?)',[(eid,q,i) for i,q in enumerate(qids)])
   return self.sendj(200,{'ok':True,'added':made,'subjects':len(SUBJECT_CATALOG),'notice':'DỮ LIỆU MINH HỌA: Giáo viên phải rà soát đáp án và sửa theo chương trình từng lớp. Đề mẫu mặc định chưa công bố.'})
  if p=='/api/demo/showcase':
   # Teacher-authenticated, reversible-by-selecting-demo-data fixture. No fabricated student outcomes.
   added={'games':0,'media':0,'attendance':0,'draft_exams':0}
   with db() as c:
    subjects=[r[0] for r in c.execute("SELECT DISTINCT subject FROM questions WHERE origin='demo-multisubject' ORDER BY subject")]
    for subject in subjects:
     ids=[r[0] for r in c.execute("SELECT id FROM questions WHERE subject=? AND origin='demo-multisubject' ORDER BY id LIMIT 10",(subject,))]
     if not ids:continue
     for kind,label in [('quiz','Trắc nghiệm'),('flash','Lật thẻ'),('speed','Đua tốc độ'),('mystery','Ô cửa bí mật'),('ladder','Leo thang')]:
      name=f'{label} · {subject} [MINH HỌA]'
      if not c.execute('SELECT id FROM games WHERE title=?',(name,)).fetchone():
       c.execute('INSERT INTO games(title,topic,kind,question_ids) VALUES(?,?,?,?)',(name,subject,kind,json.dumps(ids)))
       added['games']+=1
    lesson_title='Kế hoạch bài dạy mẫu · Toán 8 [MINH HỌA]'
    planner={ 'school':'TRƯỜNG THCS MINH HỌA', 'teacher':'GIÁO VIÊN MINH HỌA', 'subject':'Toán', 'grade':'8', 'periods':'1', 'title':'Hằng đẳng thức đáng nhớ (dữ liệu minh họa)', 'knowledge':'Nhận biết và vận dụng công thức bình phương một tổng.', 'skills':'Tư duy và lập luận toán học; giải quyết vấn đề.', 'qualities':'Chăm chỉ, trung thực trong trình bày lời giải.', 'digital':'Khai thác thông tin và dữ liệu; sáng tạo nội dung số', 'digital_evidence':'Sử dụng bảng tính hoặc công cụ trực tuyến để kiểm tra các ví dụ.', 'resources':'Máy chiếu; phiếu học tập; công cụ số phù hợp.', 'warmup':'Nêu tình huống tính nhanh (a+b)²; học sinh dự đoán kết quả.', 'explore':'Hướng dẫn hình thành công thức và giải thích bằng mô hình diện tích.', 'practice':'Học sinh thực hiện 3 bài tập có mức độ tăng dần, đối chiếu và sửa lỗi.', 'apply':'Vận dụng công thức giải một bài toán thực tiễn; ghi nhận sản phẩm.' }
    if not c.execute('SELECT id FROM lesson_media WHERE title=?',(lesson_title,)).fetchone():
     c.execute('INSERT INTO lesson_media(title,kind,content) VALUES(?,?,?)',(lesson_title,'planner-sample',json.dumps(planner,ensure_ascii=False)))
     added['media']+=1
    storyboard_title='Kịch bản học liệu · An toàn số [MINH HỌA]'
    storyboard={'title':storyboard_title,'note':'Dữ liệu minh họa, không phải video tạo thật','scenes':[{'scene':1,'visual':'Học sinh thảo luận về mật khẩu mạnh','narration':'Không dùng chung mật khẩu.'},{'scene':2,'visual':'Minh họa xác thực hai yếu tố','narration':'Hãy bật xác thực bổ sung khi có thể.'}]}
    if not c.execute('SELECT id FROM lesson_media WHERE title=?',(storyboard_title,)).fetchone():
     c.execute('INSERT INTO lesson_media(title,kind,content) VALUES(?,?,?)',(storyboard_title,'storyboard',json.dumps(storyboard,ensure_ascii=False)))
     added['media']+=1
   return self.sendj(200,{'ok':True,'added':added,'subjects':len(subjects),'notice':'CHỈ LÀ DỮ LIỆU MINH HỌA: Không tạo bài làm, điểm số hay sản phẩm AI giả. Game cần câu hỏi mẫu đa môn đã được tạo trước.'})
  if p=='/api/demo/seed':
   with db() as c:
    if c.execute("SELECT 1 FROM demo_meta WHERE k='seeded'").fetchone():return self.sendj(200,{'ok':True,'already':True})
    classes=[('9A - Minh họa','9'),('8B - Minh họa','8')]
    ids=[]
    for name,grade in classes:
     c.execute('INSERT OR IGNORE INTO classes(name,grade) VALUES(?,?)',(name,grade))
     ids.append(c.execute('SELECT id FROM classes WHERE name=?',(name,)).fetchone()[0])
    sample=[('DEMO901','Nguyễn Minh Anh',ids[0]),('DEMO902','Trần Hải Nam',ids[0]),('DEMO903','Lê Thu Hà',ids[0]),('DEMO904','Phạm Gia Bảo',ids[0]),('DEMO905','Võ Ngọc Linh',ids[0]),('DEMO801','Đỗ Minh Khang',ids[1]),('DEMO802','Hoàng Thảo Vy',ids[1]),('DEMO803','Bùi Đức An',ids[1])]
    for code,name,cid in sample:c.execute('INSERT OR IGNORE INTO students(code,name,class_id) VALUES(?,?,?)',(code,name,cid))
    day=datetime.now().strftime('%Y-%m-%d')
    for i,(code,_,_) in enumerate(sample):
     sid=c.execute('SELECT id FROM students WHERE code=?',(code,)).fetchone()[0]
     c.execute('INSERT OR IGNORE INTO attendance(student_id,day,status) VALUES(?,?,?)',(sid,day,['present','present','late','present','absent','present','excused','present'][i]))
    demo_q=[
     ('Trong Python, lệnh nào kiểm tra điều kiện?','for','if','def','while','B','Câu lệnh if dùng kiểm tra điều kiện.'),
     ('Hàm nào tạo dãy số nguyên trong Python?','range','input','print','len','A','range tạo dãy giá trị.'),
     ('Chỉ số đầu tiên của list trong Python là gì?','1','-1','0','2','C','List đánh chỉ số từ 0.'),
     ('Tìm kiếm nhị phân yêu cầu dữ liệu thế nào?','Ngẫu nhiên','Được sắp xếp','Chỉ số chẵn','Không trùng','B','Dữ liệu phải được sắp xếp.'),
     ('Giá trị của 3 * 4 bằng bao nhiêu?','7','12','34','1','B','Phép nhân cho kết quả 12.'),
     ('Kiểu dữ liệu đúng/sai trong Python là?','int','str','bool','list','C','bool nhận True hoặc False.'),
     ('Vòng lặp nào duyệt lần lượt từng phần tử?','for','if','def','return','A','for dùng để lặp.'),
     ('Độ phức tạp của duyệt tuần tự n phần tử là?','O(1)','O(n)','O(log n)','O(n²)','B','Mỗi phần tử được xét tối đa một lần.')]
    ids=[]
    for text,a,b,copt,dopt,answer,exp in demo_q:
     row=c.execute('SELECT id FROM questions WHERE content=? AND origin=?',(text,'demo_contest')).fetchone()
     if row:ids.append(row[0]);continue
     cur=c.execute('INSERT INTO questions(subject,grade,topic,content,a,b,c,d,answer,difficulty,explanation,origin) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)',('Tin học','9','Thuật toán - minh họa',text,a,b,copt,dopt,answer,'Nhận biết',exp,'demo_contest'))
     ids.append(cur.lastrowid)
    title='Đề luyện tập Tin học 9 [MINH HỌA]'
    eidrow=c.execute('SELECT id FROM exams WHERE title=?',(title,)).fetchone()
    if not eidrow:
     eid=c.execute('INSERT INTO exams(title,subject,grade,duration,published) VALUES(?,?,?,?,?)',(title,'Tin học','9',20,1)).lastrowid
     c.executemany('INSERT INTO exam_questions(exam_id,question_id,ord) VALUES(?,?,?)',[(eid,q,i) for i,q in enumerate(ids)])
    if not c.execute('SELECT 1 FROM games WHERE title=?',('Thử thách thuật toán [MINH HỌA]',)).fetchone():
     c.execute('INSERT INTO games(title,topic,kind,question_ids) VALUES(?,?,?,?)',('Thử thách thuật toán [MINH HỌA]','Tin học','quiz',json.dumps(ids[:6])))
    for title,kind in [('Lật thẻ tri thức [MINH HỌA]','flash'),('Đua tốc độ Python [MINH HỌA]','speed'),('Ô cửa bí mật [MINH HỌA]','mystery'),('Leo thang kiến thức [MINH HỌA]','ladder')]:
     c.execute('INSERT INTO games(title,topic,kind,question_ids) VALUES(?,?,?,?)',(title,'Tin học',kind,json.dumps(ids[:6])))
    c.execute("INSERT INTO demo_meta(k,v) VALUES('seeded','1')")
   return self.sendj(200,{'ok':True,'classes':2,'students':8,'label':'DỮ LIỆU MINH HỌA'})
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
   if not title or not topic or kind not in ('quiz','flash','speed','mystery','ladder') or not 1<=len(ids)<=30:return self.err(400,'Cần tên, chủ đề và 1–30 câu hỏi.')
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
  if p in ('/api/ai/image','/api/ai/video'):
   media_type='image' if p.endswith('/image') else 'video'
   prompt=str(d.get('prompt','')).strip()[:600]
   if len(prompt)<8:return self.err(400,'Mô tả cần ít nhất 8 ký tự.')
   model=IMAGE_MODEL if media_type=='image' else VIDEO_MODEL
   try:
    description='Tạo một minh họa giáo dục an toàn, không có thông tin cá nhân học sinh: ' if media_type=='image' else 'Tạo video ngắn phục vụ dạy học, không sử dụng hình ảnh hay thông tin nhận dạng trẻ em thật: '
    raw,mime=gemini_interaction(model,description+prompt,media_type,timeout=150)
    allowed={'image':{'image/png':'png','image/jpeg':'jpg','image/webp':'webp'},'video':{'video/mp4':'mp4'}}[media_type]
    ext=allowed.get(mime)
    if not ext or not raw or len(raw)>30_000_000:raise RuntimeError('Tệp trả về không hợp lệ, quá lớn hoặc sai định dạng.')
    filename=uuid.uuid4().hex+'.'+ext;(MEDIA/filename).write_bytes(raw)
    with db() as c:cur=c.execute('INSERT INTO lesson_media(title,kind,content,filename) VALUES(?,?,?,?)',(prompt[:130],media_type,prompt,filename))
    return self.sendj(200,{'id':cur.lastrowid,'url':'/media/'+filename,'kind':media_type,'note':'Nội dung AI tạo thực tế; tệp trên Render Free có thể mất khi khởi động lại.'})
   except (RuntimeError,ValueError,KeyError,TypeError) as e:return self.err(502,str(e) if isinstance(e,RuntimeError) else 'Gemini trả tệp không hợp lệ.')
  if p=='/api/ai/generate':
   if not AI_KEY:return self.err(503,'AI chưa cấu hình. Chức năng ngân hàng đề thủ công và chấm trắc nghiệm vẫn hoạt động.')
   subject=str(d.get('subject','Tin học'))[:70];grade=str(d.get('grade','9'))[:20];topic=str(d.get('topic','Thuật toán'))[:130]
   try:n=int(d.get('count',5))
   except:n=5
   if not 1<=n<=10:return self.err(400,'Chỉ tạo 1–10 câu mỗi lần.')
   try:
    data=gemini_text('Tạo '+str(n)+' câu hỏi trắc nghiệm tiếng Việt cho giáo viên, môn '+subject+', lớp '+grade+', chủ đề '+topic+'. Đảm bảo đáp án và giải thích chính xác. Chỉ trả JSON object với questions là danh sách câu hỏi có content,a,b,c,d,answer (A/B/C/D),difficulty,explanation. Không chứa tên học sinh.')
    # Gemini sometimes returns a top-level JSON array instead of {"questions": [...]}.
    # Validate before accessing object methods to avoid aborting the HTTP connection.
    if isinstance(data,list):found=data
    elif isinstance(data,dict):found=data.get('questions',[])
    else:raise ValueError('Cấu trúc phản hồi Gemini không hợp lệ.')
    out=[]
    if not isinstance(found,list):raise ValueError('Danh sách câu hỏi Gemini không hợp lệ.')
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
