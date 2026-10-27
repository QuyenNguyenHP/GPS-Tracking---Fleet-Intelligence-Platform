import React, {useEffect, useRef, useState} from 'react';
import FleetMap from '../components/FleetMap';
import {useFleet} from '../hooks/useFleet';
import {request} from '../services/api';

const localInput = date => new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0,16);
export default function Dashboard({auth, logout}) {
  const {snapshot, connection, error} = useFleet(auth);
  const [selected, setSelected] = useState(''), [search, setSearch] = useState('');
  const [history, setHistory] = useState(null), [cursor, setCursor] = useState(0), [playing, setPlaying] = useState(false);
  const [from, setFrom] = useState(localInput(new Date(Date.now() - 3600000))), [to, setTo] = useState(localInput(new Date()));
  const [historyError, setHistoryError] = useState(''), [loading, setLoading] = useState(false);
  const historyRequest = useRef(0);
  const devices = snapshot.devices;
  const device = devices.find(d => d.device_id === selected), position = device?.position;
  const filtered = devices.filter(d => `${d.device_id} ${d.asset_name || ''}`.toLowerCase().includes(search.toLowerCase()));
  useEffect(() => {if (!selected && devices.length) setSelected(devices[0].device_id);}, [devices, selected]);
  useEffect(() => {
    if (!playing || !history?.length) return;
    const timer = setInterval(() => setCursor(c => {if (c >= history.length - 1) {setPlaying(false); return c;} return c + 1;}), 400);
    return () => clearInterval(timer);
  }, [playing, history]);
  function select(id) {historyRequest.current++; setSelected(id); setHistory(null); setPlaying(false); setHistoryError(''); setLoading(false);}
  async function loadHistory(event) {
    event.preventDefault();
    if (!position?.asset_id) return;
    const requestId = ++historyRequest.current;
    setLoading(true); setHistoryError(''); setPlaying(false);
    try {
      const start = new Date(from), end = new Date(to);
      if (!Number.isFinite(+start) || !Number.isFinite(+end) || end <= start) throw new Error('Choose a valid start and end time.');
      let all = [], offset = 0;
      do {
        const query = new URLSearchParams({from: start.toISOString(), to: end.toISOString(), limit: '5000', offset: String(offset)});
        const page = await request(`/assets/${position.asset_id}/positions?${query}`, auth);
        if (requestId !== historyRequest.current) return;
        all = all.concat(page.points); offset = page.next_offset;
        if (all.length >= 50000 && offset !== null) throw new Error('More than 50,000 samples. Choose a shorter range.');
      } while (offset !== null);
      setHistory(all); setCursor(0);
    } catch (e) {if (requestId === historyRequest.current) setHistoryError(e.message);}
    finally {if (requestId === historyRequest.current) setLoading(false);}
  }
  return <div className="dashboard">
    <header><a className="brand" href="/">◈ <span>MERIDIAN<small>FLEET INTELLIGENCE</small></span></a><span className="workspace">{auth.organization} workspace</span><button onClick={logout}>Sign out</button></header>
    <main><div className="page-title"><div><p className="eyebrow">OPERATIONS / LIVE TRACKING</p><h1>Your fleet, in focus.</h1><p className="muted">Live positions and recorded journeys. Built around your assets.</p></div><span className="connection">● {connection}</span></div>
      {(error || historyError) && <div role="alert" className="error">{error || historyError}</div>}
      <section className="stats">{[['Total devices', devices.length], ['Live', devices.filter(d => d.state === 'live').length], ['Stale GPS / report', devices.filter(d => d.state === 'stale').length], ['Offline', devices.filter(d => d.state === 'offline').length]].map(([label,value]) => <div key={label}><span>{label}</span><strong>{value.toString().padStart(2,'0')}</strong></div>)}</section>
      <section className="tracking"><aside><div className="panel-heading"><h2>Fleet devices</h2><span>{devices.length}</span></div><input aria-label="Search fleet" placeholder="Search asset or device…" value={search} onChange={e => setSearch(e.target.value)}/><div className="device-list">
        {!filtered.length && <p className="empty">No devices found. Seed a fleet or adjust your search.</p>}
        {filtered.map(d => <button key={d.device_id} className={`device ${selected === d.device_id ? 'selected' : ''}`} onClick={() => select(d.device_id)}><span className="device-icon">↗</span><span><strong>{d.asset_name || d.device_id}</strong><small>{d.device_id}</small></span><span className={`badge ${d.state}`}>{d.state}</span></button>)}
      </div><div className="legend">● Live &lt; 30s · stale &gt; 30s<br/>Offline after 120s without a report</div></aside>
      <div className="map-panel"><div className="map-title"><strong>{history ? 'Route history' : 'Live fleet map'}</strong><span>Singapore · synthetic demo</span></div><FleetMap devices={filtered} selected={selected} onSelect={select} history={history} cursor={cursor}/><div className="map-footer"><span>◉ {history ? `${history.length} recorded samples` : `${devices.filter(d => d.position).length} last-known positions`}</span><span>Gaps are never joined into assumed routes</span></div></div></section>
      <section className="details"><div><p className="eyebrow">SELECTED ASSET</p><h2>{device?.asset_name || selected || 'Select a device'}</h2><p className="muted">{position ? `${position.speed_kmh ?? '—'} km/h · Heading ${position.heading_deg ?? '—'}° · Satellites ${position.satellites ?? '—'}` : 'Waiting for first valid GPS fix'}</p><p className="muted">Last fix: {position ? new Date(position.recorded_at).toLocaleString() : '—'}</p></div>
      <form onSubmit={loadHistory} className="history-form"><label>From (local time)<input type="datetime-local" required value={from} onChange={e => setFrom(e.target.value)}/></label><label>To (local time)<input type="datetime-local" required value={to} onChange={e => setTo(e.target.value)}/></label><button className="primary" disabled={!position?.asset_id || loading}>{loading ? 'Loading…' : 'View journey'}</button></form></section>
      {history && <section className="playback"><button disabled={!history.length} onClick={() => {if(cursor === history.length - 1) setCursor(0); setPlaying(!playing);}}>{playing ? 'Pause' : 'Play'}</button><input aria-label="Playback position" type="range" min="0" max={Math.max(0, history.length - 1)} value={cursor} onChange={e => {setCursor(+e.target.value); setPlaying(false);}}/><span>{history.length ? `${new Date(history[cursor].recorded_at).toLocaleString()}${history[cursor].fix_valid ? '' : ' · No GPS fix'}` : 'No samples in this time range'}</span><button onClick={() => {setHistory(null); setPlaying(false);}}>Back to live</button></section>}
      <footer>Milestone A · Simulator workspace <span>Times shown in your browser’s timezone</span></footer>
    </main></div>;
}
