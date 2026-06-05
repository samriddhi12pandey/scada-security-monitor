// ─── System Clock ─────────────────────────────────────────────
function updateSystemTime() {
    const el = document.getElementById('systemTime');
    if (el) el.textContent = new Date().toLocaleTimeString('en-US', { hour12: false });
}
setInterval(updateSystemTime, 1000);
updateSystemTime();

// ─── Sidebar alert count + Threat badge ───────────────────────
async function updateNavStats() {
    try {
        const res = await fetch('/api/dashboard-stats');
        if (!res.ok) return;
        const data = await res.json();

        // Sidebar alert badge
        const badge = document.getElementById('sidebarAlertCount');
        if (badge) {
            badge.textContent = data.active_alerts;
            badge.style.display = data.active_alerts > 0 ? 'inline-block' : 'none';
        }

        // Nav threat badge
        const tl = data.threat_level || 'Normal';
        const navTL = document.getElementById('navThreatLevel');
        const navBadge = document.getElementById('navThreatBadge');
        if (navTL) navTL.textContent = tl.toUpperCase();

        if (navBadge) {
            navBadge.className = 'threat-badge';
            const colorMap = {
                'Normal':   'rgba(16,185,129,0.1)',
                'Guarded':  'rgba(6,182,212,0.1)',
                'Elevated': 'rgba(245,158,11,0.1)',
                'High':     'rgba(249,115,22,0.12)',
                'Critical': 'rgba(220,38,38,0.15)',
            };
            const borderMap = {
                'Normal':   'rgba(16,185,129,0.3)',
                'Guarded':  'rgba(6,182,212,0.3)',
                'Elevated': 'rgba(245,158,11,0.3)',
                'High':     'rgba(249,115,22,0.4)',
                'Critical': 'rgba(220,38,38,0.5)',
            };
            const textMap = {
                'Normal':   '#86efac',
                'Guarded':  '#67e8f9',
                'Elevated': '#fde047',
                'High':     '#fdba74',
                'Critical': '#fca5a5',
            };
            navBadge.style.background   = colorMap[tl] || colorMap['Normal'];
            navBadge.style.borderColor  = borderMap[tl] || borderMap['Normal'];
            navBadge.style.color        = textMap[tl] || textMap['Normal'];
        }
    } catch (e) {}
}

setInterval(updateNavStats, 8000);
updateNavStats();
