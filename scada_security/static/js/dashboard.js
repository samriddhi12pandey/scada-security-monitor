// ═══════════════════════════════════════════════════════════════
// SCADA Dashboard – Real-time Charts & Device Monitor
// ═══════════════════════════════════════════════════════════════

Chart.defaults.color = '#8892a4';
Chart.defaults.font.family = "'Share Tech Mono', monospace";
Chart.defaults.font.size = 10;

const CHART_OPTS = {
    responsive: true,
    maintainAspectRatio: false,
    animation: { duration: 400 },
    plugins: {
        legend: { display: false },
        tooltip: {
            backgroundColor: '#111827',
            borderColor: '#1e2d4a',
            borderWidth: 1,
            titleColor: '#e2e8f0',
            bodyColor: '#8892a4',
            padding: 10,
        }
    },
    scales: {
        x: {
            grid: { color: 'rgba(30,45,74,0.6)', drawBorder: false },
            ticks: { maxTicksLimit: 6 }
        },
        y: {
            grid: { color: 'rgba(30,45,74,0.6)', drawBorder: false },
            ticks: { maxTicksLimit: 5 }
        }
    }
};

function makeGradient(ctx, color1, color2) {
    const g = ctx.createLinearGradient(0, 0, 0, 200);
    g.addColorStop(0, color1);
    g.addColorStop(1, color2);
    return g;
}

// ─── Temperature Chart ────────────────────────────────────────
const tempCtx = document.getElementById('tempChart').getContext('2d');
const tempChart = new Chart(tempCtx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            data: [],
            borderColor: '#ef4444',
            backgroundColor: makeGradient(tempCtx, 'rgba(239,68,68,0.3)', 'rgba(239,68,68,0.01)'),
            fill: true,
            tension: 0.4,
            borderWidth: 2,
            pointRadius: 3,
            pointBackgroundColor: '#ef4444',
        }]
    },
    options: { ...CHART_OPTS }
});

// ─── Voltage Chart ────────────────────────────────────────────
const voltCtx = document.getElementById('voltChart').getContext('2d');
const voltChart = new Chart(voltCtx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [{
            data: [],
            borderColor: '#f59e0b',
            backgroundColor: makeGradient(voltCtx, 'rgba(245,158,11,0.3)', 'rgba(245,158,11,0.01)'),
            fill: true,
            tension: 0.4,
            borderWidth: 2,
            pointRadius: 3,
            pointBackgroundColor: '#f59e0b',
        }]
    },
    options: { ...CHART_OPTS }
});

// ─── Health Bar Chart ─────────────────────────────────────────
const healthCtx = document.getElementById('healthChart').getContext('2d');
const healthChart = new Chart(healthCtx, {
    type: 'bar',
    data: {
        labels: ['Turbine-1', 'Generator-1', 'Boiler-1', 'PLC-1', 'Transformer-1'],
        datasets: [
            {
                label: 'Temperature (°C)',
                data: [0,0,0,0,0],
                backgroundColor: 'rgba(239,68,68,0.7)',
                borderColor: '#ef4444',
                borderWidth: 1,
                borderRadius: 4,
            },
            {
                label: 'Voltage (V)',
                data: [0,0,0,0,0],
                backgroundColor: 'rgba(245,158,11,0.7)',
                borderColor: '#f59e0b',
                borderWidth: 1,
                borderRadius: 4,
            },
            {
                label: 'Current (A)',
                data: [0,0,0,0,0],
                backgroundColor: 'rgba(59,130,246,0.7)',
                borderColor: '#3b82f6',
                borderWidth: 1,
                borderRadius: 4,
            }
        ]
    },
    options: {
        ...CHART_OPTS,
        plugins: {
            ...CHART_OPTS.plugins,
            legend: {
                display: true,
                position: 'top',
                labels: { color: '#8892a4', boxWidth: 12, font: { size: 10 }, padding: 16 }
            }
        }
    }
});

// ─── Device Icon Map ─────────────────────────────────────────
const DEVICE_ICONS = {
    'Turbine':     'fa-fan',
    'Generator':   'fa-bolt',
    'Boiler':      'fa-fire-flame-curved',
    'PLC':         'fa-microchip',
    'Transformer': 'fa-plug-circle-bolt',
};

const DEVICE_COLORS = {
    'Turbine':     '#3b82f6',
    'Generator':   '#f59e0b',
    'Boiler':      '#ef4444',
    'PLC':         '#10b981',
    'Transformer': '#8b5cf6',
};

function barColor(pct) {
    if (pct > 85) return '#ef4444';
    if (pct > 65) return '#f59e0b';
    return '#10b981';
}

