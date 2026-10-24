// Monthly attendance reporting; reads only server-persisted data from this teacher tenant.
let loadedAttendanceReport=null;
async function loadAttendanceReport(){
 if(!state.user||state.mustChange)return;
 const select=document.getElementById('reportClass'),month=document.getElementById('reportMonth');
 const feedback=document.getElementById('reportFeedback');
 if(!month.value){const now=new Date();month.value=now.getFullYear()+'-'+String(now.getMonth()+1).padStart(2,'0')}
 try{
  const classesResult=await api('classes');
  const previous=select.value;
  select.replaceChildren();
  for(const item of classesResult.items){
   const option=document.createElement('option');option.value=item.id;option.textContent=item.name+' ('+item.student_count+' HS)';select.append(option);
  }
  if([...select.options].some(o=>o.value===previous))select.value=previous;
  if(!select.value){feedback.textContent='Chưa có lớp học. Hãy thêm lớp và học sinh trước.';return}
  await refreshAttendanceReport();
 }catch(error){feedback.textContent='Không tải được danh sách lớp: '+error.message}
}
async function refreshAttendanceReport(){
 const cid=document.getElementById('reportClass').value,month=document.getElementById('reportMonth').value;
 const feedback=document.getElementById('reportFeedback');
 const dayTarget=document.getElementById('reportDaySummary'),studentTarget=document.getElementById('reportStudentSummary');
 if(!cid||!/^\\d{4}-(0[1-9]|1[0-2])$/.test(month)){feedback.textContent='Hãy chọn lớp và tháng hợp lệ.';return}
 feedback.textContent='Đang tải dữ liệu điểm danh đã lưu…';
 dayTarget.replaceChildren();studentTarget.replaceChildren();loadedAttendanceReport=null;
 try{
  const report=await api('attendance/report?class_id='+encodeURIComponent(cid)+'&month='+encodeURIComponent(month));
  if(document.getElementById('reportClass').value!==cid||document.getElementById('reportMonth').value!==month)return;
  loadedAttendanceReport={cid,month};
  feedback.textContent='Lớp '+report.class.name+' — '+report.saved_days+' ngày có dữ liệu điểm danh đã lưu. Ngày chưa lưu không được thống kê là có mặt.';
  const dayRows=report.days.map(r=>{
   const totals=r.saved?[r.present,r.absent,r.late,r.excused,r.unrecorded].map(String):['—','—','—','—','—'];
   return '<tr><td>'+esc(r.day)+'</td><td>'+ (r.saved?'<strong>Đã lưu</strong>':'Chưa điểm danh')+'</td>'+totals.map(x=>'<td>'+x+'</td>').join('')+'</tr>';
  }).join('');
  dayTarget.innerHTML='<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse"><thead><tr><th>Ngày</th><th>Tình trạng</th><th>Có mặt</th><th>Vắng</th><th>Muộn</th><th>Có phép</th><th>Chưa ghi nhận</th></tr></thead><tbody>'+dayRows+'</tbody></table></div>';
  if(!report.students.length){studentTarget.textContent='Lớp chưa có học sinh.';return}
  const rows=report.students.map(r=>'<tr><td>'+esc(r.code)+'</td><td>'+esc(r.name)+'</td><td>'+r.present+'</td><td>'+r.absent+'</td><td>'+r.late+'</td><td>'+r.excused+'</td><td>'+r.recorded+'</td></tr>').join('');
  studentTarget.innerHTML='<div style="overflow-x:auto"><table style="width:100%;border-collapse:collapse"><thead><tr><th>Mã HS</th><th>Họ và tên</th><th>Có mặt</th><th>Vắng</th><th>Muộn</th><th>Có phép</th><th>Ngày ghi nhận</th></tr></thead><tbody>'+rows+'</tbody></table></div>';
 }catch(error){feedback.textContent='Không tải được báo cáo: '+error.message}
}
document.getElementById('reportLoad').addEventListener('click',refreshAttendanceReport);
document.getElementById('reportClass').addEventListener('change',refreshAttendanceReport);
document.getElementById('reportMonth').addEventListener('change',refreshAttendanceReport);
document.getElementById('reportExport').addEventListener('click',async()=>{
 const cid=document.getElementById('reportClass').value,month=document.getElementById('reportMonth').value;
 const feedback=document.getElementById('reportFeedback'),button=document.getElementById('reportExport');
 if(!cid||!/^\\d{4}-(0[1-9]|1[0-2])$/.test(month)){feedback.textContent='Chọn lớp và tháng hợp lệ.';return}
 button.disabled=true;
 try{
  const response=await fetch('/api/attendance/report/export?class_id='+encodeURIComponent(cid)+'&month='+encodeURIComponent(month),{credentials:'same-origin'});
  if(!response.ok){let reason;try{reason=(await response.json()).error}catch{}throw Error(reason||'HTTP '+response.status)}
  const blob=await response.blob(),url=URL.createObjectURL(blob);
  const link=document.createElement('a');link.href=url;link.download='Chuyen_can_lop_'+cid+'_'+month+'.xlsx';
  document.body.appendChild(link);link.click();link.remove();
  setTimeout(()=>URL.revokeObjectURL(url),10000);
  feedback.textContent='Đã tạo báo cáo Excel với 3 trang: tổng hợp ngày, từng học sinh và chi tiết điểm danh.';
 }catch(error){feedback.textContent='Xuất Excel không thành công: '+error.message}
 finally{button.disabled=false}
});
