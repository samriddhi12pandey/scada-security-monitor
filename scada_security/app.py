"""
SCADA Security Monitoring System - Main Application
Thermal Power Plant Cybersecurity Operations Center
"""

import os
import sqlite3
import hashlib
import json
import threading
import time
import random
import datetime
import io
from functools import wraps
from flask import (Flask, render_template, request, redirect, url_for,
                   session, jsonify, flash, send_file, g)
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.units import inch

# ─── App Setup ───────────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = os.urandom(32)
DATABASE = os.path.join(os.path.dirname(__file__), 'scada.db')

# ─── Threat Thresholds ────────────────────────────────────────────────────────
THRESHOLDS = {
    'temperature': {'low': 60, 'medium': 80, 'high': 100, 'critical': 120},
    'voltage':     {'low': 240, 'medium': 260, 'high': 280, 'critical': 300},
    'current':     {'low': 80,  'medium': 100, 'high': 120, 'critical': 140},
}

DEVICES = [
    {'id': 'turbine-1',     'name': 'Turbine-1',     'type': 'Turbine'},
    {'id': 'generator-1',   'name': 'Generator-1',   'type': 'Generator'},
    {'id': 'boiler-1',      'name': 'Boiler-1',      'type': 'Boiler'},
    {'id': 'plc-1',         'name': 'PLC-1',         'type': 'PLC'},
    {'id': 'transformer-1', 'name': 'Transformer-1', 'type': 'Transformer'},
]

# IP brute-force tracking (in-memory)
login_attempts = {}  # ip -> {'count': int, 'last': float}
request_counts = {}  # ip -> {'count': int, 'window_start': float}

# ─── Database ─────────────────────────────────────────────────────────────────

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_db(exc):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

def query_db(query, args=(), one=False, commit=False):
    """Thread-safe DB query"""
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(query, args)
        if commit:
            conn.commit()
            return cur.lastrowid
        rv = cur.fetchall()
        return (rv[0] if rv else None) if one else rv
    finally:
        conn.close()

