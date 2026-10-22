/* SmartClass AI - five real interactive formats using server-verified answers */
(()=>{'use strict';
const root=document.getElementById('gameList'),board=document.getElementById('gamePlay');if(!root||!board)return;
const modes={quiz:'Thử thách trắc nghiệm',flash:'Lật thẻ tri thức',speed:'Đua tốc độ',mystery:'Ô cửa bí mật',ladder:'Leo thang kiến thức'};
const clean=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;','\"':'&quot;'}[c]));
root.addEventListener('click',async e=>{const b=e.target.closest('[data-play-game]');if(!b)return;
 try{const id=Number(b.dataset.playGame),data=await api('games/public/'+id),kind=modes[data.game.kind]?data.game.kind:'quiz';const qs=data.items;
 let pos=0,score=0,streak=0,started=performance.now();
 function render(){if(pos>=qs.length){board.innerHTML=`<div class="card gameBoard"><h3>🎉 Hoàn thành ${clean(data.game.title)}</h3><p>Đúng ${score}/${qs.length} câu · Chuỗi đúng tốt nhất: ${streak}</p><p class="muted">Đây là kết quả luyện tập, không phải điểm bài thi.</p><button class="primary" id="againGame">Chơi lại</button></div>`;document.getElementById('againGame').onclick=()=>{pos=0;score=0;streak=0;started=performance.now();render()};return}
 const q=qs[pos],progress=Math.round(pos/qs.length*100);let heading=clean(q.content);
 if(kind==='mystery')heading=`🔐 Ô cửa số ${pos+1}: `+heading;
 if(kind==='ladder')heading=`🪜 Bậc ${pos+1}: `+heading;
 if(kind==='flash')heading=`🃏 Thẻ ${pos+1}: `+heading;
 if(kind==='speed')heading=`⚡ Câu ${pos+1}: `+heading;
 board.innerHTML=`<div class="card gameBoard"><span class="tag">${modes[kind]} · ${pos+1}/${qs.length}</span><div class="gameProgress"><span style="width:${progress}%"></span></div><h3>${heading}</h3><div id="gameChoices" class="gameChoices ${kind==='flash'?'flashMode':''}">${'ABCD'.split('').map(k=>`<button type="button" class="ghost" data-game-answer="${k}"><b>${k}</b> ${clean(q[k.toLowerCase()])}</button>`).join('')}</div><p id="gameVerdict" role="status" class="muted"></p></div>`;
 board.querySelectorAll('[data-game-answer]').forEach(btn=>btn.addEventListener('click',async()=>{board.querySelectorAll('[data-game-answer]').forEach(x=>x.disabled=true);
 try{const r=await api('games/answer',{game_id:id,question_id:q.id,choice:btn.dataset.gameAnswer});if(r.correct){score++;streak++}else streak=0;
 document.getElementById('gameVerdict').textContent=(r.correct?'✓ Chính xác! ':'Chưa đúng. Đáp án: '+r.answer+'. ')+(r.explanation||'');const next=document.createElement('button');next.className='primary';next.textContent=pos===qs.length-1?'Xem kết quả':'Câu tiếp theo →';next.onclick=()=>{pos++;render()};board.querySelector('.card').appendChild(next);
 }catch(err){document.getElementById('gameVerdict').textContent='Lỗi chấm câu hỏi: '+err.message;board.querySelectorAll('[data-game-answer]').forEach(x=>x.disabled=false)} })); }
 render();board.scrollIntoView({behavior:'smooth',block:'nearest'});
 }catch(err){notice('Không mở được game: '+err.message,true)} });
const f=document.getElementById('planForm');if(!f)return;
const store='smartclass_planner_5512_v1';
try{const d=JSON.parse(localStorage.getItem(store)||'null');if(d)Object.entries(d).forEach(([k,v])=>{const field=f.elements.namedItem(k);if(field)field.value=v})}catch{}
const data=()=>Object.fromEntries(new FormData(f));
function exportHTML(){const d=data();const e=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const field=(name,label)=>`<section><h3>${e(label)}</h3><p>${e(d[name]).replace(/\n/g,'<br>')}</p></section>`;
return `<!doctype html><html lang="vi"><meta charset="utf-8"><title>Kế hoạch bài dạy - ${e(d.title)}</title><style>body{font:14px/1.6 Arial;max-width:800px;margin:35px auto;color:#222}h1{text-align:center;font-size:22px}h2{font-size:18px;margin-top:22px}h3{font-size:15px;margin:12px 0 3px}p{white-space:normal;margin:3px 0 10px}section{break-inside:avoid}@media print{body{margin:15mm}}</style><p>Trường: ${e(d.school)} · Giáo viên: ${e(d.teacher)}</p><h1>KẾ HOẠCH BÀI DẠY</h1><h2>${e(d.title)}</h2><p>Môn: ${e(d.subject)} · Lớp: ${e(d.grade)} · Số tiết: ${e(d.periods)}</p><h2>I. MỤC TIÊU</h2>${field('knowledge','1. Kiến thức')}${field('skills','2. Năng lực')}${field('qualities','3. Phẩm chất')}<h3>Năng lực số: ${e(d.digital)}</h3>${field('digital_evidence','Biểu hiện / minh chứng')}<h2>II. THIẾT BỊ DẠY HỌC VÀ HỌC LIỆU</h2>${field('resources','Thiết bị và học liệu')}<h2>III. TIẾN TRÌNH DẠY HỌC</h2>${field('warmup','1. Hoạt động mở đầu')}${field('explore','2. Hình thành kiến thức')}${field('practice','3. Luyện tập')}${field('apply','4. Vận dụng')}<p><em>Mẫu soạn thảo SmartClass AI theo cấu trúc Phụ lục IV CV5512; giáo viên tự rà soát yêu cầu cần đạt và phân phối chương trình.</em></p></html>`}
document.getElementById('planSave').onclick=()=>{try{localStorage.setItem(store,JSON.stringify(data()));notice('Đã lưu nháp trên trình duyệt này.')}catch{notice('Trình duyệt không cho phép lưu cục bộ.',true)}};
document.getElementById('planExport').onclick=()=>{const blob=new Blob([exportHTML()],{type:'text/html;charset=utf-8'}),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='Ke_hoach_bai_day_5512.html';a.click();setTimeout(()=>URL.revokeObjectURL(url),1500)};
document.getElementById('planPrint').onclick=()=>{const win=window.open('','_blank');if(!win){notice('Hãy cho phép cửa sổ bật lên để in.',true);return}win.document.write(exportHTML());win.document.close();win.focus();win.print()};
})();
