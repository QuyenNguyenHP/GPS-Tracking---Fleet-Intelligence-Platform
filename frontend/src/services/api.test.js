import test from 'node:test';
import assert from 'node:assert/strict';
import {request} from './api.js';

test('aborts an unanswered login so the form can leave its busy state', async t => {
  let aborted = false;
  t.mock.method(globalThis, 'fetch', async (_url, {signal}) => new Promise((_resolve, reject) => {
    signal.addEventListener('abort', () => {aborted = true; reject(new DOMException('Aborted', 'AbortError'));});
  }));
  await assert.rejects(request('/auth/login', null, {method: 'POST', timeoutMs: 20}), /backend did not respond/);
  assert.equal(aborted, true);
});

test('timeout also covers a response body that stalls after headers', async t => {
  t.mock.method(globalThis, 'fetch', async (_url, {signal}) => ({ok: true,
    json: () => new Promise((_resolve, reject) => signal.addEventListener('abort', () => reject(new DOMException('Aborted', 'AbortError')))),
  }));
  await assert.rejects(request('/auth/login', null, {timeoutMs: 20}), /backend did not respond/);
});

test('reports unreachable backend proxy and preserves wrong-password messages', async t => {
  t.mock.method(globalThis, 'fetch', async () => ({ok: false, status: 502, json: async () => {throw new SyntaxError('not JSON');}}));
  await assert.rejects(request('/auth/login'), /Backend unavailable/);
  globalThis.fetch = async () => ({ok: false, status: 401, json: async () => ({detail: 'Incorrect username or password'})});
  await assert.rejects(request('/auth/login'), /Incorrect username or password/);
});

test('returns successful login and clears its deadline', async t => {
  let sent;
  t.mock.method(globalThis, 'fetch', async (url, options) => {
    sent = {url, options};
    return {ok: true, json: async () => ({token: 'test-session'})};
  });
  const result = await request('/auth/login', null, {method: 'POST', body: '{}', timeoutMs: 20});
  assert.equal(result.token, 'test-session');
  assert.equal(sent.url, '/api/v1/auth/login');
  assert.equal(sent.options.headers['Content-Type'], 'application/json');
  await new Promise(resolve => setTimeout(resolve, 30));
  assert.equal(sent.options.signal.aborted, false);
});
