(()=>{'use strict';
const form=document.getElementById('registerForm');
if(!form)return;
const feedback=document.getElementById('registerResult');
const username=form.elements.username,password=form.elements.password,confirmField=form.elements.confirm;
const usernameRule=/^[a-z][a-z0-9_.-]{4,31}$/;
const detail='Tên đăng nhập phải có 5–32 ký tự không dấu, bắt đầu bằng chữ cái a–z; chỉ dùng chữ thường, số, dấu chấm, gạch dưới hoặc gạch ngang.';
function show(message){feedback.textContent=message;feedback.setAttribute('role','status')}
username.addEventListener('blur',()=>{username.value=username.value.trim().toLowerCase()});
form.addEventListener('submit',async event=>{
 event.preventDefault();
 const name=username.value.trim().toLowerCase();
 username.value=name;
 const pw=password.value;
 if(!usernameRule.test(name)){show(detail);username.focus();return}
 if(pw.length<12||pw.length>128||!/[A-Z]/.test(pw)||!/[a-z]/.test(pw)||!/[0-9]/.test(pw)){
  show('Mật khẩu cần 12–128 ký tự, gồm ít nhất một chữ hoa, một chữ thường và một chữ số.');password.focus();return;
 }
 if(pw!==confirmField.value){show('Hai mật khẩu không giống nhau.');confirmField.focus();return}
 const submit=form.querySelector('button[type="submit"]');
 submit.disabled=true;
 show('Đang kiểm tra và tạo tài khoản…');
 try{
  const response=await fetch('/api/register',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:name,password:pw})});
  const text=await response.text();
  let data;try{data=JSON.parse(text)}catch{show('Máy chủ không trả dữ liệu hợp lệ (HTTP '+response.status+'). Vui lòng báo quản trị viên.');return}
  if(!response.ok){show(data.error||'Đăng ký chưa thành công (HTTP '+response.status+').');return}
  const login=await fetch('/api/login',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:name,password:pw,portal:'teacher'})});
  const loginData=await login.json();
  if(!login.ok){show('Tài khoản đã tạo; vui lòng đăng nhập tại cổng giáo viên. '+(loginData.error||''));return}
  show('Đã tạo tài khoản và đăng nhập thành công.');
  form.reset();
  window.location.reload();
 }catch(error){show('Không thể kết nối máy chủ. Kiểm tra mạng rồi thử lại.')}
 finally{submit.disabled=false}
});
})();