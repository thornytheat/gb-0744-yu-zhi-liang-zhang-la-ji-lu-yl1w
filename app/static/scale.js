const form = document.getElementById('calculate');
const notice = document.getElementById('notice');
form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const button = event.submitter;
  button.disabled = true;
  notice.value = '正在复算…';
  delete notice.dataset.error;
  try {
    const response = await fetch(form.action, {method: 'POST', body: new FormData(form)});
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail);
    location.assign(result.next);
  } catch (error) {
    notice.dataset.error = '';
    notice.value = error.message || '复算失败，请重试。';
    button.disabled = false;
  }
});
