(() => {
  'use strict';
  const root = document.getElementById('bank');
  if (!root) return;
  const block = document.createElement('section');
  block.className = 'card';
  block.style.margin = '1rem 0';
  const heading = document.createElement('h3');
  heading.textContent = 'Duyệt ngân hàng câu hỏi có phân trang';
  const filter = document.createElement('input');
  filter.placeholder = 'Tìm kiếm nội dung';
  filter.setAttribute('aria-label','Tìm câu hỏi');
  const go = document.createElement('button');
  go.textContent = 'Tìm';
  const prev = document.createElement('button');
  prev.textContent = 'Trang trước';
  const next = document.createElement('button');
  next.textContent = 'Trang sau';
  const status = document.createElement('p');
  status.setAttribute('role','status');
  const results = document.createElement('div');
  [heading,filter,go,status,results,prev,next].forEach(x => block.appendChild(x));
  root.prepend(block);
  let page = 1, totalPages = 0, busy = false;
  let authenticated = false;
  async function checkSession() {
    try {
      const response = await fetch('/api/me', {credentials:'same-origin',cache:'no-store'});
      if (!response.ok) return false;
      const data = await response.json();
      return Boolean(data.user);
    } catch (_) { return false; }
  }
  async function refreshIfVisible() {
    if (!root.classList.contains('active')) return;
    authenticated = await checkSession();
    if (!authenticated) {
      results.replaceChildren();
      status.textContent = 'Đăng nhập để xem ngân hàng câu hỏi.';
      prev.disabled = true;
      next.disabled = true;
      return;
    }
    await load();
  }
  async function load() {
    if (busy) return;
    if (!authenticated) { await refreshIfVisible(); return; }
    busy = true;
    status.textContent = 'Đang tải...';
    try {
      const params = new URLSearchParams({page:String(page), size:'30', q:filter.value.trim()});
      const response = await fetch('/api/questions/page?' + params, {credentials:'same-origin',cache:'no-store'});
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || 'Không thể truy cập');
      totalPages = data.pages;
      status.textContent = 'Tổng ' + data.total + ' câu hỏi, trang ' + page + '/' + Math.max(1,totalPages);
      results.replaceChildren();
      for (const item of data.items) {
        const div = document.createElement('div');
        div.className = 'item';
        div.textContent = item.subject + ' | Lớp ' + item.grade + ': ' + item.content;
        results.appendChild(div);
      }
      prev.disabled = page <= 1;
      next.disabled = page >= totalPages;
    } catch (error) {
      status.textContent = 'Lỗi: ' + error.message;
      if (String(error.message).includes('đăng nhập')) authenticated = false;
    }
    finally { busy = false; }
  }
  go.onclick = () => { page=1; load(); };
  prev.onclick = () => { if (page > 1) { page--; load(); } };
  next.onclick = () => { if (page < totalPages) { page++; load(); } };
  // The bank exists in DOM before a teacher signs in. Reload on opening the tab,
  // not during anonymous page startup; otherwise the first 401 remains stuck.
  const observer = new MutationObserver(() => {
    if (root.classList.contains('active')) refreshIfVisible();
  });
  observer.observe(root,{attributes:true,attributeFilter:['class']});
  if (root.classList.contains('active')) refreshIfVisible();
})();
