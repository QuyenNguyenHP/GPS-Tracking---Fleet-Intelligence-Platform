import React, {useEffect, useRef, useState} from 'react';
import {request} from '../services/api';

const emptyUser = {username: '', name: '', password: '', enabled: true, is_platform_admin: false, organization_ids: []};
const emptyOrg = {id: '', name: '', enabled: true};

export default function Admin({auth, logout, openFleet, refreshProfile}) {
  const [organizations, setOrganizations] = useState([]), [users, setUsers] = useState([]);
  const [tab, setTab] = useState('organizations'), [search, setSearch] = useState('');
  const [editor, setEditor] = useState(null), [form, setForm] = useState({});
  const [error, setError] = useState(''), [notice, setNotice] = useState('');
  const [loading, setLoading] = useState(true), [saving, setSaving] = useState(false);
  const dialog = useRef(null);
  async function load() {
    const [orgs, accounts] = await Promise.all([request('/admin/organizations', auth), request('/admin/users', auth)]);
    setOrganizations(orgs); setUsers(accounts);
  }
  useEffect(() => {load().catch(e => setError(e.message)).finally(() => setLoading(false));}, [auth.token]);
  useEffect(() => {if (editor) dialog.current?.showModal();}, [editor]);
  function edit(kind, item) {
    setError(''); setNotice(''); setEditor({kind, id: item?.id});
    setForm(kind === 'users' ? {...emptyUser, ...item, password: ''} : {...emptyOrg, ...item});
  }
  function close() {dialog.current?.close(); setEditor(null); setError('');}
  function change(key, value) {setForm(previous => ({...previous, [key]: value}));}
  async function save(event) {
    event.preventDefault(); setSaving(true); setError(''); setNotice('');
    try {
      const body = {...form};
      delete body.id;
      if (editor.kind === 'organizations' && !editor.id) body.id = form.id;
      if (editor.kind === 'users' && editor.id) {
        delete body.username;
        if (!body.password) delete body.password;
      }
      const url = `/admin/${editor.kind}${editor.id ? '/' + encodeURIComponent(editor.id) : ''}`;
      await request(url, auth, {method: editor.id ? 'PUT' : 'POST', body: JSON.stringify(body)});
      const resetSelf = editor.kind === 'users' && editor.id === auth.user.id && !!body.password;
      close();
      if (resetSelf) {window.dispatchEvent(new Event('session-expired')); return;}
      setNotice(editor.kind === 'users' ? 'Account saved. Access changes take effect immediately.' : 'Organization saved.');
      await load();
      await refreshProfile();
    } catch(e) {setError(e.message);} finally {setSaving(false);}
  }
  const query = search.toLowerCase();
  const filteredOrgs = organizations.filter(org => `${org.id} ${org.name}`.toLowerCase().includes(query));
  const filteredUsers = users.filter(user => `${user.username || ''} ${user.name}`.toLowerCase().includes(query));
  const self = editor?.kind === 'users' && editor.id === auth.user.id;
  return <div className="admin-page">
    <header><a className="brand" href="/">◈ <span>MERIDIAN<small>PLATFORM ADMINISTRATION</small></span></a>
      <span className="workspace">{auth.user.name}</span><button onClick={openFleet}>Fleet workspace</button><button onClick={() => logout().catch(e => setError(e.message))}>Sign out</button></header>
    <main><div className="page-title"><div><p className="eyebrow">PLATFORM / ADMINISTRATION</p><h1>Manage your platform.</h1><p className="muted">Organizations, accounts and access across every workspace.</p></div><span className="connection">Platform administrator</span></div>
      <section className="stats"><div><span>Organizations</span><strong>{organizations.length}</strong></div><div><span>Active organizations</span><strong>{organizations.filter(o => o.enabled).length}</strong></div><div><span>User accounts</span><strong>{users.length}</strong></div><div><span>Platform administrators</span><strong>{users.filter(u => u.is_platform_admin && u.enabled).length}</strong></div></section>
      {!editor && error && <p role="alert" className="error">{error}</p>}
      {notice && <p role="status" className="success">{notice}</p>}
      <section className="admin-panel"><div className="admin-actions"><div className="admin-tabs" role="tablist" aria-label="Administration sections">
        <button role="tab" aria-selected={tab === 'organizations'} onClick={() => {setTab('organizations'); setSearch('');}}>Organizations</button>
        <button role="tab" aria-selected={tab === 'users'} onClick={() => {setTab('users'); setSearch('');}}>Users</button>
      </div><input aria-label="Search records" placeholder={`Search ${tab}…`} value={search} onChange={e => setSearch(e.target.value)}/>
        <button className="primary" disabled={loading} onClick={() => edit(tab)}>+ {tab === 'users' ? 'Create account' : 'Create organization'}</button></div>
      {loading ? <p className="empty">Loading platform records…</p> : <div className="table-scroll"><table>
        <thead><tr>{(tab === 'organizations' ? ['Organization', 'ID', 'Status', 'Members', 'Actions'] : ['Account', 'Role', 'Workspaces', 'Status', 'Actions']).map(label => <th key={label}>{label}</th>)}</tr></thead>
        <tbody>{tab === 'organizations' ? filteredOrgs.map(org => <tr key={org.id}><td><strong>{org.name}</strong></td><td><code>{org.id}</code></td><td><span className={`badge ${org.enabled ? 'live' : 'offline'}`}>{org.enabled ? 'Active' : 'Disabled'}</span></td><td>{users.filter(u => u.organization_ids.includes(org.id)).length}</td><td><button onClick={() => edit('organizations', org)}>Edit organization</button></td></tr>) : filteredUsers.map(user => <tr key={user.id}><td><strong>{user.name}</strong><small>{user.username || 'Legacy API identity (no account login)'}</small></td><td>{user.is_platform_admin ? 'Platform admin' : 'Viewer'}</td><td>{user.organization_ids.map(id => organizations.find(o => o.id === id)?.name || id).join(', ') || 'No workspaces'}</td><td><span className={`badge ${user.enabled ? 'live' : 'offline'}`}>{user.enabled ? 'Active' : 'Disabled'}</span></td><td><button onClick={() => edit('users', user)}>Edit account</button></td></tr>)}</tbody>
      </table>{!(tab === 'organizations' ? filteredOrgs.length : filteredUsers.length) && <p className="empty">No matching records.</p>}</div>}
      </section><footer>Account changes apply to API and live-map access. <span>Signed in as {auth.user.username}</span></footer>
    </main>
    {editor && <dialog ref={dialog} className="admin-dialog" aria-labelledby="editor-title" onCancel={event => {if(saving) event.preventDefault(); else close();}}>
      <h2 id="editor-title">{editor.id ? 'Edit' : 'Create'} {editor.kind === 'users' ? 'account' : 'organization'}</h2>
      <form onSubmit={save}>
        {editor.kind === 'organizations' ? <>
          <label>Organization ID<input autoFocus required disabled={!!editor.id || saving} value={form.id} pattern="[a-z0-9][a-z0-9-]{0,63}" maxLength={64} onChange={e => change('id', e.target.value)} placeholder="e.g. north-logistics"/></label>
          <label>Organization name<input required value={form.name} maxLength={200} onChange={e => change('name', e.target.value)} disabled={saving}/></label>
          <label className="check-label"><input type="checkbox" checked={form.enabled} onChange={e => change('enabled', e.target.checked)} disabled={saving}/> Active organization</label>
          <p className="muted">Disabling an organization blocks its workspace access and device uploads. Stored history is retained.</p>
        </> : <>
          <label>Username<input autoFocus required={!editor.id} disabled={!!editor.id || saving} value={form.username || ''} maxLength={100} autoComplete="off" onChange={e => change('username', e.target.value)}/></label>
          <label>Display name<input required value={form.name} maxLength={200} onChange={e => change('name', e.target.value)} disabled={saving}/></label>
          <label>{editor.id ? 'New password (leave blank to keep current)' : 'Password'}<input type="password" minLength={8} maxLength={128} required={!editor.id} autoComplete="new-password" value={form.password} onChange={e => change('password', e.target.value)} disabled={saving || (!!editor.id && !form.username)}/></label>
          <p className="muted">Use at least 8 characters. Resetting a password signs the account out of all sessions.</p>
          <label className="check-label"><input type="checkbox" checked={form.enabled} disabled={self || saving} onChange={e => change('enabled', e.target.checked)}/> Account enabled</label>
          <label className="check-label"><input type="checkbox" checked={form.is_platform_admin} disabled={self || saving || (!!editor.id && !form.username)} onChange={e => change('is_platform_admin', e.target.checked)}/> Platform administrator — can manage all organizations and users</label>
          <fieldset disabled={saving}><legend>Workspace access</legend>{organizations.map(org => <label className="check-label" key={org.id}><input type="checkbox" checked={form.organization_ids.includes(org.id)} onChange={e => change('organization_ids', e.target.checked ? [...form.organization_ids, org.id] : form.organization_ids.filter(id => id !== org.id))}/>{org.name}{!org.enabled && ' (disabled)'}</label>)}{!organizations.length && <p>Create an organization to grant workspace access.</p>}</fieldset>
          <p className="muted">Workspace access controls the fleet map. Platform administration does not automatically grant access to fleet data.</p>
        </>}
        {error && <p role="alert" className="error">{error}</p>}
        <div className="dialog-actions"><button type="button" onClick={close} disabled={saving}>Cancel</button><button type="submit" className="primary" disabled={saving}>{saving ? 'Saving…' : 'Save changes'}</button></div>
      </form>
    </dialog>}
  </div>;
}
