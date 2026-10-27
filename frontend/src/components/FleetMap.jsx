import React, { useEffect } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, Polyline, useMap } from 'react-leaflet';
import { segments } from '../features/history';

function Focus({position}) {
  const map = useMap();
  useEffect(() => {if (position) map.panTo([position.latitude, position.longitude]);}, [position?.device_id]);
  return null;
}

export default function FleetMap({devices, selected, onSelect, history, cursor}) {
  const current = devices.find(d => d.device_id === selected)?.position;
  const replay = history?.[cursor];
  return <MapContainer center={[1.297, 103.849]} zoom={13} className="map" scrollWheelZoom>
    <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      url="https://tile.openstreetmap.org/{z}/{x}/{y}.png" />
    <Focus position={current}/>
    {!history && devices.filter(d => d.position).map(d => <CircleMarker key={d.device_id}
      center={[d.position.latitude, d.position.longitude]} radius={d.device_id === selected ? 10 : 7}
      pathOptions={{color: '#fff', weight: 2, fillColor: d.state === 'live' ? '#087f75' : d.state === 'stale' ? '#c08024' : '#737e86', fillOpacity: 1}}
      eventHandlers={{click: () => onSelect(d.device_id)}}>
      <Popup><strong>{d.asset_name || d.device_id}</strong><br/>{d.state} · {d.position.speed_kmh ?? '—'} km/h<br/>{new Date(d.position.recorded_at).toLocaleString()}</Popup>
    </CircleMarker>)}
    {history && segments(history).map((line, i) => <Polyline key={i} positions={line} pathOptions={{color: '#087f75', weight: 4}}/>)}
    {replay?.fix_valid && <CircleMarker center={[replay.latitude, replay.longitude]} radius={9} pathOptions={{color:'#f29243', fillOpacity:1}}/>}
  </MapContainer>;
}
