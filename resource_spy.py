#!/usr/bin/env python3
import os
import json
import time
import argparse
from datetime import datetime, timedelta
import psutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
METRICS_FILE = os.path.join(SCRIPT_DIR, "metrics.json")
REPORT_FILE = os.path.join(SCRIPT_DIR, "report.html")

def get_metrics():
    """Captures system metrics using psutil."""
    cpu_percent = psutil.cpu_percent(interval=1)
    load_avg = os.getloadavg()[0]  # 1-minute load average
    
    mem = psutil.virtual_memory()
    net = psutil.net_io_counters()
    disk_usage = psutil.disk_usage('/')
    
    # I/O wait is a CPU metric, but we'll include it as requested
    cpu_times = psutil.cpu_times_percent(interval=None)
    io_wait = getattr(cpu_times, 'iowait', 0.0)

    return {
        "timestamp": datetime.now().isoformat(),
        "cpu_percent": cpu_percent,
        "load_avg": load_avg,
        "ram_total": mem.total,
        "ram_used": mem.used,
        "ram_available": mem.available,
        "net_sent": net.bytes_sent,
        "net_recv": net.bytes_recv,
        "disk_io_wait": io_wait,
        "disk_free": disk_usage.free
    }

def save_metrics(new_data):
    """Saves metrics to JSON and prunes data older than 24 hours."""
    data = []
    if os.path.exists(METRICS_FILE):
        try:
            with open(METRICS_FILE, 'r') as f:
                data = json.load(f)
        except (json.JSONDecodeError, IOError):
            data = []

    data.append(new_data)
    
    # Retention: Keep last 24 hours
    cutoff = datetime.now() - timedelta(hours=24)
    data = [entry for entry in data if datetime.fromisoformat(entry['timestamp']) > cutoff]
    
    with open(METRICS_FILE, 'w') as f:
        json.dump(data, f, indent=2)
    
    return data

def check_alerts(data):
    """Triggers an alert if CPU > 90% for the last 3 consecutive checks."""
    if len(data) < 3:
        return

    last_three = data[-3:]
    if all(entry['cpu_percent'] > 90 for entry in last_three):
        print("\n[!] ALERT: CPU usage has been above 90% for the last 3 checks!")
        # Optional: Add Webhook call here
        # requests.post(WEBHOOK_URL, json={"text": "CPU Alert!"})

def generate_report(data):
    """Generates a standalone dark-mode HTML dashboard using Chart.js."""
    if not data:
        print("No data available to generate report.")
        return

    # Prepare data for Chart.js
    labels = [datetime.fromisoformat(d['timestamp']).strftime('%H:%M') for d in data]
    cpu_data = [d['cpu_percent'] for d in data]
    ram_data = [(d['ram_used'] / d['ram_total']) * 100 for d in data]
    
    # Calculate Network Throughput (diff between consecutive points)
    net_sent_rates = [0]
    net_recv_rates = [0]
    for i in range(1, len(data)):
        # Bytes since last check (simple delta)
        sent_delta = max(0, data[i]['net_sent'] - data[i-1]['net_sent'])
        recv_delta = max(0, data[i]['net_recv'] - data[i-1]['net_recv'])
        net_sent_rates.append(sent_delta / 1024 / 1024) # MB
        net_recv_rates.append(recv_delta / 1024 / 1024) # MB

    html_template = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ResourceSpy Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            background-color: #0f172a;
            color: #f8fafc;
            font-family: 'Inter', system-ui, -apple-system, sans-serif;
            margin: 0;
            padding: 2rem;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; }}
        header {{ margin-bottom: 2rem; border-bottom: 1px solid #334155; padding-bottom: 1rem; }}
        h1 {{ font-size: 1.5rem; margin: 0; color: #38bdf8; }}
        .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; }}
        .card {{
            background: #1e293b;
            padding: 1.5rem;
            border-radius: 0.75rem;
            box-shadow: 0 4px 6px -1px rgb(0 0 0 / 0.1);
            border: 1px solid #334155;
        }}
        .card h2 {{ font-size: 1rem; margin-top: 0; color: #94a3b8; }}
        .stats-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 2rem; }}
        .stat-card {{ background: #1e293b; padding: 1rem; border-radius: 0.5rem; border: 1px solid #334155; text-align: center; }}
        .stat-val {{ font-size: 1.25rem; font-weight: bold; color: #38bdf8; }}
        .stat-label {{ font-size: 0.75rem; color: #94a3b8; text-transform: uppercase; }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>ResourceSpy // System Health Report</h1>
            <p style="color: #64748b; font-size: 0.875rem;">Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </header>

        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-val">{data[-1]['cpu_percent']}%</div>
                <div class="stat-label">CPU Usage</div>
            </div>
            <div class="stat-card">
                <div class="stat-val">{data[-1]['ram_used'] // (1024**2)} MB</div>
                <div class="stat-label">RAM Used</div>
            </div>
            <div class="stat-card">
                <div class="stat-val">{data[-1]['disk_free'] // (1024**3)} GB</div>
                <div class="stat-label">Disk Free</div>
            </div>
            <div class="stat-card">
                <div class="stat-val">{data[-1]['load_avg']}</div>
                <div class="stat-label">Load (1m)</div>
            </div>
        </div>

        <div class="grid">
            <div class="card">
                <h2>CPU & RAM Trends (%)</h2>
                <canvas id="resourceChart"></canvas>
            </div>
            <div class="card">
                <h2>Network Throughput (MB per check)</h2>
                <canvas id="networkChart"></canvas>
            </div>
        </div>
    </div>

    <script>
        const commonOptions = {{
            responsive: true,
            scales: {{
                y: {{ grid: {{ color: '#334155' }}, ticks: {{ color: '#94a3b8' }} }},
                x: {{ grid: {{ display: false }}, ticks: {{ color: '#94a3b8' }} }}
            }},
            plugins: {{ legend: {{ labels: {{ color: '#f8fafc' }} }} }}
        }};

        new Chart(document.getElementById('resourceChart'), {{
            type: 'line',
            data: {{
                labels: {json.dumps(labels)},
                datasets: [
                    {{ label: 'CPU %', data: {json.dumps(cpu_data)}, borderColor: '#ef4444', tension: 0.3, fill: false }},
                    {{ label: 'RAM %', data: {json.dumps(ram_data)}, borderColor: '#3b82f6', tension: 0.3, fill: false }}
                ]
            }},
            options: commonOptions
        }});

        new Chart(document.getElementById('networkChart'), {{
            type: 'line',
            data: {{
                labels: {json.dumps(labels)},
                datasets: [
                    {{ label: 'Sent (MB)', data: {json.dumps(net_sent_rates)}, borderColor: '#10b981', tension: 0.3, fill: false }},
                    {{ label: 'Recv (MB)', data: {json.dumps(net_recv_rates)}, borderColor: '#8b5cf6', tension: 0.3, fill: false }}
                ]
            }},
            options: commonOptions
        }});
    </script>
</body>
</html>
    """
    with open(REPORT_FILE, 'w') as f:
        f.write(html_template)
    print(f"Report generated successfully: {REPORT_FILE}")

def main():
    parser = argparse.ArgumentParser(description="ResourceSpy - Agentless Monitoring")
    parser.add_argument('--alert', action='store_true', help="Enable CPU usage alerts")
    args = parser.parse_args()

    metrics = get_metrics()
    all_data = save_metrics(metrics)
    
    if args.alert:
        check_alerts(all_data)
    
    generate_report(all_data)

if __name__ == "__main__":
    main()
