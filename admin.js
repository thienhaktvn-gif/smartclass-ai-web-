// Admin overview: authorization always enforced by the server, never by hiding the menu.
async function loadAdminDashboard(){
 const target=document.getElementById('adminTeacherList'),stats=document.getElementById('adminStats');
 if(!target||!stats||state.role!=='admin')return;
 target.textContent='Đang tải danh sách tài khoản…';
 try{
  const data=await api('admin/teachers');
  const teachers=data.items.filter(row=>row.role==='teacher');
  stats.innerHTML='<div class="stat"><b>'+teachers.length+'</b><small>Tài khoản giáo viên</small></div>'+
    '<div class="stat"><b>1</b><small>Quản trị viên hệ thống</small></div>';
  target.replaceChildren();
  const list=document.createElement('div');
  list.className='stack';
  for(const user of data.items){
   const item=document.createElement('div');
   item.className='item';
   const name=document.createElement('strong');
   name.textContent=user.username;
   const role=document.createElement('div');
   role.className='meta';
   role.textContent=(user.role==='admin'?'Quản trị viên':'Giáo viên')+' · Ngày tạo: '+(user.created||'Chưa có');
   item.append(name,role);
   if(user.role==='teacher'){
    const button=document.createElement('button');
    button.type='button';button.className='ghost small';button.textContent='Cấp lại mật khẩu tạm';
    button.addEventListener('click',()=>resetTeacherPassword(user.username,button));
    item.append(button);
   }
   list.append(item);
  }
  target.append(list);
 }catch(e){target.textContent='Không thể tải tài khoản: '+e.message}
}

async function resetTeacherPassword(username,button){
 const typed=window.prompt('Xác minh yêu cầu với giáo viên trước khi tiếp tục.\nNhập chính xác tên tài khoản cần cấp lại mật khẩu: '+username);
 if(typed===null)return;
 if(typed.trim().toLowerCase()!==username){window.alert('Tên xác nhận không khớp. Đã hủy.');return}
 button.disabled=true;
 try{
  const result=await api('admin/password-reset',{username,confirm:username});
  const box=document.getElementById('adminResetResult');
  if(box){
   box.replaceChildren();
   const p=document.createElement('p');p.textContent='Đã cấp lại mật khẩu cho '+username+'. Mật khẩu tạm chỉ hiển thị một lần. Giao trực tiếp cho đúng giáo viên; tài khoản phải đổi mật khẩu sau khi đăng nhập.';
   const code=document.createElement('code');code.textContent=result.temporaryPassword;
   const copy=document.createElement('button');copy.type='button';copy.className='ghost small';copy.textContent='Sao chép mật khẩu tạm';
   copy.onclick=()=>navigator.clipboard.writeText(result.temporaryPassword).then(()=>{copy.textContent='Đã sao chép';}).catch(()=>{copy.textContent='Hãy sao chép thủ công';});
   const close=document.createElement('button');close.type='button';close.className='ghost small';close.textContent='Đóng và xóa mật khẩu hiển thị';close.onclick=()=>box.replaceChildren();
   box.append(p,code,document.createTextNode(' '),copy,document.createTextNode(' '),close);
   box.scrollIntoView({block:'nearest'});
  }
 }catch(error){window.alert('Không thể cấp lại mật khẩu: '+error.message);}
 finally{button.disabled=false;}
}
