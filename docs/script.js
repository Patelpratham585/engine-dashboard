const thresholds = { normal: 105, warning: 115, critical: 125 };
const colors = { normal: '#3ecf8e', elevated: '#e8c04a', warning: '#ff9a3d', critical: '#ff4f4f' };
const statusMessage = { elevated: 'Coolant temperature is elevated. Keep an eye on it.', warning: 'Engine is overheating. Reduce load and check the cooling system.', critical: 'CRITICAL temperature. Shut down the engine to prevent damage.' };
const history = [];
let state = { temp: 90, rpm: 900, oil: 45, load: 25, fault: null };

const statusFor = temp => temp >= thresholds.critical ? 'critical' : temp >= thresholds.warning ? 'warning' : temp >= thresholds.normal ? 'elevated' : 'normal';
const chart = new Chart(document.getElementById('tempChart'), {
  type: 'line', data: { labels: [], datasets: [
    { label: 'Coolant temp (°C)', data: [], borderColor: colors.normal, backgroundColor: 'rgba(62, 207, 142, .08)', borderWidth: 2, pointRadius: 0, tension: .25, fill: true, segment: { borderColor: c => colors[statusFor(c.p1.parsed.y)] } },
    { label: 'Warning (115°C)', data: [], borderColor: 'rgba(255,154,61,.5)', borderWidth: 1, borderDash: [6, 4], pointRadius: 0 },
    { label: 'Critical (125°C)', data: [], borderColor: 'rgba(255,79,79,.5)', borderWidth: 1, borderDash: [6, 4], pointRadius: 0 }
  ] }, options: { responsive: true, animation: false, interaction: { intersect: false, mode: 'index' }, scales: { x: { ticks: { color: '#8b939c', maxTicksLimit: 8, font: { family: 'IBM Plex Mono', size: 10 } }, grid: { color: 'rgba(255,255,255,.04)' } }, y: { min: 15, max: 140, ticks: { color: '#8b939c', font: { family: 'IBM Plex Mono', size: 10 } }, grid: { color: 'rgba(255,255,255,.04)' } } }, plugins: { legend: { labels: { color: '#8b939c', font: { family: 'IBM Plex Mono', size: 11 }, boxWidth: 12 } } } }
});

function step() {
  state.load = Math.max(0, Math.min(100, state.load + (Math.random() - .52) * 8 + (35 - state.load) * .04));
  if (state.fault === 'high_load') state.load = Math.min(100, state.load + 8);
  state.rpm += (800 + state.load * 38 - state.rpm) * .15 + (Math.random() - .5) * 80;
  const faultHeat = state.fault === 'high_load' ? 25 : state.fault === 'stuck_thermostat' ? 12 : state.fault === 'coolant_loss' ? 18 : 0;
  const target = 90 + state.load * .35 + faultHeat;
  const cooling = state.fault === 'coolant_loss' ? .006 : state.fault === 'stuck_thermostat' ? .014 : .06;
  state.temp += (target - state.temp) * (state.temp < target ? .08 : cooling) + (Math.random() - .5) * .5;
  state.temp = Math.max(22, Math.min(140, state.temp));
  state.oil = Math.max(5, Math.min(60, 45 - Math.max(0, state.temp - 105) * .4 + (Math.random() - .5) * 1.6));
  history.push({ time: new Date(), temp: state.temp, rpm: state.rpm, oil: state.oil, load: state.load, status: statusFor(state.temp) });
  if (history.length > 600) history.shift();
  render();
}
function render() {
  const readings = history.slice(-90), latest = readings[readings.length - 1], rig = document.getElementById('rig');
  const status = latest.status; rig.dataset.status = status;
  document.getElementById('temp-value').textContent = latest.temp.toFixed(1); document.getElementById('rpm-value').textContent = Math.round(latest.rpm).toLocaleString(); document.getElementById('oil-value').textContent = latest.oil.toFixed(1); document.getElementById('load-value').textContent = latest.load.toFixed(0);
  document.getElementById('rpm-bar').style.width = `${Math.min(100, latest.rpm / 70)}%`; document.getElementById('oil-bar').style.width = `${Math.min(100, latest.oil / .6)}%`; document.getElementById('load-bar').style.width = `${latest.load}%`;
  const alert = document.getElementById('alert-rail'); alert.hidden = status === 'normal'; if (status !== 'normal') document.getElementById('alert-text').textContent = statusMessage[status] + (state.fault ? ` (active fault: ${state.fault.replaceAll('_', ' ')})` : '');
  const temps = readings.map(r => r.temp); const avg = temps.slice(-10).reduce((a, b) => a + b, 0) / Math.min(10, temps.length); chart.data.labels = readings.map(r => r.time.toLocaleTimeString()); chart.data.datasets[0].data = temps; chart.data.datasets[1].data = temps.map(() => 115); chart.data.datasets[2].data = temps.map(() => 125); chart.update('none');
  const set = (id, value) => document.getElementById(id).textContent = value; set('stat-avg', `${avg.toFixed(1)}°C`); set('stat-max', `${Math.max(...temps).toFixed(1)}°C`); set('stat-min', `${Math.min(...temps).toFixed(1)}°C`); set('stat-mean', `${(temps.reduce((a, b) => a + b, 0) / temps.length).toFixed(1)}°C`); set('stat-overheat', `${Math.round(history.filter(r => r.status === 'warning' || r.status === 'critical').length / 2)}s`); set('stat-count', history.length);
}
document.querySelectorAll('.control-buttons button').forEach(button => button.addEventListener('click', () => { state.fault = button.dataset.fault === 'clear' ? null : button.dataset.fault; }));
document.getElementById('export-link').addEventListener('click', event => { event.preventDefault(); const rows = ['timestamp,coolant_temp_c,rpm,oil_pressure_psi,load_pct,status', ...history.map(r => `${r.time.toISOString()},${r.temp.toFixed(1)},${Math.round(r.rpm)},${r.oil.toFixed(1)},${r.load.toFixed(1)},${r.status}`)]; const link = document.createElement('a'); link.href = URL.createObjectURL(new Blob([rows.join('\n')], { type: 'text/csv' })); link.download = 'engine_sensor_log.csv'; link.click(); URL.revokeObjectURL(link.href); });
for (let i = 0; i < 30; i++) step(); setInterval(step, 500);
