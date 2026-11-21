/* Dacia Smart Control dashboard */
const appToken = localStorage.getItem('appToken') || '';
async function api(path, options = {}) {
  const res = await fetch(path, {
    headers: { 'X-App-Token': appToken, 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || res.statusText);
  }
  return res.json();
}
function showError(msg) {
  const el = document.getElementById('error');
  el.textContent = msg;
  el.classList.remove('hidden');
}
function clearError() { document.getElementById('error').classList.add('hidden'); }
function busy(els, promise) {
  els.forEach(el => (el.disabled = true));
  return promise.finally(() => els.forEach(el => (el.disabled = false)));
}
const CHARGING_STATES = new Set([0.1, 1, 2]); /* instant/scheduled/charging codes */

async function refresh() {
  try {
    clearError();
    const s = await api('/api/status');
    const b = s.battery || {};
    const c = s.cockpit || {};
    const h = s.hvac || {};
    document.getElementById('soc').textContent = (b.batteryLevel ?? '--') + '%';
    document.getElementById('battery-extra').textContent =
      'Range: ' + (b.batteryAutonomy ?? '?') + ' km';
    const charging = CHARGING_STATES.has(Number(b.chargingStatus));
    const pill = document.getElementById('charging');
    pill.textContent = charging
      ? '⚡ Charging' + (b.chargingRemainingTime ? ` (~${b.chargingRemainingTime} min left)` : '')
      : (b.plugStatus ? '🔌 Plugged in' : 'Not charging');
    pill.classList.toggle('on', charging);
    document.getElementById('charge-info').innerHTML =
      'Plugged in: <b>' + (b.plugStatus ? 'yes' : 'no') + '</b><br>' +
      'Battery temp: <b>' + (b.batteryTemperature ?? '?') + '°C</b>';
    document.getElementById('hvac-info').innerHTML =
      'HVAC: <b>' + (h.hvacStatus ?? '?') + '</b><br>' +
      'Outside: <b>' + (h.externalTemperature ?? '?') + '°C</b>';
    document.getElementById('vehicle-info').innerHTML =
      'Mileage: <b>' + Math.round(c.totalMileage ?? 0) + ' km</b>';
  } catch (e) {
    showError('Failed to load status: ' + e.message);
  }
}
function action(path, options) {
  return busy(
    Array.from(document.getElementsByTagName('button')),
    api(path, options).then(refresh).catch(e => showError(e.message))
  );
}
document.getElementById('btn-charge-start').onclick = () => action('/api/charge/start', { method: 'POST' });
document.getElementById('btn-hvac-start').onclick = () =>
  action('/api/hvac/start', {
    method: 'POST',
    body: JSON.stringify({ temperature: parseFloat(document.getElementById('temp').value) || 21 }),
  });
document.getElementById('btn-hvac-stop').onclick = () => action('/api/hvac/stop', { method: 'POST' });
document.getElementById('btn-horn').onclick = () => action('/api/horn', { method: 'POST' });
document.getElementById('btn-lights').onclick = () => action('/api/lights', { method: 'POST' });
document.getElementById('btn-location').onclick = () => action('/api/location/refresh', { method: 'POST' });

if (!appToken) {
  const t = prompt('App token (leave empty if none):');
  if (t !== null) { localStorage.setItem('appToken', t); location.reload(); }
} else {
  refresh();
  setInterval(refresh, 60000);
}
