// Progressive enhancements and safe display-brand correction.
(()=>{
  'use strict';
  const nav=document.getElementById('nav');
  if(nav){
    nav.setAttribute('aria-label','Điều hướng SÁNG GIÁO AI');
    const buttons=[...nav.querySelectorAll('[data-tab]')];
    function update(){buttons.forEach(b=>{const active=b.classList.contains('active');if(active)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');b.title=b.textContent.trim();});}
    nav.addEventListener('click',()=>requestAnimationFrame(update));
    document.addEventListener('click',e=>{if(e.target.closest('[data-jump]'))requestAnimationFrame(update)});
    update();
  }
  const oldName=/SmartClass AI/gi;
  const newName='SÁNG GIÁO AI';
  function applyBrand(){
    document.title=document.title.replace(oldName,newName);
    // Only text nodes, never script code, API paths, or database identifiers.
    const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT,{
      acceptNode(node){
        if(!node.nodeValue || !/SmartClass AI/i.test(node.nodeValue))return NodeFilter.FILTER_REJECT;
        if(node.parentElement?.closest('script,style,textarea,code,pre,[contenteditable="true"]'))return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    const nodes=[];while(walker.nextNode())nodes.push(walker.currentNode);
    nodes.forEach(node=>{node.nodeValue=node.nodeValue.replace(oldName,newName)});
    const brand=document.querySelector('.sidebar .brand strong');
    if(brand)brand.textContent=newName;
    const eyebrow=document.querySelector('.eyebrow');
    document.querySelectorAll('.sidebar .brand .scCopyright').forEach(el=>{el.style.fontSize='14px';el.style.fontWeight='900';el.style.lineHeight='1.4';});
  }
  applyBrand();
  // Update text rendered after login without interfering with other JS behavior.
  let pending=false;
  const observer=new MutationObserver(()=>{
    if(pending)return;
    pending=true;
    queueMicrotask(()=>{observer.disconnect();applyBrand();observer.observe(document.body,{subtree:true,childList:true,characterData:true});pending=false;});
  });
  observer.observe(document.body,{subtree:true,childList:true,characterData:true});
})();
