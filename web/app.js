'use strict';
const form = document.querySelector('#extract-form');
const submit = document.querySelector('#extract');
const statusLine = document.querySelector('#status');
const result = document.querySelector('#result');
const text = document.querySelector('#transcript');
const copy = document.querySelector('#copy');
const local = ['localhost', '127.0.0.1'].includes(location.hostname);
// On the Python host use its own origin; GitHub Pages needs a configured backend.
const api = (window.EXTRACTOR_API || (location.hostname.endsWith('.onrender.com') || local ? location.origin : '')).replace(/\/$/, '');
let current = null;

function status(message, kind = '') {
  statusLine.textContent = message;
  statusLine.className = `status ${kind}`;
}
if (!api) {
  submit.disabled = true;
  status('Website preview · Online extraction is not connected yet. Use the downloadable Python tool below.');
} else {
  status('Ready for a YouTube link. Captions must be available.');
}

form.addEventListener('submit', async event => {
  event.preventDefault();
  if (!api) return;
  current = null;
  result.hidden = true;
  submit.disabled = true;
  submit.textContent = 'Getting captions…';
  status('Retrieving captions. If the free server is waking up, this may take a minute.');
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 120000);
  try {
    const response = await fetch(`${api}/api/transcript`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: document.querySelector('#video-url').value.trim(), language: document.querySelector('#language').value }),
      signal: controller.signal,
    });
    const data = await response.json().catch(() => null);
    if (!response.ok) throw new Error(typeof data?.detail === 'string' ? data.detail : 'The service could not complete this request. Please try again later.');
    if (!data || typeof data.text !== 'string' || typeof data.srt !== 'string' || typeof data.json !== 'string' || !/^[\w-]{11}$/.test(data.video_id)) throw new Error('The server returned an invalid transcript response.');
    current = data;
    text.value = data.text;
    document.querySelector('#metadata').textContent = `${data.language} (${data.language_code}) · ${data.is_generated ? 'Automatic' : 'Manual'} captions · ${data.video_id}`;
    result.hidden = false;
    status('Transcript ready. Caption wording is preserved.', 'success');
    document.querySelector('#result-title').setAttribute('tabindex', '-1');
    document.querySelector('#result-title').focus({ preventScroll: true });
  } catch (error) {
    status(error.name === 'AbortError' ? 'The server took too long to respond. Please try again shortly.' : error instanceof TypeError ? 'Cannot reach the extractor service. Please try again later or use the Python tool.' : error.message, 'error');
  } finally {
    clearTimeout(timer);
    submit.disabled = false;
    submit.textContent = 'Get transcript';
  }
});

copy.addEventListener('click', async () => {
  if (!current) return;
  try {
    await navigator.clipboard.writeText(current.text);
    status('Transcript copied.', 'success');
  } catch {
    text.focus();
    text.select();
    status('Select and copy the highlighted transcript with your keyboard or browser menu.');
  }
});
document.querySelectorAll('[data-format]').forEach(button => button.addEventListener('click', () => {
  if (!current) return;
  const format = button.dataset.format;
  const content = { txt: current.text, srt: current.srt, json: current.json }[format];
  const type = { txt: 'text/plain;charset=utf-8', srt: 'text/plain;charset=utf-8', json: 'application/json;charset=utf-8' }[format];
  const url = URL.createObjectURL(new Blob([content + '\n'], { type }));
  const link = document.createElement('a');
  link.href = url;
  link.download = `${current.video_id}.${format}`;
  document.body.append(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}));