function renderDeviceCard(dev) {
    const icon  = DEVICE_ICONS[dev.device_type] || 'fa-server';
    const color = DEVICE_COLORS[dev.device_type] || '#3b82f6';
    const isOnline = dev.status === 'Online';
    const tempPct = Math.min((dev.temperature / 150) * 100, 100);
    const voltPct = Math.min((dev.voltage / 320) * 100, 100);
    const currPct = Math.min((dev.current / 160) * 100, 100);
    const updated = dev.recorded_at ? dev.recorded_at.slice(11,19) : '--';

    return `
    <div class="device-card">
        <div class="device-header">
            <div>
                <div class="device-name">${dev.device_name}</div>
                <div style="font-size:10px;color:var(--text-muted);">${dev.device_type}</div>
            </div>
            <div class="device-type-icon" style="background:${color}18;color:${color};">
                <i class="fas ${icon}"></i>
            </div>
        </div>

        <div class="device-status ${isOnline ? 'online' : 'offline'}">
            <span class="status-dot ${isOnline ? 'online' : 'offline'}"></span>
            ${dev.status}
        </div>

        ${isOnline ? `
        <div class="device-metrics">
            <div class="metric-row">
                <span class="metric-label"><i class="fas fa-temperature-half" style="color:#ef4444;"></i> Temp</span>
                <span class="metric-value">${dev.temperature}°C</span>
            </div>
            <div class="metric-bar"><div class="metric-bar-fill" style="width:${tempPct}%;background:${barColor(tempPct)};"></div></div>

            <div class="metric-row">
                <span class="metric-label"><i class="fas fa-bolt" style="color:#f59e0b;"></i> Volt</span>
                <span class="metric-value">${dev.voltage}V</span>
            </div>
            <div class="metric-bar"><div class="metric-bar-fill" style="width:${voltPct}%;background:${barColor(voltPct)};"></div></div>

            <div class="metric-row">
                <span class="metric-label"><i class="fas fa-wave-square" style="color:#3b82f6;"></i> Curr</span>
                <span class="metric-value">${dev.current}A</span>
            </div>
            <div class="metric-bar"><div class="metric-bar-fill" style="width:${currPct}%;background:${barColor(currPct)};"></div></div>
        </div>
        ` : `
        <div style="text-align:center;padding:16px;color:#fca5a5;font-size:12px;">
            <i class="fas fa-plug-circle-xmark fa-2x mb-2"></i><br>
            Device Offline<br>
            <span style="font-size:10px;color:var(--text-muted);">No sensor data available</span>
        </div>
        `}

        <div class="device-updated"><i class="fas fa-clock me-1"></i>Updated: ${updated}</div>
    </div>`;
}

// ─── Stats Counters ───────────────────────────────────────────
function animateValue(el, target) {
    const start = parseInt(el.textContent) || 0;
    const diff = target - start;
    if (diff === 0) return;
    const steps = 20;
    let step = 0;
    const timer = setInterval(() => {
        step++;
        el.textContent = Math.round(start + (diff * step / steps));
        if (step >= steps) clearInterval(timer);
    }, 20);
}

const THREAT_STYLES = {
    'Normal':   { text: '#86efac', bg: 'rgba(16,185,129,0.1)'  },
    'Guarded':  { text: '#67e8f9', bg: 'rgba(6,182,212,0.1)'   },
    'Elevated': { text: '#fde047', bg: 'rgba(245,158,11,0.1)'  },
    'High':     { text: '#fdba74', bg: 'rgba(249,115,22,0.12)' },
    'Critical': { text: '#fca5a5', bg: 'rgba(220,38,38,0.15)'  },
};

function updateStatCards(data) {
    animateValue(document.getElementById('statTotalVal'),   data.total_devices);
    animateValue(document.getElementById('statOnlineVal'),  data.online_devices);
    animateValue(document.getElementById('statOfflineVal'), data.offline_devices);
    animateValue(document.getElementById('statAlertsVal'),  data.active_alerts);

    const tl = data.threat_level || 'Normal';
    const tvEl = document.getElementById('statThreatVal');
    if (tvEl) {
        tvEl.textContent = tl.toUpperCase();
        const s = THREAT_STYLES[tl] || THREAT_STYLES['Normal'];
        tvEl.style.color = s.text;
    }

    // Card glow
    const alertCard = document.getElementById('statAlerts');
    if (alertCard && data.active_alerts > 0) {
        alertCard.style.boxShadow = '0 0 20px rgba(245,158,11,0.2)';
    }
}

