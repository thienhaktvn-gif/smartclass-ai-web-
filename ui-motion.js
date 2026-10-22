// Enhancements are progressive: the existing app.js owns all API and navigation behavior.
(()=>{
  const nav=document.getElementById('nav');
  if(!nav)return;
  nav.setAttribute('aria-label','Điều hướng SmartClass AI');
  const buttons=[...nav.querySelectorAll('[data-tab]')];
  function update(){buttons.forEach(b=>{const active=b.classList.contains('active'); if(active)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');b.title=b.textContent.trim();});}
  nav.addEventListener('click',()=>requestAnimationFrame(update));
  document.addEventListener('click',e=>{if(e.target.closest('[data-jump]'))requestAnimationFrame(update)});
  update();
})();
