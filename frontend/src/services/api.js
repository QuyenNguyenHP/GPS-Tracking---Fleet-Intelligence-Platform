export async function request(path, auth, options = {}) {
  const {timeoutMs = 15000, signal, ...settings} = options;
  const controller = new AbortController();
  let timedOut = false;
  const cancel = () => controller.abort();
  if (signal?.aborted) cancel();
  else signal?.addEventListener('abort', cancel, {once: true});
  const timer = setTimeout(() => {timedOut = true; controller.abort();}, timeoutMs);
  try {
    const response = await fetch('/api/v1' + path, {...settings, signal: controller.signal, headers: {
      ...(auth ? {Authorization: `Bearer ${auth.token}`, 'X-Organization-ID': auth.organization || ''} : {}),
      ...(settings.body ? {'Content-Type': 'application/json'} : {}),
      ...settings.headers,
    }});
    if (!response.ok) {
      const body = await response.json().catch(error => {
        if (controller.signal.aborted) throw error;
        return {};
      });
      if (response.status === 401 && auth) window.dispatchEvent(new Event('session-expired'));
      const detail = Array.isArray(body.detail) ? body.detail.map(item => `${item.loc.at(-1)}: ${item.msg}`).join('; ') : body.detail;
      const fallback = response.status >= 500
        ? `Backend unavailable or returned an error (${response.status}). Check the backend terminal and that both servers are running in the same WSL environment.`
        : `Request failed (${response.status})`;
      throw new Error(typeof detail === 'string' ? detail : fallback);
    }
    return await response.json();
  } catch (error) {
    if (timedOut) throw new Error('The backend did not respond within 15 seconds. Check the backend terminal, then try again.');
    if (error instanceof TypeError) throw new Error('Cannot connect to the server. Check that the frontend and backend are running, then try again.');
    throw error;
  } finally {
    clearTimeout(timer);
    signal?.removeEventListener('abort', cancel);
  }
}
