export async function request(path, auth) {
  const response = await fetch('/api/v1' + path, {headers: {
    Authorization: `Bearer ${auth.token}`, 'X-Organization-ID': auth.organization,
  }});
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === 'string' ? body.detail : `Request failed (${response.status})`);
  }
  return response.json();
}
