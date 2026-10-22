(()=>{'use strict';
const layer=document.getElementById('portalChoice');
const show=()=>{layer.classList.remove('is-hidden');document.body.style.overflow='hidden'};
const hide=()=>{layer.classList.add('is-hidden');document.body.style.overflow=''};
function enter(role){hide();if(role==='student')go('student');else if(state.user)go('home');else go('login');}
layer.addEventListener('click',e=>{const b=e.target.closest('[data-portal]');if(b)enter(b.dataset.portal)});
document.getElementById('portalSwitch').addEventListener('click',show);
const route=location.pathname;
if(route==='/student'||route==='/games')hide();else if(route==='/auth/login'||route==='/teacher'||route==='/planner'){hide();}else show();
// A genuine .docx is produced by the authenticated server, not by renaming HTML.
const btn=document.getElementById('planWord');
if(btn)btn.addEventListener('click',async()=>{
 if(!state.user){notice('Đăng nhập giáo viên để xuất giáo án Word.',true);go('login');return}
 const form=document.getElementById('planForm'),payload=Object.fromEntries(new FormData(form));
 btn.disabled=true;btn.textContent='Đang tạo Word...';
 try{const response=await fetch('/api/planner/docx',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':state.csrf},body:JSON.stringify(payload)});
 if(!response.ok){let error={};try{error=await response.json()}catch{}throw Error(error.error||'Không thể xuất Word')}
 const blob=await response.blob(),url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download='Ke_hoach_bai_day_5512.docx';document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),3000);notice('Đã xuất giáo án Word .docx.');
 }catch(err){notice(err.message,true)}finally{btn.disabled=false;btn.textContent='📄 Xuất Word (.docx)'}
});
})();
