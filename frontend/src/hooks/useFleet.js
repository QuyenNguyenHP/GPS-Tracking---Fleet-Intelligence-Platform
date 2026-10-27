import { useEffect, useState } from 'react';
import { request } from '../services/api';

export function useFleet(auth) {
  const [snapshot, setSnapshot] = useState({devices: []});
  const [connection, setConnection] = useState('Connecting');
  const [error, setError] = useState('');
  useEffect(() => {
    if (!auth) return;
    let active = true, socket, retry;
    const connect = async () => {
      try {
        const initial = await request('/devices/latest', auth);
        if (!active) return;
        setSnapshot(initial); setError('');
        socket = new WebSocket(`${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/api/v1/ws/locations`);
        socket.onopen = () => socket.send(JSON.stringify({token: auth.token, organization_id: auth.organization}));
        socket.onmessage = event => {
          if (active) {setSnapshot(JSON.parse(event.data)); setConnection('Live connection'); setError('');}
        };
        socket.onclose = () => {
          if (active) {setConnection('Disconnected · reconnecting'); retry = setTimeout(connect, 3000);}
        };
        socket.onerror = () => socket.close();
      } catch (e) {
        if (active) {setError(e.message); setConnection('Unavailable'); retry = setTimeout(connect, 5000);}
      }
    };
    connect();
    return () => {active = false; clearTimeout(retry); socket?.close();};
  }, [auth]);
  return {snapshot, connection, error};
}
