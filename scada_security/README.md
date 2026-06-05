# SCADA Security Monitoring System
### Thermal Power Plant – Cybersecurity Operations Center

A full-stack industrial cybersecurity monitoring platform simulating a real-world ICS/SCADA security operations center for power plants.

---

## 🚀 Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Run the Application
```bash
python app.py
```

### 3. Open in Browser
```
http://localhost:5000
```

### 4. Default Credentials
| Role     | Username   | Password      |
|----------|------------|---------------|
| Admin    | admin      | admin123      |
| Operator | operator   | operator123   |

---

## 🏗️ Project Structure

```
scada_security/
├── app.py                  # Main Flask application
├── requirements.txt        # Python dependencies
├── scada.db               # SQLite database (auto-created)
├── static/
│   ├── css/
│   │   └── style.css      # Industrial dark theme CSS
│   └── js/
│       ├── base.js        # Shared nav/clock JS
│       └── dashboard.js   # Charts, device cards, simulations
└── templates/
    ├── base.html          # Base layout with sidebar/nav
    ├── login.html         # Animated login page
    ├── dashboard.html     # Main monitoring dashboard
    ├── alerts.html        # Alert management
    ├── audit.html         # Audit & security logs
    ├── reports.html       # PDF report generation
    └── users.html         # User management (admin only)
```

---

## 🔧 Core Features

### Device Monitoring
- **5 Industrial Devices**: Turbine-1, Generator-1, Boiler-1, PLC-1, Transformer-1
- Real-time Temperature, Voltage, Current readings
- Live Online/Offline status with visual indicators
- Color-coded metric bars (Green → Yellow → Red)

### Real-Time Dashboard
- Animated stats cards (Total/Online/Offline devices, Active Alerts, Threat Level)
- Live temperature trend chart (per device)
- Live voltage trend chart (per device)
- Device health overview bar chart
- 5-second auto-refresh cycle

### Threat Detection Engine
Generates alerts when:
- Temperature exceeds 60/80/100/120°C (Low/Medium/High/Critical)
- Voltage exceeds 240/260/280/300V
- Current exceeds 80/100/120/140A
- Device goes offline
- Multiple failed logins (brute-force)
- Excessive requests from same IP (rate limiting)

### Attack Simulation Panel
| Simulation | Severity | Description |
|------------|----------|-------------|
| High Temperature | Critical | Thermal attack / cooling failure |
| Device Failure | Critical | Forced device offline |
| Voltage Spike | Critical | Power surge / cyber manipulation |
| Brute Force | Critical | Simulated login attack |
| Network Scan | High | Port scan / reconnaissance |

### PDF Reports
- **Device Health Report** – Current status of all industrial devices
- **Security Incident Report** – High/Critical severity events
- **Alert Summary Report** – All alerts with acknowledgment status
- **System Activity Report** – Full audit trail

### Cybersecurity Monitoring
- Track successful/failed logins with IP addresses
- Brute-force detection (5+ failed attempts = Critical alert)
- Rate limiting (>100 req/min = High alert)
- Complete security event log

### Audit Logging
All actions recorded: Login, Logout, Alert Generated, Simulations, Report Downloads, Config Changes

### User Management (Admin)
- Add/delete operator accounts
- Role-based access (Admin vs Operator)
- Admin-only: User management panel

---

## 🛢️ Database Schema

| Table | Purpose |
|-------|---------|
| `users` | Authentication & roles |
| `device_readings` | Sensor data from all devices |
| `alerts` | Security/operational alerts |
| `audit_logs` | All user/system actions |
| `security_logs` | Login attempts & threat events |

---

## 🔒 Security Features
- SHA-256 password hashing
- Server-side session management
- Role-based access control
- IP-based brute-force detection
- Rate limiting per IP
- Complete audit trail

---

## 🎨 UI Design
- Industrial control room dark theme
- Monospace + Exo 2 typography
- Animated scanline effect
- Real-time Chart.js visualizations
- CRT-style color palette
- Responsive Bootstrap 5 grid

---

*Built for educational demonstration of ICS/SCADA cybersecurity monitoring concepts.*
