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
  filter.setAttribute('aria-label', 'Tìm câu hỏi');
  const go = document.createElement('button');
  go.textContent = 'Tìm';
  const prev = document.createElement('button');
  prev.textContent = 'Trang trước';
  const next = document.createElement('button');
  next.textContent = 'Trang sau';
  const status = document.createElement('p');
  status.setAttribute('role', 'status');
  const results = document.createElement('div');
  [heading,filter,go,status,results,prev,next].forEach(x => block.appendChild(x));
  root.prepend(block);

  let page = 1, totalPages = 0, requestId = 0;
  let activeController = null;
  const visible = () => root.classList.contains('active');
  const setNavigation = () => {
    prev.disabled = page <= 1;
    next.disabled = page >= totalPages || totalPages === 0;
  };
  const resetBank = (message) => {
    results.replaceChildren();
    totalPages = 0;
    page = 1;
    status.textContent = message;
    setNavigation();
  };
  async function load() {
    if (!visible()) return;
    const id = ++requestId;
    if (activeController) activeController.abort();
    const controller = new AbortController();
    activeController = controller;
    status.textContent = 'Đang tải...';
    prev.disabled = next.disabled = true;
    try {
      // Auth and question data both use the same server-side cookie session.
      const sessionResponse = await fetch('/api/me', {
        credentials:'same-origin', cache:'no-store', signal:controller.signal
      });
      if (!sessionResponse.ok) throw new Error('Không thể kiểm tra phiên đăng nhập.');
      const session = await sessionResponse.json();
      if (!session.user) {
        resetBank('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.');
        return;
      }
      const params = new URLSearchParams({page:String(page), size:'30', q:filter.value.trim()});
      const response = await fetch('/api/questions/page?' + params, {
        credentials:'same-origin', cache:'no-store', signal:controller.signal
      });
      const data = await response.json();
      if (!response.ok) {
        if (response.status === 401) {
          resetBank('Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.');
          return;
        }
        throw new Error(data.error || ('Không thể tải câu hỏi (HTTP ' + response.status + ')'));
      }
      if (id !== requestId || !visible()) return;
      totalPages = Number(data.pages) || 0;
      page = Number(data.page) || page;
      status.textContent = 'Tổng ' + data.total + ' câu hỏi, trang ' + page + '/' + Math.max(1,totalPages);
      results.replaceChildren();
      for (const item of data.items || []) {
        const div = document.createElement('div');
        div.className = 'item';
        div.textContent = item.subject + ' | Lớp ' + item.grade + ': ' + item.content;
        results.appendChild(div);
      }
      setNavigation();
    } catch (error) {
      if (error.name === 'AbortError' || id !== requestId) return;
      status.textContent = 'Lỗi: ' + error.message;
      setNavigation();
    } finally {
      if (id === requestId) activeController = null;
    }
  }
  go.onclick = () => { page=1; load(); };
  filter.addEventListener('keydown', e => { if (e.key === 'Enter') { e.preventDefault();page=1;load(); } });
  prev.onclick = () => { if (page > 1) { page--; load(); } };
  next.onclick = () => { if (page < totalPages) { page++; load(); } };
  const observer = new MutationObserver(() => {
    if (visible()) load();
    else {
      requestId++;
      if (activeController) activeController.abort();
      activeController = null;
    }
  });
  observer.observe(root, {attributes:true, attributeFilter:['class']});
  if (visible()) load();
})();
