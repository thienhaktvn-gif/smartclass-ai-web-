// Teacher-review-first multiple-choice DOCX variant generator.
(()=>{'use strict';
let reviewed=[];
const $id=id=>document.getElementById(id);
const feedback=$id('wordExamFeedback'),preview=$id('wordExamPreview'),button=$id('wordExamExport');
function message(text){feedback.textContent=text}
function field(label,value,max,callback){
 const wrapper=document.createElement('label');wrapper.textContent=label;
 const input=document.createElement('textarea');input.value=value;input.rows=2;input.maxLength=max;
 input.style.width='100%';input.addEventListener('input',e=>{callback(e.target.value);});
 wrapper.append(input);return wrapper;
}
function render(){
 preview.replaceChildren();
 reviewed.forEach((q,index)=>{
  const item=document.createElement('div');item.className='item';
  const title=document.createElement('strong');title.textContent='Câu '+(index+1);
  item.append(title,field('Nội dung câu hỏi',q.content,4000,v=>q.content=v));
  for(const letter of 'ABCD'){item.append(field('Phương án '+letter,q.options[letter],2000,v=>q.options[letter]=v));}
  const choice=document.createElement('label');choice.textContent='Đáp án đúng: ';
  const select=document.createElement('select');
  for(const letter of 'ABCD'){
   const option=document.createElement('option');option.value=letter;option.textContent=letter;select.append(option);
  }
  select.value=q.answer;select.addEventListener('change',()=>q.answer=select.value);
  choice.append(select);item.append(choice);preview.append(item);
 });
}
$id('wordExamRead').addEventListener('click',async()=>{
 const file=$id('wordExamFile').files[0];
 reviewed=[];button.disabled=true;preview.replaceChildren();
 if(!file){message('Hãy chọn file Word .docx trước.');return}
 if(!file.name.toLowerCase().endsWith('.docx')){message('Chỉ hỗ trợ tệp .docx. Vui lòng lưu Word dưới định dạng .docx.');return}
 if(file.size>1700000){message('Để tải an toàn, file Word cần nhỏ hơn 1,7 MB.');return}
 const readButton=$id('wordExamRead');readButton.disabled=true;message('Đang đọc câu hỏi và bảng đáp án…');
 try{
  const raw=await file.arrayBuffer();
  const bytes=new Uint8Array(raw);let binary='';
  for(let i=0;i<bytes.length;i+=8192){binary+=String.fromCharCode(...bytes.subarray(i,i+8192))}
  const result=await api('exams/word/preview',{filename:file.name,file:btoa(binary)});
  reviewed=result.items;render();button.disabled=false;
  message('Đã nhận dạng '+result.count+' câu. Hãy đọc và sửa nội dung/đáp án nếu cần. Chỉ nhấn Xuất khi chắc chắn mọi đáp án đúng.');
 }catch(error){message('Không nhập được đề Word: '+error.message)}
 finally{readButton.disabled=false}
});
$id('wordExamExport').addEventListener('click',async()=>{
 if(!reviewed.length){message('Cần nhập và kiểm tra đề trước khi trộn.');return}
 const count=Number($id('wordExamCount').value),title=$id('wordExamTitle').value.trim();
 if(!title||title.length<3){message('Nhập tên đề dài ít nhất 3 ký tự.');return}
 if(!window.confirm('Bạn đã kiểm tra đủ '+reviewed.length+' câu và đáp án đúng? Xuất '+count+' mã đề Word cùng bảng đáp án?'))return;
 button.disabled=true;message('Đang tạo các mã đề và cập nhật đáp án…');
 try{
  const response=await fetch('/api/exams/word/export',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':state.csrf},body:JSON.stringify({title,variants:count,items:reviewed})});
  if(!response.ok){
   let err;try{err=(await response.json()).error}catch{}
   throw Error(err||'Máy chủ báo HTTP '+response.status);
  }
  const blob=await response.blob(),url=URL.createObjectURL(blob);
  const link=document.createElement('a');link.href=url;link.download='De_tron_'+count+'_ma_va_dap_an.zip';
  document.body.append(link);link.click();link.remove();
  setTimeout(()=>URL.revokeObjectURL(url),12000);
  message('Đã xuất '+count+' mã đề Word (001–'+String(count).padStart(3,'0')+') và Bang_dap_an.docx. Tải ZIP, giải nén, kiểm tra bản in trước khi dùng.');
 }catch(error){message('Không thể xuất đề: '+error.message)}
 finally{button.disabled=false}
});
})();