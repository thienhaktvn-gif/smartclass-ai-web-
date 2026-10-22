(()=>{'use strict';
const form=document.getElementById('planForm'),button=document.getElementById('scPlannerAIButton'),undo=document.getElementById('scPlannerUndo'),status=document.getElementById('scPlannerAIStatus');
if(!form||!button||!undo||!status)return;
const fields=['knowledge','skills','qualities','digital_evidence','resources','warmup','explore','practice','apply'];let before=null;
const snapshot=()=>Object.fromEntries(fields.map(k=>[k,form.elements.namedItem(k)?.value||'']));
const setStatus=(message,isError=false)=>{status.textContent=message;status.style.color=isError?'#aa253a':'#345375';};
button.addEventListener('click',async()=>{
 const data=Object.fromEntries(new FormData(form));if(!String(data.subject||'').trim()||!String(data.grade||'').trim()||String(data.title||'').trim().length<4){setStatus('Hãy điền môn, lớp và tên bài dạy trước.',true);return;}
 button.disabled=true;setStatus('Đang nhờ Gemini soạn bản nháp...');
 try{
  const meRes=await fetch('/api/me',{credentials:'same-origin'});const me=await meRes.json();if(!me.csrf)throw Error('Hãy đăng nhập giáo viên trước khi dùng AI.');
  const resp=await fetch('/api/planner/ai-draft',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':me.csrf},body:JSON.stringify(data)});
  const raw=await resp.text();let result;try{result=JSON.parse(raw)}catch{throw Error('Máy chủ trả phản hồi không hợp lệ (HTTP '+resp.status+').');}
  if(!resp.ok)throw Error(result.error||'Lỗi HTTP '+resp.status);
  if(!result.draft||fields.some(k=>typeof result.draft[k]!=='string'))throw Error('Bản nháp AI thiếu trường dữ liệu.');
  before=snapshot();fields.forEach(k=>{const el=form.elements.namedItem(k);if(el){el.value=result.draft[k];el.dispatchEvent(new Event('input',{bubbles:true}));}});undo.disabled=false;
  setStatus('Đã điền 9 mục. Hãy rà soát yêu cầu cần đạt, từng hoạt động và năng lực số; sau đó bấm Xuất Word.');
  form.elements.namedItem('knowledge')?.focus();
 }catch(err){setStatus(err.message||'Không thể kết nối Gemini. Bạn vẫn có thể soạn thủ công.',true)}finally{button.disabled=false;}
});
undo.addEventListener('click',()=>{if(!before)return;fields.forEach(k=>{const el=form.elements.namedItem(k);if(el)el.value=before[k]||'';});undo.disabled=true;before=null;setStatus('Đã hoàn tác nội dung AI.');});
})();
