/* script.js — polls the Flask API and renders a live Chart.js line
 * graph plus simple bar gauges, coloring everything by the current
 * overheat status returned by the backend. */

const POLL_MS = 1000;
const HISTORY_POINTS = 90;

const rig = document.getElementById('rig');
const alertRail = document.getElementById('alert-rail');
const alertText = document.getElementById('alert-text');

const statusColor = {
  normal:   '#3ecf8e',
  elevated: '#e8c04a',
  warning:  '#ff9a3d',
  critical: '#ff4f4f',
};

const statusMessage = {
  elevated: 'Coolant temperature is elevated. Keep an eye on it.',
  warning:  'Engine is overheating. Reduce load and check the cooling system.',
  critical: 'CRITICAL temperature. Shut down the engine to prevent damage.',
};

// ---- Chart.js setup ----------------------------------------------
const ctx = document.getElementById('tempChart').getContext('2d');
const tempChart = new Chart(ctx, {
  type: 'line',
  data: {
    labels: [],
    datasets: [
      {
        label: 'Coolant temp (°C)',
        data: [],
        borderColor: '#3ecf8e',
        backgroundColor: 'rgba(62, 207, 142, 0.08)',
        borderWidth: 2,
        pointRadius: 0,
        tension: 0.25,
        fill: true,
        segment: {
          borderColor: (context) => segmentColor(context),
        },
      },
      {
        label: `Warning (${window.THRESHOLDS.warning_max}°C)`,
        data: [],
        borderColor: 'rgba(255, 154, 61, 0.5)',
        borderWidth: 1,
        borderDash: [6, 4],
        pointRadius: 0,
        fill: false,
      },
      {
        label: `Critical (${window.THRESHOLDS.critical_max}°C)`,
        data: [],
        borderColor: 'rgba(255, 79, 79, 0.5)',
        borderWidth: 1,
        borderDash: [6, 4],
        pointRadius: 0,
        fill: false,
      },
    ],
  },
  options: {
    responsive: true,
    animation: false,
    interaction: { intersect: false, mode: 'index' },
    scales: {
      x: {
        ticks: { color: '#8b939c', maxTicksLimit: 8, font: { family: 'IBM Plex Mono', size: 10 } },
        grid: { color: 'rgba(255,255,255,0.04)' },
      },
      y: {
        min: 15,
        max: 140,
        ticks: { color: '#8b939c', font: { family: 'IBM Plex Mono', size: 10 } },
        grid: { color: 'rgba(255,255,255,0.04)' },
      },
    },
    plugins: {
      legend: {
        labels: { color: '#8b939c', font: { family: 'IBM Plex Mono', size: 11 }, boxWidth: 12 },
      },
      tooltip: {
        bodyFont: { family: 'IBM Plex Mono' },
        titleFont: { family: 'IBM Plex Mono' },
      },
    },
  },
});

function segmentColor(context) {
  const temp = context.p1.parsed.y;
  const t = window.THRESHOLDS;
  if (temp >= t.critical_max) return statusColor.critical;
  if (temp >= t.warning_max) return statusColor.warning;
  if (temp >= t.normal_max) return statusColor.elevated;
  return statusColor.normal;
}

// ---- polling loop --------------------------------------------------
async function pollLive() {
  try {
    const res = await fetch(`/api/live?n=${HISTORY_POINTS}`);
    const data = await res.json();
    updateChart(data.readings);
    updateLatest(data.readings);
  } catch (err) {
    console.error('live poll failed', err);
  }
}

async function pollSummary() {
  try {
    const res = await fetch('/api/summary');
    const s = await res.json();
    if (!s.count) return;
    document.getElementById('stat-avg').textContent = `${s.rolling_avg_temp_c}°C`;
    document.getElementById('stat-max').textContent = `${s.max_temp_c}°C`;
    document.getElementById('stat-min').textContent = `${s.min_temp_c}°C`;
    document.getElementById('stat-mean').textContent = `${s.mean_temp_c}°C`;
    document.getElementById('stat-overheat').textContent = `${s.overheat_seconds}s`;
    document.getElementById('stat-count').textContent = s.count;
  } catch (err) {
    console.error('summary poll failed', err);
  }
}

function updateChart(readings) {
  const labels = readings.map(r => new Date(r.timestamp * 1000).toLocaleTimeString());
  const temps = readings.map(r => r.coolant_temp_c);

  tempChart.data.labels = labels;
  tempChart.data.datasets[0].data = temps;
  tempChart.data.datasets[1].data = temps.map(() => window.THRESHOLDS.warning_max);
  tempChart.data.datasets[2].data = temps.map(() => window.THRESHOLDS.critical_max);
  tempChart.update('none');
}

function updateLatest(readings) {
  if (!readings.length) return;
  const latest = readings[readings.length - 1];

  document.getElementById('temp-value').textContent = latest.coolant_temp_c.toFixed(1);
  document.getElementById('rpm-value').textContent = latest.rpm.toLocaleString();
  document.getElementById('oil-value').textContent = latest.oil_pressure_psi.toFixed(1);
  document.getElementById('load-value').textContent = latest.load_pct.toFixed(0);

  document.getElementById('rpm-bar').style.width = `${Math.min(100, (latest.rpm / 7000) * 100)}%`;
  document.getElementById('oil-bar').style.width = `${Math.min(100, (latest.oil_pressure_psi / 60) * 100)}%`;
  document.getElementById('load-bar').style.width = `${latest.load_pct}%`;

  rig.dataset.status = latest.status;

  if (latest.status === 'normal') {
    alertRail.hidden = true;
  } else {
    alertRail.hidden = false;
    let msg = statusMessage[latest.status];
    if (latest.fault) {
      msg += ` (active fault: ${latest.fault.replaceAll('_', ' ')})`;
    }
    alertText.textContent = msg;
  }
}

// ---- fault control buttons -----------------------------------------
document.querySelectorAll('.control-buttons button').forEach(btn => {
  btn.addEventListener('click', async () => {
    const fault = btn.dataset.fault;
    const url = fault === 'clear' ? '/api/fault/clear' : `/api/fault/${fault}`;
    btn.disabled = true;
    try {
      const response = await fetch(url, { method: 'POST' });
      if (!response.ok) {
        throw new Error(`fault request failed (${response.status})`);
      }
      await Promise.all([pollLive(), pollSummary()]);
    } catch (err) {
      console.error('fault trigger failed', err);
    } finally {
      btn.disabled = false;
    }
  });
});

pollLive();
pollSummary();
setInterval(pollLive, POLL_MS);
setInterval(pollSummary, POLL_MS * 3);
