// SÁNG GIÁO AI: progressive navigation enhancements without replacing app.js.
(()=>{'use strict';
 const nav=document.getElementById('nav');
 if(nav){nav.setAttribute('aria-label','Điều hướng Sáng Giáo AI');const buttons=[...nav.querySelectorAll('button[data-tab]')];const update=()=>buttons.forEach(b=>{if(b.classList.contains('active'))b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');b.title=b.textContent.trim()});nav.addEventListener('click',()=>requestAnimationFrame(update));document.addEventListener('click',e=>{if(e.target.closest('[data-jump]'))requestAnimationFrame(update)});update()}
 // The four dashboard statistics were created as plain div.stat in app.js.
 // Use event delegation because the dashboard replaces its stats on every refresh.
 const destination=['bank','exams','grade','classes'];
 const titles=['Mở ngân hàng câu hỏi','Mở danh sách đề kiểm tra','Mở chấm bài','Mở quản lý lớp và học sinh'];
 const style=document.createElement('style');style.textContent=`#stats .stat{cursor:pointer;transition:transform .16s,box-shadow .16s;position:relative}#stats .stat:hover{transform:translateY(-3px);box-shadow:0 10px 28px #283b6520}#stats .stat:focus-visible{outline:3px solid #6154d9;outline-offset:3px}#stats .stat::after{content:'Mở →';display:block;margin-top:8px;font-size:12px;font-weight:700;color:#5551bd}@media(prefers-reduced-motion:reduce){#stats .stat{transition:none}}`;document.head.append(style);
 const stats=document.getElementById('stats');
 if(!stats)return;
 function decorate(){[...stats.querySelectorAll(':scope > .stat')].forEach((card,index)=>{if(index>=destination.length)return;card.setAttribute('role','button');card.setAttribute('tabindex','0');card.setAttribute('aria-label',titles[index]);card.title=titles[index]})}
 function navigate(target){if(typeof go==='function'){go(target);return}const button=document.querySelector(`#nav button[data-tab="${target}"]`);if(button)button.click();}
 function onActivate(e){const card=e.target.closest('.stat');if(!card||!stats.contains(card))return;const index=[...stats.children].indexOf(card);if(index<0||index>=destination.length)return;if(e.type==='keydown'&&e.key!=='Enter'&&e.key!==' ')return;if(e.type==='keydown')e.preventDefault();navigate(destination[index])}
 stats.addEventListener('click',onActivate);stats.addEventListener('keydown',onActivate);
 const observer=new MutationObserver(decorate);observer.observe(stats,{childList:true});decorate();
})();
