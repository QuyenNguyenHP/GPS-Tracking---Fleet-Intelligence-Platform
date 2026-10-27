export function segments(points, gapSeconds = 30) {
  const result = [];
  let segment = [], previous;
  for (const p of points) {
    if (!p.fix_valid || (previous && (p.device_id !== previous.device_id ||
        Date.parse(p.recorded_at) - Date.parse(previous.recorded_at) > gapSeconds * 1000))) {
      if (segment.length) result.push(segment);
      segment = [];
    }
    if (p.fix_valid) segment.push([p.latitude, p.longitude]);
    previous = p;
  }
  if (segment.length) result.push(segment);
  return result;
}
