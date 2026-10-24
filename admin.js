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
   item.append(name,role);list.append(item);
  }
  target.append(list);
 }catch(e){target.textContent='Không thể tải tài khoản: '+e.message}
}