def init_db():
    conn = sqlite3.connect(DATABASE)
    c = conn.cursor()

    c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'operator',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS device_readings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT NOT NULL,
            device_name TEXT NOT NULL,
            device_type TEXT NOT NULL,
            temperature REAL,
            voltage REAL,
            current REAL,
            status TEXT DEFAULT 'Online',
            recorded_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            device_id TEXT,
            device_name TEXT,
            alert_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            message TEXT NOT NULL,
            acknowledged INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user TEXT,
            action TEXT NOT NULL,
            details TEXT,
            ip_address TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS security_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            username TEXT,
            ip_address TEXT,
            details TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Seed admin user
    admin_hash = hashlib.sha256('admin123'.encode()).hexdigest()
    op_hash = hashlib.sha256('operator123'.encode()).hexdigest()
    try:
        c.execute("INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                  ('admin', admin_hash, 'admin'))
        c.execute("INSERT OR IGNORE INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                  ('operator', op_hash, 'operator'))
    except Exception:
        pass

    conn.commit()
    conn.close()

# ─── Auth Helpers ─────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if session.get('role') != 'admin':
            flash('Admin access required.', 'danger')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated

def hash_password(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def log_audit(user, action, details='', ip=''):
    query_db("INSERT INTO audit_logs (user, action, details, ip_address) VALUES (?,?,?,?)",
             (user, action, details, ip), commit=True)

def log_security(event_type, username='', ip='', details=''):
    query_db("INSERT INTO security_logs (event_type, username, ip_address, details) VALUES (?,?,?,?)",
             (event_type, username, ip, details), commit=True)

def create_alert(device_id, device_name, alert_type, severity, message):
    query_db("INSERT INTO alerts (device_id, device_name, alert_type, severity, message) VALUES (?,?,?,?,?)",
             (device_id, device_name, alert_type, severity, message), commit=True)
    log_audit('SYSTEM', 'Alert Generated', f'{severity} alert: {message}')

# ─── Simulator ────────────────────────────────────────────────────────────────

def get_normal_reading(device_type):
    base = {
        'Turbine':     {'temp': (55, 75),  'volt': (220, 240), 'curr': (60, 80)},
        'Generator':   {'temp': (50, 70),  'volt': (225, 245), 'curr': (65, 85)},
        'Boiler':      {'temp': (70, 90),  'volt': (210, 230), 'curr': (55, 75)},
        'PLC':         {'temp': (30, 45),  'volt': (215, 235), 'curr': (40, 60)},
        'Transformer': {'temp': (45, 65),  'volt': (230, 250), 'curr': (70, 90)},
    }
    r = base.get(device_type, {'temp': (50, 70), 'volt': (220, 240), 'curr': (60, 80)})
    return (
        round(random.uniform(*r['temp']), 2),
        round(random.uniform(*r['volt']), 2),
        round(random.uniform(*r['curr']), 2),
    )

def check_thresholds(device_id, device_name, temp, volt, curr, status):
    if status == 'Offline':
        create_alert(device_id, device_name, 'Device Offline', 'Critical',
                     f'{device_name} is OFFLINE – immediate inspection required.')
        return

    def sev(val, thresholds):
        if val >= thresholds['critical']: return 'Critical'
        if val >= thresholds['high']:     return 'High'
        if val >= thresholds['medium']:   return 'Medium'
        if val >= thresholds['low']:      return 'Low'
        return None

    ts = sev(temp, THRESHOLDS['temperature'])
    vs = sev(volt, THRESHOLDS['voltage'])
    cs = sev(curr, THRESHOLDS['current'])

    if ts:
        create_alert(device_id, device_name, 'High Temperature', ts,
                     f'{device_name} temperature critical: {temp}°C (threshold: {THRESHOLDS["temperature"]["low"]}°C)')
    if vs:
        create_alert(device_id, device_name, 'Voltage Anomaly', vs,
                     f'{device_name} voltage anomaly: {volt}V (threshold: {THRESHOLDS["voltage"]["low"]}V)')
    if cs:
        create_alert(device_id, device_name, 'Current Overload', cs,
                     f'{device_name} current overload: {curr}A (threshold: {THRESHOLDS["current"]["low"]}A)')

simulator_running = False

def simulator_loop():
    global simulator_running
    while simulator_running:
        for dev in DEVICES:
            temp, volt, curr = get_normal_reading(dev['type'])
            status = 'Online' if random.random() > 0.02 else 'Offline'
            query_db(
                "INSERT INTO device_readings (device_id, device_name, device_type, temperature, voltage, current, status) VALUES (?,?,?,?,?,?,?)",
                (dev['id'], dev['name'], dev['type'], temp, volt, curr, status),
                commit=True
            )
            # Only generate alerts occasionally (every ~20th reading)
            if random.random() < 0.05:
                check_thresholds(dev['id'], dev['name'], temp, volt, curr, status)

        # Keep DB small
        query_db("DELETE FROM device_readings WHERE id NOT IN (SELECT id FROM device_readings ORDER BY id DESC LIMIT 5000)",
                 commit=True)
        time.sleep(5)

def start_simulator():
    global simulator_running
    if not simulator_running:
        simulator_running = True
        t = threading.Thread(target=simulator_loop, daemon=True)
        t.start()

# ─── Rate Limiting ────────────────────────────────────────────────────────────

def check_rate_limit(ip):
    now = time.time()
    if ip not in request_counts:
        request_counts[ip] = {'count': 1, 'window_start': now}
        return False
    rc = request_counts[ip]
    if now - rc['window_start'] > 60:
        request_counts[ip] = {'count': 1, 'window_start': now}
        return False
    rc['count'] += 1
    if rc['count'] > 100:
        create_alert(None, 'Network', 'Suspicious Network Activity', 'High',
                     f'Excessive requests from IP {ip}: {rc["count"]} requests/min')
        log_security('Rate Limit Exceeded', ip=ip, details=f'{rc["count"]} req/min')
        return True
    return False

# ─── Routes ───────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    return redirect(url_for('dashboard') if 'user_id' in session else url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    ip = request.remote_addr
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        # Brute-force detection
        if ip not in login_attempts:
            login_attempts[ip] = {'count': 0, 'last': time.time()}
        la = login_attempts[ip]
        if time.time() - la['last'] > 300:
            la['count'] = 0
        la['last'] = time.time()

        user = query_db("SELECT * FROM users WHERE username=?", (username,), one=True)
        if user and user['password_hash'] == hash_password(password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            login_attempts[ip] = {'count': 0, 'last': time.time()}
            log_audit(username, 'User Login', f'Successful login', ip)
            log_security('Successful Login', username, ip, 'Login OK')
            return redirect(url_for('dashboard'))
        else:
            la['count'] += 1
            log_security('Failed Login', username, ip, f'Attempt #{la["count"]}')
            log_audit(username, 'Failed Login', f'Bad credentials, attempt #{la["count"]}', ip)
            if la['count'] >= 5:
                create_alert(None, 'Auth System', 'Brute Force Attack', 'Critical',
                             f'Multiple failed logins from IP {ip} ({la["count"]} attempts) for user "{username}"')
            flash(f'Invalid credentials. Attempt #{la["count"]}.', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    log_audit(session.get('username'), 'User Logout', 'Session ended', request.remote_addr)
    session.clear()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html', username=session.get('username'), role=session.get('role'))

@app.route('/alerts')
@login_required
def alerts_page():
    return render_template('alerts.html', username=session.get('username'), role=session.get('role'))

@app.route('/audit')
@login_required
def audit_page():
    return render_template('audit.html', username=session.get('username'), role=session.get('role'))

@app.route('/reports')
@login_required
def reports_page():
    return render_template('reports.html', username=session.get('username'), role=session.get('role'))

@app.route('/users')
@admin_required
def users_page():
    users = query_db("SELECT id, username, role, created_at FROM users")
    return render_template('users.html', users=users, username=session.get('username'), role=session.get('role'))

# ─── API Endpoints ────────────────────────────────────────────────────────────

@app.route('/api/dashboard-stats')
@login_required
def api_dashboard_stats():
    check_rate_limit(request.remote_addr)

    # Latest reading per device
    latest = query_db("""
        SELECT dr.* FROM device_readings dr
        INNER JOIN (
            SELECT device_id, MAX(id) as max_id FROM device_readings GROUP BY device_id
        ) t ON dr.device_id = t.device_id AND dr.id = t.max_id
    """)

    total = len(latest)
    online = sum(1 for r in latest if r['status'] == 'Online')
    offline = total - online

    active_alerts = query_db("SELECT COUNT(*) as c FROM alerts WHERE acknowledged=0", one=True)['c']
    critical_alerts = query_db("SELECT COUNT(*) as c FROM alerts WHERE acknowledged=0 AND severity='Critical'", one=True)['c']

    threat_level = 'Normal'
    if critical_alerts > 0: threat_level = 'Critical'
    elif active_alerts > 10: threat_level = 'High'
    elif active_alerts > 5:  threat_level = 'Elevated'
    elif active_alerts > 0:  threat_level = 'Guarded'

    devices_data = []
    for r in latest:
        devices_data.append({
            'device_id': r['device_id'],
            'device_name': r['device_name'],
            'device_type': r['device_type'],
            'temperature': r['temperature'],
            'voltage': r['voltage'],
            'current': r['current'],
            'status': r['status'],
            'recorded_at': r['recorded_at'],
        })

    return jsonify({
        'total_devices': total,
        'online_devices': online,
        'offline_devices': offline,
        'active_alerts': active_alerts,
        'threat_level': threat_level,
        'devices': devices_data,
    })

@app.route('/api/chart-data')
@login_required
def api_chart_data():
    device_id = request.args.get('device_id', 'turbine-1')
    rows = query_db("""
        SELECT temperature, voltage, current, recorded_at
        FROM device_readings WHERE device_id=?
        ORDER BY id DESC LIMIT 20
    """, (device_id,))
    rows = list(reversed(rows))
    return jsonify({
        'labels': [r['recorded_at'][-8:] for r in rows],
        'temperature': [r['temperature'] for r in rows],
        'voltage': [r['voltage'] for r in rows],
        'current': [r['current'] for r in rows],
    })

@app.route('/api/alerts')
@login_required
def api_alerts():
    limit = int(request.args.get('limit', 50))
    rows = query_db("SELECT * FROM alerts ORDER BY id DESC LIMIT ?", (limit,))
    return jsonify([dict(r) for r in rows])

@app.route('/api/alerts/acknowledge/<int:alert_id>', methods=['POST'])
@login_required
def ack_alert(alert_id):
    query_db("UPDATE alerts SET acknowledged=1 WHERE id=?", (alert_id,), commit=True)
    log_audit(session['username'], 'Alert Acknowledged', f'Alert ID {alert_id}', request.remote_addr)
    return jsonify({'success': True})

@app.route('/api/alerts/acknowledge-all', methods=['POST'])
@login_required
def ack_all_alerts():
    query_db("UPDATE alerts SET acknowledged=1 WHERE acknowledged=0", commit=True)
    log_audit(session['username'], 'All Alerts Acknowledged', '', request.remote_addr)
    return jsonify({'success': True})

@app.route('/api/audit-logs')
@login_required
def api_audit_logs():
    rows = query_db("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 100")
    return jsonify([dict(r) for r in rows])

@app.route('/api/security-logs')
@login_required
def api_security_logs():
    rows = query_db("SELECT * FROM security_logs ORDER BY id DESC LIMIT 100")
    return jsonify([dict(r) for r in rows])

# ─── Attack Simulations ───────────────────────────────────────────────────────

@app.route('/api/simulate/high-temperature', methods=['POST'])
@login_required
def sim_high_temp():
    dev = random.choice(DEVICES)
    temp = round(random.uniform(115, 145), 2)
    volt = round(random.uniform(225, 245), 2)
    curr = round(random.uniform(65, 85), 2)
    query_db(
        "INSERT INTO device_readings (device_id, device_name, device_type, temperature, voltage, current, status) VALUES (?,?,?,?,?,?,?)",
        (dev['id'], dev['name'], dev['type'], temp, volt, curr, 'Online'), commit=True
    )
    create_alert(dev['id'], dev['name'], 'High Temperature Attack', 'Critical',
                 f'SIMULATED: {dev["name"]} temperature spike to {temp}°C – possible thermal attack or cooling failure')
    log_audit(session['username'], 'Attack Simulation', f'High Temperature on {dev["name"]}', request.remote_addr)
    return jsonify({'success': True, 'device': dev['name'], 'temperature': temp})

@app.route('/api/simulate/device-failure', methods=['POST'])
@login_required
def sim_device_failure():
    dev = random.choice(DEVICES)
    query_db(
        "INSERT INTO device_readings (device_id, device_name, device_type, temperature, voltage, current, status) VALUES (?,?,?,?,?,?,?)",
        (dev['id'], dev['name'], dev['type'], 0, 0, 0, 'Offline'), commit=True
    )
    create_alert(dev['id'], dev['name'], 'Device Failure', 'Critical',
                 f'SIMULATED: {dev["name"]} has gone OFFLINE – complete device failure detected')
    log_audit(session['username'], 'Attack Simulation', f'Device Failure on {dev["name"]}', request.remote_addr)
    return jsonify({'success': True, 'device': dev['name']})

@app.route('/api/simulate/voltage-spike', methods=['POST'])
@login_required
def sim_voltage_spike():
    dev = random.choice(DEVICES)
    volt = round(random.uniform(295, 350), 2)
    temp = round(random.uniform(55, 75), 2)
    curr = round(random.uniform(130, 160), 2)
    query_db(
        "INSERT INTO device_readings (device_id, device_name, device_type, temperature, voltage, current, status) VALUES (?,?,?,?,?,?,?)",
        (dev['id'], dev['name'], dev['type'], temp, volt, curr, 'Online'), commit=True
    )
    create_alert(dev['id'], dev['name'], 'Voltage Spike', 'Critical',
                 f'SIMULATED: {dev["name"]} voltage spike to {volt}V – possible power surge or cyber manipulation')
    log_audit(session['username'], 'Attack Simulation', f'Voltage Spike on {dev["name"]}', request.remote_addr)
    return jsonify({'success': True, 'device': dev['name'], 'voltage': volt})

@app.route('/api/simulate/brute-force', methods=['POST'])
@login_required
def sim_brute_force():
    fake_ip = f'192.168.{random.randint(1,254)}.{random.randint(1,254)}'
    for i in range(7):
        log_security('Failed Login', 'root', fake_ip, f'Brute force attempt #{i+1}')
    create_alert(None, 'Auth System', 'Brute Force Attack', 'Critical',
                 f'SIMULATED: Brute-force login attack detected from IP {fake_ip} – 7 failed attempts in 30 seconds')
    log_audit(session['username'], 'Attack Simulation', f'Brute Force from {fake_ip}', request.remote_addr)
    return jsonify({'success': True, 'ip': fake_ip})

@app.route('/api/simulate/network-scan', methods=['POST'])
@login_required
def sim_network_scan():
    fake_ip = f'10.{random.randint(1,254)}.{random.randint(1,254)}.{random.randint(1,254)}'
    create_alert(None, 'Network', 'Suspicious Network Activity', 'High',
                 f'SIMULATED: Port scan detected from external IP {fake_ip} – possible reconnaissance attack on SCADA network')
    log_security('Network Scan Detected', ip=fake_ip, details='Port scan on SCADA network – 1024 ports probed')
    log_audit(session['username'], 'Attack Simulation', f'Network Scan from {fake_ip}', request.remote_addr)
    return jsonify({'success': True, 'ip': fake_ip})

# ─── PDF Reports ──────────────────────────────────────────────────────────────

def make_pdf_header(elements, title, subtitle, styles):
    elements.append(Paragraph(f'🔒 SCADA SECURITY MONITORING SYSTEM', styles['Title']))
    elements.append(Paragraph(f'Thermal Power Plant – Cybersecurity Operations Center', styles['Normal']))
    elements.append(Spacer(1, 6))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#e53e3e')))
    elements.append(Spacer(1, 6))
    elements.append(Paragraph(title, styles['Heading1']))
    elements.append(Paragraph(subtitle, styles['Normal']))
    elements.append(Spacer(1, 12))

def build_pdf(title, subtitle, table_data, table_headers, col_widths=None):
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, topMargin=0.5*inch, bottomMargin=0.5*inch,
                            leftMargin=0.5*inch, rightMargin=0.5*inch)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='SmallCell', fontSize=7, leading=9))
    elements = []
    make_pdf_header(elements, title, subtitle, styles)

    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    elements.append(Paragraph(f'Generated: {now}  |  Classification: CONFIDENTIAL', styles['Normal']))
    elements.append(Spacer(1, 12))

    data = [table_headers] + table_data
    cw = col_widths or [1.2*inch] * len(table_headers)
    t = Table(data, colWidths=cw, repeatRows=1)
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1a202c')),
        ('TEXTCOLOR',  (0,0), (-1,0), colors.white),
        ('FONTNAME',   (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE',   (0,0), (-1,0), 8),
        ('FONTSIZE',   (0,1), (-1,-1), 7),
        ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.HexColor('#f7fafc'), colors.white]),
        ('GRID',       (0,0), (-1,-1), 0.5, colors.HexColor('#cbd5e0')),
        ('VALIGN',     (0,0), (-1,-1), 'MIDDLE'),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 20))
    elements.append(Paragraph('END OF REPORT – CONFIDENTIAL', styles['Normal']))
    doc.build(elements)
    buf.seek(0)
    return buf

