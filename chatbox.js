(()=>{'use strict';
const style=document.createElement('style');style.textContent=`
#scChatToggle{position:fixed;right:22px;bottom:22px;z-index:9900;border:0;border-radius:100px;padding:15px 19px;background:linear-gradient(110deg,#5b40df,#168bdc);color:white;box-shadow:0 10px 35px #31228b55;cursor:pointer;font-size:15px;font-weight:750;transition:transform .2s}
#scChatToggle:hover{transform:translateY(-3px)}
#scChatPanel{position:fixed;right:20px;bottom:86px;width:min(390px,calc(100vw - 28px));height:min(550px,calc(100vh - 113px));background:#fff;color:#1c2741;border:1px solid #d9e4f6;border-radius:20px;z-index:9900;box-shadow:0 15px 50px #14254f44;display:flex;flex-direction:column;overflow:hidden}
#scChatPanel[hidden]{display:none}
.scChatHead{background:linear-gradient(110deg,#5937ca,#0a91d5);color:white;padding:15px;display:flex;align-items:center;justify-content:space-between}
.scChatHead strong{font-size:17px}.scChatHead small{display:block;color:#f4f6ff;margin-top:3px}
#scChatClose{color:white;background:transparent;border:0;font-size:24px;cursor:pointer;padding:0 4px}
#scChatHistory{flex:1;overflow:auto;padding:14px;display:flex;flex-direction:column;gap:10px;background:#f8faff}
.scMsg{max-width:92%;padding:11px 12px;border-radius:14px;white-space:pre-wrap;overflow-wrap:anywhere;font-size:14px;line-height:1.5}
.scMsg.ai{align-self:flex-start;background:white;border:1px solid #e1e8f2}.scMsg.user{align-self:flex-end;background:#e3eaff;color:#1d2860}
#scChatForm{padding:12px;border-top:1px solid #dce4ee;display:flex;gap:8px}
#scChatInput{flex:1;min-width:0;min-height:42px;border:1px solid #c5d1e7;border-radius:11px;padding:9px;font:inherit;background:white;color:#172554}
#scChatSend{border:0;border-radius:11px;background:#4a4dd6;color:white;padding:0 15px;cursor:pointer;font-weight:700}
#scChatSend:disabled{opacity:.5;cursor:wait}
#scChatNote{font-size:11px;color:#61708e;padding:0 12px 9px;text-align:center}
@media(max-width:480px){#scChatToggle{right:13px;bottom:12px}#scChatPanel{right:8px;bottom:70px;width:calc(100vw - 16px)}}
@media(prefers-reduced-motion:reduce){#scChatToggle{transition:none}}
`;document.head.append(style);
const toggle=document.createElement('button');toggle.id='scChatToggle';toggle.type='button';toggle.textContent='✦ Hỏi trợ lý AI';toggle.setAttribute('aria-expanded','false');toggle.setAttribute('aria-controls','scChatPanel');
const panel=document.createElement('section');panel.id='scChatPanel';panel.hidden=true;panel.setAttribute('aria-label','Chat với trợ lý SÁNG GIÁO AI');panel.innerHTML=`<div class="scChatHead"><div><strong>✦ Trợ lý SÁNG GIÁO AI</strong><small>Hỗ trợ giáo viên mọi môn học</small></div><button id="scChatClose" aria-label="Đóng hộp chat" type="button">×</button></div><div id="scChatHistory" role="log" aria-live="polite" aria-relevant="additions"></div><form id="scChatForm"><input id="scChatInput" placeholder="Nhập câu hỏi về bài giảng..." maxlength="1800" aria-label="Nội dung hỏi AI" required/><button id="scChatSend" type="submit">Gửi</button></form><div id="scChatNote">Cần đăng nhập giáo viên · Hãy kiểm tra nội dung AI trước khi dùng</div>`;
document.body.append(toggle,panel);
const history=[],log=panel.querySelector('#scChatHistory'),input=panel.querySelector('#scChatInput'),send=panel.querySelector('#scChatSend');
function add(text,who){const e=document.createElement('div');e.className='scMsg '+who;e.textContent=text;log.append(e);log.scrollTop=log.scrollHeight;return e}
add('Xin chào! Mình có thể giúp soạn câu hỏi đa môn, lên ý tưởng bài dạy 5512 và hướng dẫn sử dụng SÁNG GIÁO AI. Bạn muốn hỏi gì?', 'ai');
function show(value){panel.hidden=!value;toggle.setAttribute('aria-expanded',String(value));if(value)input.focus()}
toggle.addEventListener('click',()=>show(panel.hidden));panel.querySelector('#scChatClose').addEventListener('click',()=>show(false));document.addEventListener('keydown',e=>{if(e.key==='Escape'&&!panel.hidden)show(false)});
panel.querySelector('#scChatForm').addEventListener('submit',async e=>{e.preventDefault();const message=input.value.trim();if(!message)return;input.value='';add(message,'user');send.disabled=true;const pending=add('Đang hỏi Gemini…','ai');try{
 const me=await fetch('/api/me',{credentials:'same-origin'}).then(r=>r.json());if(!me.csrf)throw Error('Bạn cần đăng nhập cổng giáo viên trước khi dùng trợ lý AI.');
 const response=await fetch('/api/ai/chat',{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json','X-CSRF-Token':me.csrf},body:JSON.stringify({message,history:history.slice(-8)})});
 const raw=await response.text();let data;try{data=JSON.parse(raw)}catch{throw Error('Máy chủ chưa trả JSON hợp lệ. Hãy thử lại.')}
 if(!response.ok)throw Error(data.error||'Yêu cầu thất bại (HTTP '+response.status+').');if(!data.reply)throw Error('Trợ lý chưa trả nội dung.');pending.textContent=data.reply;history.push({role:'user',text:message},{role:'assistant',text:data.reply});if(history.length>10)history.splice(0,history.length-10);
 }catch(err){pending.textContent='⚠ '+err.message;}finally{send.disabled=false;log.scrollTop=log.scrollHeight;input.focus()}});
})();
