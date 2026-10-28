import React, { useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import 'leaflet/dist/leaflet.css';
import './styles.css';
import './admin.css';
import Dashboard from './pages/Dashboard';
import Admin from './pages/Admin';
import { request } from './services/api';

function App() {
  const [auth, setAuth] = useState(null), [error, setError] = useState(''), [busy, setBusy] = useState(false);
  const [page, setPage] = useState('fleet');
  useEffect(() => {
    const expire = () => {setAuth(null); setError('Your session ended. Please sign in again.');};
    window.addEventListener('session-expired', expire);
    return () => window.removeEventListener('session-expired', expire);
  }, []);
  useEffect(() => {
    if (!auth) return;
    const timer = setTimeout(() => window.dispatchEvent(new Event('session-expired')),
      Math.max(0, Date.parse(auth.expires_at) - Date.now()));
    return () => clearTimeout(timer);
  }, [auth?.expires_at]);
  async function login(event) {
    event.preventDefault(); setBusy(true); setError('');
    const form = new FormData(event.target);
    try {
      const result = await request('/auth/login', null, {method: 'POST', body: JSON.stringify({
        username: form.get('username').trim(), password: form.get('password'),
      })});
      setAuth({...result, organization: result.user.organizations[0]?.id || ''});
      setPage(result.user.is_platform_admin ? 'admin' : 'fleet');
    } catch(e) {setError(e.message);} finally {setBusy(false);}
  }
  async function logout() {
    await request('/auth/logout', auth, {method: 'POST'});
    setAuth(null); setError('');
  }
  async function refreshProfile() {
    const user = await request('/auth/me', auth);
    setAuth(previous => previous ? {...previous, user,
      organization: user.organizations.some(o => o.id === previous.organization) ? previous.organization : user.organizations[0]?.id || '',
    } : null);
  }
  if (auth) {
    if (page === 'admin' && auth.user.is_platform_admin) return <Admin auth={auth} logout={logout} openFleet={() => setPage('fleet')} refreshProfile={refreshProfile}/>;
    return <>
      <div className="account-toolbar"><span>Signed in as <strong>{auth.user.name}</strong></span>
        <label>Workspace <select aria-label="Workspace" value={auth.organization} onChange={e => setAuth({...auth, organization: e.target.value})}>
          {auth.user.organizations.map(org => <option key={org.id} value={org.id}>{org.name}</option>)}
        </select></label>
        {auth.user.is_platform_admin && <button onClick={() => setPage('admin')}>Platform admin</button>}
      </div>
      {error && <p role="alert" className="error">{error}</p>}
      {auth.organization ? <Dashboard key={auth.organization} auth={auth} logout={() => logout().catch(e => setError(e.message))}/> : <main><h1>No active workspace</h1><p>Ask a platform administrator to assign your account to an active organization.</p><button onClick={() => refreshProfile().catch(e => setError(e.message))}>Refresh access</button> <button onClick={() => logout().catch(e => setError(e.message))}>Sign out</button></main>}
    </>;
  }
  return <main className="login"><div className="brand">◈ MERIDIAN</div><p className="eyebrow">FLEET INTELLIGENCE</p>
    <h1>A clearer view<br/>of every journey.</h1><p className="muted">Sign in to your account to continue.</p>
    <form onSubmit={login}><label>Username<input name="username" required autoComplete="username" maxLength={100}/></label>
      <label>Password<input name="password" type="password" required autoComplete="current-password" maxLength={128}/></label>
      {error && <p role="alert" className="error">{error}</p>}
      <button className="primary" disabled={busy}>{busy ? 'Signing in…' : 'Sign in →'}</button>
    </form><p className="muted">Contact your platform administrator if you need an account or password reset.</p>
  </main>;
}
createRoot(document.getElementById('root')).render(<App/>);