// ─── Recent Alerts (Dashboard widget) ────────────────────────
function renderRecentAlerts(alerts) {
    const container = document.getElementById('recentAlerts');
    if (!container) return;
    const active = alerts.filter(a => !a.acknowledged).slice(0, 8);
    if (!active.length) {
        container.innerHTML = `<div class="loading-placeholder"><i class="fas fa-shield-check text-success me-2"></i>No active alerts — System secure</div>`;
        return;
    }
    container.innerHTML = active.map(a => `
        <div class="alert-item ${(a.severity||'low').toLowerCase()}">
            <div class="alert-sev-dot ${(a.severity||'low').toLowerCase()}"></div>
            <div class="alert-content">
                <div class="alert-title-row">
                    <span class="alert-type-text">${a.alert_type}</span>
                    <span class="alert-time">${a.created_at.slice(11,16)}</span>
                </div>
                <div class="alert-msg-text">${a.message}</div>
            </div>
        </div>
    `).join('');
}

// ─── Chart Updaters ───────────────────────────────────────────
async function fetchChartData(deviceId) {
    try {
        const res = await fetch(`/api/chart-data?device_id=${deviceId}`);
        return await res.json();
    } catch { return null; }
}

async function refreshTempChart() {
    const dev = document.getElementById('tempDeviceSelect').value;
    const d = await fetchChartData(dev);
    if (!d) return;
    tempChart.data.labels = d.labels;
    tempChart.data.datasets[0].data = d.temperature;
    tempChart.update('none');
}

async function refreshVoltChart() {
    const dev = document.getElementById('voltDeviceSelect').value;
    const d = await fetchChartData(dev);
    if (!d) return;
    voltChart.data.labels = d.labels;
    voltChart.data.datasets[0].data = d.voltage;
    voltChart.update('none');
}

function updateHealthChart(devices) {
    const order = ['turbine-1','generator-1','boiler-1','plc-1','transformer-1'];
    const byId = {};
    devices.forEach(d => { byId[d.device_id] = d; });
    healthChart.data.datasets[0].data = order.map(id => byId[id] ? byId[id].temperature : 0);
    healthChart.data.datasets[1].data = order.map(id => byId[id] ? byId[id].voltage     : 0);
    healthChart.data.datasets[2].data = order.map(id => byId[id] ? byId[id].current     : 0);
    healthChart.update('none');
}

// ─── Main Refresh Loop ────────────────────────────────────────
async function refreshDashboard() {
    try {
        const [statsRes, alertsRes] = await Promise.all([
            fetch('/api/dashboard-stats'),
            fetch('/api/alerts?limit=30'),
        ]);

        const stats  = await statsRes.json();
        const alerts = await alertsRes.json();

        updateStatCards(stats);
        updateHealthChart(stats.devices || []);
        renderRecentAlerts(alerts);

        const grid = document.getElementById('deviceGrid');
        if (grid && stats.devices) {
            grid.innerHTML = stats.devices.map(renderDeviceCard).join('');
        }

        const lastRefresh = document.getElementById('lastRefresh');
        if (lastRefresh) lastRefresh.textContent = 'Updated ' + new Date().toLocaleTimeString();

    } catch (e) { console.warn('Dashboard refresh error:', e); }
}

// ─── Attack Simulations ───────────────────────────────────────
async function simulate(type) {
    const resultEl = document.getElementById('simResult');
    if (resultEl) { resultEl.style.display = 'none'; }

    try {
        const res = await fetch(`/api/simulate/${type}`, { method: 'POST' });
        const data = await res.json();

        if (resultEl) {
            const msgs = {
                'high-temperature': `⚠ SIMULATED: Temperature spike on ${data.device} → ${data.temperature}°C`,
                'device-failure':   `⚠ SIMULATED: ${data.device} has been forced OFFLINE`,
                'voltage-spike':    `⚠ SIMULATED: Voltage surge on ${data.device} → ${data.voltage}V`,
                'brute-force':      `⚠ SIMULATED: Brute-force attack from ${data.ip}`,
                'network-scan':     `⚠ SIMULATED: Port scan detected from ${data.ip}`,
            };
            resultEl.textContent = msgs[type] || '⚠ Simulation executed';
            resultEl.className = 'sim-result success';
            resultEl.style.display = 'block';
            setTimeout(() => { resultEl.style.display = 'none'; }, 6000);
        }

        // Immediate refresh
        setTimeout(refreshDashboard, 800);
    } catch (e) {
        if (resultEl) {
            resultEl.textContent = '✕ Simulation failed: ' + e.message;
            resultEl.className = 'sim-result error';
            resultEl.style.display = 'block';
        }
    }
}

// ─── Chart Device Selectors ───────────────────────────────────
document.getElementById('tempDeviceSelect').addEventListener('change', refreshTempChart);
document.getElementById('voltDeviceSelect').addEventListener('change', refreshVoltChart);

// ─── Init ─────────────────────────────────────────────────────
refreshDashboard();
refreshTempChart();
refreshVoltChart();

setInterval(refreshDashboard, 5000);
setInterval(refreshTempChart, 7000);
setInterval(refreshVoltChart, 7000);
