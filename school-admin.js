(()=>{'use strict';
const page=document.getElementById('classes');if(!page)return;
const box=document.createElement('section');box.className='card';box.style.margin='16px 0';box.innerHTML=`<h3>🏫 Quản lý danh sách toàn trường</h3><p><b>Excel cần 3 cột:</b> Mã học sinh | Họ và tên | Lớp. Tự tạo lớp chưa có, tự phân lớp theo từng dòng. Tối đa 2.000 em/lần.</p><label>Chọn file toàn trường (.xlsx) <input id="schoolXlsx" type="file" accept=".xlsx"></label><div class="flex"><button type="button" class="primary" id="schoolPreview">1. Xem trước phân lớp</button><button type="button" class="ghost" id="schoolImport" disabled>2. Xác nhận nhập toàn trường</button></div><p id="schoolResult" role="status" class="muted"></p><details><summary>Di chuyển/xóa học sinh đã nhập nhầm</summary><div class="flex"><button type="button" id="schoolSelectFiltered" class="ghost">Chọn tất cả học sinh đang hiển thị</button><button type="button" id="schoolUnselect" class="ghost">Bỏ chọn</button></div><p id="schoolSelected">0 học sinh được chọn</p><label>Chuyển sang lớp <select id="schoolDestination"></select></label><div class="flex"><button type="button" id="schoolMove" class="primary">Chuyển học sinh đã chọn</button><button type="button" id="schoolDelete" class="ghost">Xóa học sinh đã chọn</button></div><p class="muted">Hãy xuất bản sao Excel trước khi xóa. Xóa học sinh sẽ xóa cả thông tin điểm danh liên quan.</p></details>`;
const title=page.querySelector('.sectionHead');title?.after(box);
const get=id=>document.getElementById(id),status=get('schoolResult');
// Deactivate legacy import action that forces every Excel row into one selected class.
const legacy=get('importExcel');if(legacy){const replacement=legacy.cloneNode(true);replacement.textContent='Dùng nhập toàn trường phía trên';replacement.onclick=()=>box.scrollIntoView({behavior:'smooth'});legacy.replaceWith(replacement);}
let raw=null,selected=new Set(),preview=null;
async function request(path,payload){const me=await fetch('/api/me',{credentials:'same-origin'}).then(r=>r.json());if(!me.csrf)throw Error('Vui lòng đăng nhập giáo viên.');const r=await fetch('/api/'+path,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':me.csrf},body:JSON.stringify(payload)});const t=await r.text();let d;try{d=JSON.parse(t)}catch{throw Error('Máy chủ trả phản hồi không hợp lệ (HTTP '+r.status+').')}if(!r.ok)throw Error(d.error||'HTTP '+r.status);return d}
function format(d){return Object.entries(d.classes).map(([c,n])=>c+': '+n+' em').join(' · ')}
get('schoolXlsx').addEventListener('change',()=>{raw=null;preview=null;get('schoolImport').disabled=true;status.textContent='Chưa xem trước danh sách.'});
get('schoolPreview').onclick=async()=>{const f=get('schoolXlsx').files[0];if(!f||!f.name.toLowerCase().endsWith('.xlsx')||f.size>2500000){status.textContent='Chọn file Excel .xlsx tối đa 2,5 MB.';return}status.textContent='Đang đọc danh sách…';try{raw=await new Promise((resolve,reject)=>{const rd=new FileReader();rd.onload=()=>{const bytes=new Uint8Array(rd.result);let b='';for(let i=0;i<bytes.length;i+=8192)b+=String.fromCharCode(...bytes.subarray(i,i+8192));resolve(btoa(b))};rd.onerror=reject;rd.readAsArrayBuffer(f)});preview=await request('students/import',{file:raw,preview:true});get('schoolImport').disabled=false;status.textContent='Xem trước '+preview.total+' học sinh: '+format(preview)+'. Kiểm tra đúng các lớp trước khi nhập.'}catch(e){status.textContent=e.message;get('schoolImport').disabled=true}};
get('schoolImport').onclick=async()=>{if(!raw||!preview)return;if(!confirm('Xác nhận nhập '+preview.total+' học sinh, tự phân lớp theo Excel? Học sinh trùng mã sẽ được cập nhật lớp và họ tên.'))return;get('schoolImport').disabled=true;try{const d=await request('students/import',{file:raw,confirm:'NHAP_TOAN_TRUONG'});status.textContent='Thành công: thêm '+d.created+', cập nhật '+d.updated+', lớp mới '+d.classes_created+'. '+format(d);await loadClasses()}catch(e){status.textContent=e.message}finally{get('schoolImport').disabled=false}};
function updateSelected(){get('schoolSelected').textContent=selected.size+' học sinh được chọn'}
function syncRows(){const list=get('studentList');if(!list)return;list.querySelectorAll('[data-delete-student]').forEach(btn=>{const id=+btn.dataset.deleteStudent;const line=btn.closest('.item');if(!line||line.querySelector('.school-select'))return;const c=document.createElement('input');c.type='checkbox';c.className='school-select';c.dataset.sid=id;c.checked=selected.has(id);c.setAttribute('aria-label','Chọn học sinh để chuyển lớp');line.prepend(c);const move=document.createElement('button');move.type='button';move.className='ghost small';move.textContent='Chuyển lớp';move.dataset.schoolMove=id;btn.before(move)});const destination=get('schoolDestination');const old=destination.value;const select=get('filterClass');destination.innerHTML=[...select.options].filter(o=>o.value!=='0').map(o=>'<option value="'+o.value+'">'+o.textContent+'</option>').join('');if([...destination.options].some(o=>o.value===old))destination.value=old}
let busy=false;const obs=new MutationObserver(()=>{if(busy)return;busy=true;obs.disconnect();syncRows();obs.observe(get('studentList'),{childList:true,subtree:true});busy=false});obs.observe(get('studentList'),{childList:true,subtree:true});syncRows();
page.addEventListener('change',e=>{if(e.target.matches('.school-select')){const id=+e.target.dataset.sid;e.target.checked?selected.add(id):selected.delete(id);updateSelected()}});
get('schoolSelectFiltered').onclick=()=>{get('studentList').querySelectorAll('.school-select').forEach(c=>{c.checked=true;selected.add(+c.dataset.sid)});updateSelected()};
get('schoolUnselect').onclick=()=>{selected.clear();get('studentList').querySelectorAll('.school-select').forEach(c=>c.checked=false);updateSelected()};
get('studentList').addEventListener('click',e=>{const b=e.target.closest('[data-school-move]');if(b){selected.clear();selected.add(+b.dataset.schoolMove);get('studentList').querySelectorAll('.school-select').forEach(c=>c.checked=selected.has(+c.dataset.sid));updateSelected();box.querySelector('details').open=true;box.scrollIntoView({behavior:'smooth'})}});
async function bulk(kind){const ids=[...selected],cid=+get('schoolDestination').value;if(!ids.length){alert('Hãy chọn học sinh trước.');return}const isDelete=kind==='delete';if(!confirm(isDelete?'Xóa vĩnh viễn '+ids.length+' học sinh và lịch sử điểm danh liên quan?':'Chuyển '+ids.length+' học sinh sang lớp đã chọn?'))return;try{const d=await request(isDelete?'students/bulk-delete':'students/move',isDelete?{ids,confirm:'XOA_HOC_SINH'}:{ids,class_id:cid});selected.clear();updateSelected();status.textContent=isDelete?'Đã xóa '+d.deleted+' học sinh.':'Đã chuyển lớp '+d.moved+' học sinh.';await loadClasses()}catch(e){status.textContent=e.message}}
get('schoolMove').onclick=()=>bulk('move');get('schoolDelete').onclick=()=>bulk('delete');
// Dedicated management panel uses true class IDs from the API, never guesses IDs from label text.
const classArea=document.createElement('section');classArea.className='card';classArea.style.margin='14px 0';
classArea.innerHTML='<h3>✎ Đổi tên hoặc xóa lớp</h3><p class="muted">Chọn đúng lớp theo mã hệ thống. Lớp còn học sinh không thể xóa: hãy chuyển học sinh trước.</p><div id="schoolClassesManager"></div><p id="schoolClassesMsg" role="status"></p>';
get('classList').after(classArea);
const manager=classArea.querySelector('#schoolClassesManager'),feedback=classArea.querySelector('#schoolClassesMsg');
const escapeHTML=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
let classBusy=false;
async function updateClassManager(){
 if(classBusy)return;classBusy=true;
 try{
  const r=await fetch('/api/classes',{credentials:'same-origin'});
  const d=await r.json();if(!r.ok)throw Error(d.error||'Không đọc được lớp học');
  manager.innerHTML=d.items.map(c=>`<div class="item" data-class-id="${c.id}" style="display:flex;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:9px"><div style="flex:1;min-width:150px"><strong>${escapeHTML(c.name)}</strong><div class="meta">Khối ${escapeHTML(c.grade)} · ${c.student_count} học sinh · Mã lớp #${c.id}</div></div><button type="button" class="ghost small" data-school-rename="${c.id}">✎ Đổi tên</button><button type="button" class="ghost small" data-school-delete-class="${c.id}" ${c.student_count>0?'disabled title="Chuyển học sinh đi trước khi xóa"':''}>Xóa lớp trống</button></div>`).join('')||'<p>Chưa có lớp học.</p>';
 }catch(err){feedback.textContent=err.message}finally{classBusy=false}
}
manager.addEventListener('click',async e=>{
 const rename=e.target.closest('[data-school-rename]');const del=e.target.closest('[data-school-delete-class]');if(!rename&&!del)return;
 const id=Number((rename||del).dataset.schoolRename||(rename||del).dataset.schoolDeleteClass);
 if(rename){
  const current=manager.querySelector(`[data-class-id="${id}"] strong`)?.textContent||'';
  const name=prompt('Nhập tên lớp mới:',current);if(name===null)return;
  if(name.trim().length<2){feedback.textContent='Tên lớp cần ít nhất 2 ký tự.';return}
  const grade=prompt('Nhập khối lớp (ví dụ: 8, 9):','') ;if(grade===null)return;
  try{await request('classes/rename',{id,name:name.trim(),grade:grade.trim()});feedback.textContent='Đã đổi tên lớp. Danh sách học sinh được giữ nguyên.';await loadClasses();await updateClassManager()}catch(err){feedback.textContent=err.message}
 }else{
  if(!confirm('Xóa lớp trống này? Không thể hoàn tác.'))return;
  try{await request('classes/delete',{id});feedback.textContent='Đã xóa lớp trống.';await loadClasses();await updateClassManager()}catch(err){feedback.textContent=err.message}
 }
});
// The existing app refreshes classList after create/import/move; synchronize the new panel.
let classRefreshQueued=false;
const classListObs=new MutationObserver(()=>{
 if(classRefreshQueued)return;classRefreshQueued=true;
 queueMicrotask(async()=>{classRefreshQueued=false;await updateClassManager()});
});
classListObs.observe(get('classList'),{childList:true});
updateClassManager();
})();
