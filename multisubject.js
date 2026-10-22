(()=>{'use strict';
const subjects=["Toán", "Ngữ văn", "Tiếng Anh", "Vật lí", "Hóa học", "Sinh học", "Lịch sử", "Địa lí", "Giáo dục công dân", "Tin học", "Công nghệ", "Khoa học tự nhiên", "Âm nhạc", "Mĩ thuật", "Giáo dục thể chất", "Hoạt động trải nghiệm"];
const d=document.getElementById('subjectCatalog');if(d)d.innerHTML=subjects.map(x=>'<option value="'+x.replaceAll('"','&quot;')+'"></option>').join('');
const b=document.getElementById('seedAllSubjects');if(b)b.addEventListener('click',async()=>{
 if(!confirm('Tạo câu hỏi và đề mẫu cho các môn? Dữ liệu được ghi nhãn MINH HỌA.'))return;
 try{b.disabled=true;const res=await api('demo/multisubject',{});await refresh();if(typeof notice==='function')notice('Đã bổ sung '+res.added+' câu hỏi mẫu, '+res.subjects+' môn. Kiểm tra nội dung trước khi sử dụng.');}
 catch(e){if(typeof notice==='function')notice(e.message,true);else alert(e.message);}finally{b.disabled=false;}
});
})();
