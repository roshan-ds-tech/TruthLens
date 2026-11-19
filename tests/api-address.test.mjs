import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';

const source = readFileSync(new URL('../src/api/client.js', import.meta.url), 'utf8')
  .replace(/^import .* from 'react';$/m, '')
  .replaceAll('import.meta.env.VITE_API_BASE', "'https://old.example'")
  .replaceAll('import.meta.env.PROD', 'true')
  .replaceAll('export ', '');
function client(fetch) {
  const context = vm.createContext({ fetch, URL, localStorage: { getItem: () => null } });
  vm.runInContext(source + '\nglobalThis.client = api;', context);
  return context.client;
}
const response = (body, status = 200) => ({ ok: status < 400, status,
  json: async () => body, text: async () => JSON.stringify(body) });

for (const action of ['get', 'login']) test(`${action} recovers a changed demo address`, async () => {
  const calls = [];
  const api = client(async (url, opts) => {
    calls.push({ url, opts });
    if (url.startsWith('https://old.example')) throw new TypeError('Network error');
    if (url === '/api-config.json') return response({ apiBase: 'https://new.example/' });
    return response({ ok: true });
  });
  const result = action === 'get' ? await api.get('/health') : await api.post('/auth/login', { email: 'qa', password: 'test' });
  assert.equal(result.ok, true);
  assert.equal(calls.length, 3);
  assert.equal(calls[1].opts.cache, 'no-store');
  assert.equal(calls[2].url, `https://new.example/api/${action === 'get' ? 'health' : 'auth/login'}`);
  if (action === 'login') assert.equal(calls[0].opts.body, calls[2].opts.body);
});

test('a failed write is not replayed', async () => {
  const calls = [];
  const api = client(async (url) => {
    calls.push(url);
    if (url === '/api-config.json') return response({ apiBase: 'https://new.example' });
    throw new TypeError('Network error');
  });
  await assert.rejects(api.post('/cases', { title: 'Test' }));
  assert.deepEqual(calls, ['https://old.example/api/cases', '/api-config.json']);
});

test('incorrect credentials are reported without retry', async () => {
  let calls = 0;
  const api = client(async () => { calls++; return response({ detail: 'Invalid credentials' }, 401); });
  await assert.rejects(api.post('/auth/login', {}), /Invalid credentials/);
  assert.equal(calls, 1);
});

test('an insecure replacement address is ignored', async () => {
  const calls = [];
  const api = client(async (url) => {
    calls.push(url);
    if (url === '/api-config.json') return response({ apiBase: 'http://new.example' });
    throw new TypeError('Network error');
  });
  await assert.rejects(api.get('/health'));
  assert.equal(calls.length, 2);
});