@app.route('/api/report/device-health')
@login_required
def report_device_health():
    rows = query_db("""
        SELECT dr.* FROM device_readings dr
        INNER JOIN (SELECT device_id, MAX(id) as mx FROM device_readings GROUP BY device_id) t
        ON dr.device_id=t.device_id AND dr.id=t.mx
    """)
    data = [[r['device_name'], r['device_type'], f"{r['temperature']}°C",
             f"{r['voltage']}V", f"{r['current']}A", r['status'], r['recorded_at'][:16]]
            for r in rows]
    headers = ['Device', 'Type', 'Temperature', 'Voltage', 'Current', 'Status', 'Last Updated']
    widths = [1.2*inch, 1.0*inch, 0.9*inch, 0.8*inch, 0.8*inch, 0.8*inch, 1.3*inch]
    buf = build_pdf('Daily Device Health Report',
                    f'Operational status of all monitored industrial devices – {datetime.date.today()}',
                    data, headers, widths)
    log_audit(session['username'], 'Report Download', 'Device Health Report', request.remote_addr)
    return send_file(buf, mimetype='application/pdf', as_attachment=True,
                     download_name='device_health_report.pdf')

@app.route('/api/report/security-incidents')
@login_required
def report_security_incidents():
    rows = query_db("SELECT * FROM alerts WHERE severity IN ('High','Critical') ORDER BY id DESC LIMIT 100")
    data = [[r['device_name'] or 'N/A', r['alert_type'], r['severity'],
             r['message'][:60], r['created_at'][:16]] for r in rows]
    headers = ['Device', 'Alert Type', 'Severity', 'Message', 'Timestamp']
    widths = [1.0*inch, 1.2*inch, 0.8*inch, 2.8*inch, 1.2*inch]
    buf = build_pdf('Security Incident Report',
                    'High and Critical severity security incidents – last 100 records',
                    data, headers, widths)
    log_audit(session['username'], 'Report Download', 'Security Incident Report', request.remote_addr)
    return send_file(buf, mimetype='application/pdf', as_attachment=True,
                     download_name='security_incident_report.pdf')

