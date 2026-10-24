/* Teacher-gradebook and student exam code portal; server owns grading and authorisation. */
(()=>{
'use strict';
const el=id=>document.getElementById(id);
const escText=x=>String(x??'');
let activeRun=null;
async function jsonPost(path,body){
 const response=await fetch('/api/'+path,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
 let data;try{data=await response.json()}catch{throw Error('Máy chủ không trả JSON hợp lệ.')}
 if(!response.ok)throw Error(data.error||('HTTP '+response.status));
 return data;
}
window.loadOnlineGradeDashboard=async function(){
 if(!state.user||state.mustChange)return;
 const chosen=el('onlineGradeExam').value;
 el('onlineGradeExam').replaceChildren();
 for(const exam of state.exams){
  const option=document.createElement('option');option.value=exam.id;
  option.textContent=exam.title+' (#'+exam.id+')';el('onlineGradeExam').append(option);
 }
 if(chosen&&[...el('onlineGradeExam').options].some(o=>o.value===chosen))el('onlineGradeExam').value=chosen;
 await window.loadOnlineGradeResults();
};
window.loadOnlineGradeResults=async function(){
 const id=el('onlineGradeExam').value,feedback=el('onlineGradeFeedback'),target=el('onlineGradeTable');
 target.replaceChildren();
 if(!id){feedback.textContent='Chưa có đề kiểm tra được tạo.';return}
 feedback.textContent='Đang đọc bảng điểm đã lưu…';
 try{
  const data=await api('online/results?exam_id='+encodeURIComponent(id));
  const rows=data.items;
  feedback.textContent=rows.length+' bài thi trực tuyến đã được chấm và lưu cho đề '+data.exam.title+'.';
  if(!rows.length){target.textContent='Chưa có học sinh nộp bài qua mã dự thi riêng.';return}
  const table=document.createElement('table');table.style.width='100%';
  const header=document.createElement('thead');const hr=document.createElement('tr');
  ['STT','Mã học sinh','Họ tên','Điểm /10','Đúng/Tổng','Nhận xét','Thời gian'].forEach(h=>{const th=document.createElement('th');th.textContent=h;hr.append(th)});header.append(hr);table.append(header);
  const tbody=document.createElement('tbody');
  rows.forEach((r,i)=>{const tr=document.createElement('tr');[i+1,r.student_code,r.student_name,r.score,r.correct+'/'+r.total,r.feedback,r.created].forEach(v=>{const td=document.createElement('td');td.textContent=escText(v);tr.append(td)});tbody.append(tr)});
  table.append(tbody);target.append(table);
 }catch(error){feedback.textContent=error.message}
};
el('onlineGradeLoad').addEventListener('click',window.loadOnlineGradeResults);
el('onlineGradeExam').addEventListener('change',window.loadOnlineGradeResults);
async function downloadGrade(kind){
 const id=el('onlineGradeExam').value,feedback=el('onlineGradeFeedback');
 if(!id){feedback.textContent='Hãy chọn đề trước khi xuất.';return}
 const button=el(kind==='xlsx'?'onlineGradeExcel':'onlineGradeWord');button.disabled=true;
 try{
  const response=await fetch('/api/online/results/export?exam_id='+encodeURIComponent(id)+'&format='+kind,{credentials:'same-origin'});
  if(!response.ok){let data;try{data=await response.json()}catch{}throw Error(data?.error||'Xuất bảng điểm thất bại.')}
  const url=URL.createObjectURL(await response.blob());
  const link=document.createElement('a');link.href=url;link.download='Bang_diem_de_'+id+'.'+kind;
  document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(url),12000);
  feedback.textContent='Đã xuất bảng điểm '+(kind==='xlsx'?'Excel':'Word')+'.';
 }catch(error){feedback.textContent=error.message}finally{button.disabled=false}
}
el('onlineGradeExcel').addEventListener('click',()=>downloadGrade('xlsx'));
el('onlineGradeWord').addEventListener('click',()=>downloadGrade('docx'));

document.getElementById('examList').addEventListener('click',async event=>{
 const button=event.target.closest('button[data-share-online]');
 if(!button)return;
 if(!confirm('Tạo mã dự thi mới cho đề này? Mã cũ của đề sẽ ngừng hoạt động.'))return;
 button.disabled=true;
 try{
  const result=await api('online/share',{exam_id:+button.dataset.shareOnline});
  const output=el('onlineShareResult');
  output.replaceChildren();
  const text=document.createElement('p');text.textContent='MÃ DỰ THI (chỉ hiện một lần): '+result.exam_code;
  const hint=document.createElement('p');hint.textContent='Học sinh vào '+result.url+' và nhập mã này, họ tên cùng mã học sinh. Hãy lưu mã ở nơi an toàn trước khi đóng.';
  const copy=document.createElement('button');copy.className='ghost small';copy.type='button';copy.textContent='Sao chép mã';
  copy.onclick=()=>navigator.clipboard.writeText(result.exam_code).then(()=>copy.textContent='Đã sao chép').catch(()=>copy.textContent='Hãy sao chép thủ công');
  const close=document.createElement('button');close.type='button';close.className='ghost small';close.textContent='Ẩn mã';close.onclick=()=>output.replaceChildren();
  output.append(text,hint,copy,document.createTextNode(' '),close);
 }catch(error){alert('Cấp mã dự thi thất bại: '+error.message)}
 finally{button.disabled=false}
});

el('onlineStudentStart').addEventListener('submit',async event=>{
 event.preventDefault();
 const form=event.target;const fields=Object.fromEntries(new FormData(form));const feedback=el('onlineStudentFeedback');
 feedback.textContent='Đang xác minh mã dự thi và chuẩn bị đề…';
 const button=form.querySelector('button');button.disabled=true;
 try{
  const data=await jsonPost('online/start',fields);
  activeRun={token:data.attempt_token,expires:data.expires,items:data.items};
  const taking=el('onlineStudentTaking');taking.replaceChildren();
  const heading=document.createElement('h3');heading.textContent=data.exam.title+' · '+data.items.length+' câu · '+data.exam.duration+' phút';
  const deadline=document.createElement('p');deadline.textContent='Hạn nộp: '+new Date(data.expires*1000).toLocaleString('vi-VN');
  const examForm=document.createElement('form');examForm.id='onlineAnswersForm';
  for(let index=0;index<data.items.length;index++){
   const q=data.items[index],wrap=document.createElement('fieldset');
   const legend=document.createElement('legend');legend.textContent='Câu '+(index+1)+'. '+q.content;wrap.append(legend);
   for(const answer of q.options){
    const label=document.createElement('label');label.style.display='block';
    const input=document.createElement('input');input.type='radio';input.name='q_'+q.id;input.value=answer.key;
    label.append(input,document.createTextNode(' '+answer.key+'. '+answer.text));wrap.append(label);
   }
   examForm.append(wrap);
  }
  const submit=document.createElement('button');submit.type='submit';submit.className='primary';submit.textContent='Nộp bài và chấm tự động';
  examForm.append(submit);
  examForm.addEventListener('submit',submitExam);
  taking.append(heading,deadline,examForm);
  feedback.textContent='Đề đã mở. Chỉ nộp một lần; hãy kiểm tra câu trả lời trước khi nộp.';
 }catch(error){feedback.textContent=error.message}
 finally{button.disabled=false}
});
async function submitExam(event){
 event.preventDefault();if(!activeRun)return;
 if(!confirm('Xác nhận nộp bài? Sau khi nộp không thể sửa câu trả lời.'))return;
 const form=event.target,button=form.querySelector('button[type=submit]');button.disabled=true;
 const answers={};for(const [name,value] of new FormData(form))answers[name.slice(2)]=value;
 const feedback=el('onlineStudentFeedback');
 try{
  const result=await jsonPost('online/submit',{attempt_token:activeRun.token,answers});
  activeRun=null;form.remove();
  feedback.textContent='Đã nộp và lưu bài thành công. Điểm: '+result.score+'/10, đúng '+result.correct+'/'+result.total+'. '+result.feedback;
 }catch(error){feedback.textContent='Chưa nộp được: '+error.message;button.disabled=false}
}
})();