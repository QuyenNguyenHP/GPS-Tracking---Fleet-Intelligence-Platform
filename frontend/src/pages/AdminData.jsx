import React, {useEffect, useRef, useState} from 'react';
import {request} from '../services/api';
import '../data-explorer.css';

const localInput = date => new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0,16);
const displayTime = value => value ? new Date(value).toLocaleString() : '—';
export default function AdminData({auth, organizations}) {
  const [organization, setOrganization] = useState(organizations.some(o => o.id === 'demo') ? 'demo' : '');
  const [inventory, setInventory] = useState({devices: [], database: ''});
  const [device, setDevice] = useState(''), [includeDisabled, setIncludeDisabled] = useState(false);
  const [from, setFrom] = useState(localInput(new Date(Date.now()-3600000)));
  const [to, setTo] = useState(localInput(new Date(Date.now()+60000)));
  const [fix, setFix] = useState('all'), [sequence, setSequence] = useState('');
  const [result, setResult] = useState(null), [applied, setApplied] = useState(null);
  const [error, setError] = useState(''), [loading, setLoading] = useState(false), [inventoryLoading, setInventoryLoading] = useState(false);
  const [detail, setDetail] = useState(null);
  const serial = useRef(0), dialog = useRef(null);
  useEffect(() => {
    let active = true;
    setInventoryLoading(true); setInventory({devices: [], database: ''});
    request('/admin/devices' + (organization ? '?organization_id=' + encodeURIComponent(organization) : ''), auth)
      .then(data => {if(active) setInventory(data);}).catch(e => {if(active) setError(e.message);})
      .finally(() => {if(active) setInventoryLoading(false);});
    return () => {active = false;};
  }, [organization, auth.token]);
  useEffect(() => {if(detail) dialog.current?.showModal();}, [detail]);
  useEffect(() => () => {serial.current++;}, []);
  function resetResults() {serial.current++; setResult(null); setApplied(null); setLoading(false); setError('');}
  function changeOrganization(value) {setOrganization(value); setDevice(''); resetResults();}
  async function query(filters, offset = 0) {
    const id = ++serial.current;
    setLoading(true); setError('');
    try {
      const params = new URLSearchParams({...filters, offset: String(offset), limit: '50'});
      const data = await request('/admin/telemetry?' + params, auth);
      if(id === serial.current) {setResult(data); setApplied(filters);}
    } catch(e) {if(id === serial.current) {setError(e.message); setResult(null);}}
    finally {if(id === serial.current) setLoading(false);}
  }
  function submit(event) {
    event.preventDefault();
    const start = new Date(from), end = new Date(to);
    if(!Number.isFinite(+start) || !Number.isFinite(+end) || end <= start || end-start > 7*86400000) {
      setError('Chọn khoảng thời gian hợp lệ, tối đa 7 ngày.'); return;
    }
    const filters = {from: start.toISOString(), to: end.toISOString(), fix};
    if(organization) filters.organization_id = organization;
    if(device) filters.device_id = device;
    if(sequence) filters.sequence_number = sequence;
    query(filters);
  }
  const visibleDevices = inventory.devices.filter(d => includeDisabled || d.enabled);
  return <section className="data-explorer">
    <div className="collection-guide"><h2>Thu thập dữ liệu từ 20 thiết bị</h2>
      <ol className="pipeline"><li><strong>1. Thu mẫu</strong><span>Mỗi thiết bị tạo một mẫu GPS mỗi 5 giây; ghi thời gian thu và số thứ tự riêng.</span></li>
        <li><strong>2. Gửi đồng thời</strong><span>Simulator dùng tối đa 20 luồng gửi HTTP độc lập. Mẫu được lưu vào hàng đợi trước khi gửi.</span></li>
        <li><strong>3. Kiểm tra & lưu</strong><span>API xác thực từng thiết bị, kiểm tra dữ liệu, loại bản trùng và ghi database trong transaction.</span></li>
        <li><strong>4. Xác nhận</strong><span>Server commit xong mới trả ACK. Simulator chỉ xóa các mẫu đã được xác nhận khỏi hàng đợi.</span></li>
        <li><strong>5. Hiển thị</strong><span>Bản đồ lấy vị trí hợp lệ mới nhất mỗi 2 giây. Bảng dưới truy vấn lịch sử đã lưu khi bạn nhấn Tra cứu.</span></li></ol>
      <p className="muted">Hiện tại là GPS giả lập, chưa phải dữ liệu phần cứng. Chế độ normal không cố ý tạo mất mạng; resilience thử mất mạng, mất GPS, gửi trùng và gửi bù. SQLite ghi tuần tự; gửi đồng thời không có nghĩa mọi bản ghi được commit cùng thời điểm.</p>
    </div>
    <div className="data-toolbar"><label>Công ty<select value={organization} onChange={e => changeOrganization(e.target.value)}><option value="">Tất cả công ty</option>{organizations.map(o => <option key={o.id} value={o.id}>{o.name}</option>)}</select></label>
      <span>Database: <strong>{inventory.database || '…'}</strong> · <strong>{inventory.devices.filter(d => d.enabled).length}</strong> thiết bị đang bật</span>
      <label className="check-label"><input type="checkbox" checked={includeDisabled} onChange={e => setIncludeDisabled(e.target.checked)}/> Hiện thiết bị đã tắt ({inventory.devices.filter(d => !d.enabled).length})</label></div>
    <details className="device-inventory"><summary>Danh sách thiết bị ({visibleDevices.length})</summary>
      {inventoryLoading ? <p>Đang tải thiết bị…</p> : <div className="table-scroll"><table><thead><tr><th>Thiết bị</th><th>Tài sản</th><th>Công ty</th><th>Trạng thái</th><th>Nhận gần nhất</th><th/></tr></thead><tbody>{visibleDevices.map(d => <tr key={d.id}><td>{d.id}</td><td>{d.asset_name || '—'}</td><td>{d.organization_name}</td><td>{d.enabled ? 'Đang bật' : 'Đã tắt'}</td><td>{displayTime(d.last_seen_at)}</td><td><button onClick={() => {setDevice(d.id); resetResults();}}>Chọn tra cứu</button></td></tr>)}</tbody></table></div>}
    </details>
    <form className="data-filters" onSubmit={submit}>
      <label>Thiết bị<select value={device} onChange={e => {setDevice(e.target.value); resetResults();}}><option value="">Tất cả thiết bị</option>{inventory.devices.map(d => <option key={d.id} value={d.id}>{d.id}{!d.enabled ? ' (đã tắt)' : ''}</option>)}</select></label>
      <label>Từ (giờ địa phương)<input type="datetime-local" required value={from} onChange={e => setFrom(e.target.value)}/></label>
      <label>Đến (giờ địa phương)<input type="datetime-local" required value={to} onChange={e => setTo(e.target.value)}/></label>
      <label>GPS<select value={fix} onChange={e => setFix(e.target.value)}><option value="all">Tất cả</option><option value="valid">Có vị trí hợp lệ</option><option value="invalid">Không có GPS fix</option></select></label>
      <label>Sequence (tùy chọn)<input aria-label="Sequence" value={sequence} inputMode="numeric" pattern="[0-9]*" onChange={e => setSequence(e.target.value)}/></label>
      <button className="primary" disabled={loading}>{loading ? 'Đang truy vấn…' : 'Tra cứu database'}</button>
      <button type="button" onClick={() => setTo(localInput(new Date(Date.now()+60000)))}>Đến hiện tại</button>
    </form>
    <p className="muted">Lọc theo thời điểm thu mẫu (recorded_at), tối đa 7 ngày/lần. received_at là lúc server nhận; độ trễ giúp nhận biết dữ liệu gửi bù. Thiết bị đã tắt vẫn có lịch sử.</p>
    {error && <p role="alert" className="error">{error}</p>}
    {result ? <><div className="data-toolbar"><strong>{result.total.toLocaleString()} bản ghi phù hợp</strong><span>Truy vấn lúc {displayTime(result.queried_at)} · 50 bản ghi/trang</span></div>
      <div className="table-scroll"><table><thead><tr><th>ID / sequence</th><th>Thiết bị / công ty</th><th>Thu mẫu</th><th>Server nhận</th><th>Trễ (s)</th><th>GPS / tọa độ</th><th>km/h</th><th/></tr></thead><tbody>{result.records.map(row => <tr key={row.id}><td>{row.id}<small>{row.sequence_number}</small></td><td>{row.device_id}<small>{row.organization_id}</small></td><td>{displayTime(row.recorded_at)}</td><td>{displayTime(row.received_at)}</td><td>{row.latency_seconds}</td><td>{row.fix_valid ? `${row.latitude}, ${row.longitude}` : 'Không có fix'}</td><td>{row.speed_kmh ?? '—'}</td><td><button onClick={() => setDetail(row)}>Xem JSON</button></td></tr>)}</tbody></table></div>
      {!result.records.length && <p className="empty">Không có dữ liệu phù hợp. Kiểm tra simulator và khoảng thời gian.</p>}
      <div className="data-toolbar"><button disabled={loading || result.offset === 0} onClick={() => query(applied, Math.max(0, result.offset-50))}>Trang trước</button><span>{result.total ? result.offset+1 : 0}–{result.offset+result.records.length} / {result.total}</span><button disabled={loading || result.next_offset === null} onClick={() => query(applied, result.next_offset)}>Trang sau</button><button disabled={loading} onClick={() => query(applied, 0)}>Làm mới kết quả</button></div>
    </> : !loading && <p className="empty">Chọn bộ lọc rồi nhấn Tra cứu database để xem dữ liệu đã lưu.</p>}
    {detail && <dialog ref={dialog} className="admin-dialog telemetry-dialog" onCancel={() => setDetail(null)}><h2>Bản ghi #{detail.id}</h2><p className="muted">Payload đã được kiểm tra và lưu trong bảng positions; không chứa khóa xác thực.</p><pre>{JSON.stringify(detail, null, 2)}</pre><button onClick={() => {dialog.current.close(); setDetail(null);}}>Đóng</button></dialog>}
  </section>;
}
