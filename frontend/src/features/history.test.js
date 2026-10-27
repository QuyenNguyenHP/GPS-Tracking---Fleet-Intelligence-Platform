import test from 'node:test';
import assert from 'node:assert/strict';
import { segments } from './history.js';
const point = (second, fix = true, device = 'a') => ({device_id: device, fix_valid: fix, latitude: 1, longitude: 103,
  recorded_at: new Date(Date.UTC(2026, 9, 27, 0, 0, second)).toISOString()});
test('breaks tracks at explicit no-fix events, long gaps and assignment changes', () => {
  assert.deepEqual(segments([point(0), point(5), point(10, false), point(15), point(60), point(65, true, 'b')]).map(s => s.length), [2, 1, 1, 1]);
});
test('empty and only no-fix history never invent coordinates', () => {
  assert.deepEqual(segments([]), []);
  assert.deepEqual(segments([point(0, false)]), []);
});