@app.route('/api/report/alert-summary')
@login_required
def report_alert_summary():
    rows = query_db("SELECT * FROM alerts ORDER BY id DESC LIMIT 200")
    data = [[r['device_name'] or 'System', r['alert_type'], r['severity'],
             'Yes' if r['acknowledged'] else 'No', r['created_at'][:16]] for r in rows]
    headers = ['Device', 'Alert Type', 'Severity', 'Acknowledged', 'Timestamp']
    widths = [1.1*inch, 1.4*inch, 0.8*inch, 1.0*inch, 1.3*inch]
    buf = build_pdf('Alert Summary Report', 'All alerts – last 200 records', data, headers, widths)
    log_audit(session['username'], 'Report Download', 'Alert Summary Report', request.remote_addr)
    return send_file(buf, mimetype='application/pdf', as_attachment=True,
                     download_name='alert_summary_report.pdf')

@app.route('/api/report/system-activity')
@login_required
def report_system_activity():
    rows = query_db("SELECT * FROM audit_logs ORDER BY id DESC LIMIT 200")
    data = [[r['user'] or 'SYSTEM', r['action'], r['details'][:50] if r['details'] else '',
             r['ip_address'] or '', r['created_at'][:16]] for r in rows]
    headers = ['User', 'Action', 'Details', 'IP Address', 'Timestamp']
    widths = [0.9*inch, 1.3*inch, 2.2*inch, 1.0*inch, 1.2*inch]
    buf = build_pdf('System Activity Report', 'Audit log – last 200 actions', data, headers, widths)
    log_audit(session['username'], 'Report Download', 'System Activity Report', request.remote_addr)
    return send_file(buf, mimetype='application/pdf', as_attachment=True,
                     download_name='system_activity_report.pdf')

# ─── User Management ──────────────────────────────────────────────────────────

@app.route('/api/users/add', methods=['POST'])
@admin_required
def add_user():
    data = request.get_json()
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()
    role = data.get('role', 'operator')
    if not username or not password:
        return jsonify({'success': False, 'error': 'Username and password required'})
    try:
        query_db("INSERT INTO users (username, password_hash, role) VALUES (?,?,?)",
                 (username, hash_password(password), role), commit=True)
        log_audit(session['username'], 'User Created', f'Created user: {username} ({role})', request.remote_addr)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/users/delete/<int:uid>', methods=['POST'])
@admin_required
def delete_user(uid):
    user = query_db("SELECT username FROM users WHERE id=?", (uid,), one=True)
    if user and user['username'] != 'admin':
        query_db("DELETE FROM users WHERE id=?", (uid,), commit=True)
        log_audit(session['username'], 'User Deleted', f'Deleted user: {user["username"]}', request.remote_addr)
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Cannot delete admin or user not found'})

# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    init_db()
    start_simulator()
    app.run(debug=False, host='0.0.0.0', port=5000)
