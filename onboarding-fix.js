(()=>{'use strict';
const login=document.getElementById('showLogin'),register=document.getElementById('showRegister');
const panel=document.getElementById('registerPanel'),loginForm=document.getElementById('loginForm');
const status=document.getElementById('registrationStatus');
function choose(which){const reg=which==='register';panel.classList.toggle('hidden',!reg);loginForm.classList.toggle('hidden',reg);register.classList.toggle('active',reg);login.classList.toggle('active',!reg);if(typeof go==='function')go('login');}
login?.addEventListener('click',()=>choose('login'));register?.addEventListener('click',()=>choose('register'));
document.getElementById('portalRegister')?.addEventListener('click',()=>{document.getElementById('portalChoice')?.classList.add('is-hidden');document.body.style.overflow='';choose('register')});
// Show honest server capability, never pretend registration is available.
fetch('/api/registration-status').then(r=>r.json()).then(data=>{
 status.textContent=data.enabled?'Đăng ký đang mở. Mỗi tài khoản giáo viên có kho dữ liệu riêng.':'Đăng ký hiện tạm khóa để bảo vệ dữ liệu tài khoản trên máy chủ lưu trữ tạm. Quản trị cần cấu hình lưu trữ bền vững trước khi mở.';
}).catch(()=>{status.textContent='Không đọc được trạng thái đăng ký từ máy chủ.'});
})();