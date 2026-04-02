# ResourceSpy

A lightweight, "Agentless" system monitoring tool for Linux servers. ResourceSpy captures essential health metrics and generates a professional, dark-mode visual dashboard.

## Why "Agentless"?

Traditional monitoring tools (like Prometheus or Datadog) often require a persistent background agent that consumes memory and CPU. ResourceSpy is designed for **lightweight VPS environments** where every megabyte counts. It runs as a transient task, collects data, updates a JSON database, and disappears.

## Features

- **CPU & RAM Tracking**: Line charts showing trends over the last 24 hours.
- **Network Throughput**: Visualizes MB sent/received between checks.
- **Disk & Load Stats**: Real-time snapshot of remaining space and system load.
- **Auto-Pruning**: Automatically keeps only the last 24 hours of data.
- **Standalone Dashboard**: Generates a single `report.html` file—no web server required (just open it in your browser).
- **Threshold Alerts**: Console/Webhook alerts for sustained high CPU usage.

## Installation

1. **Clone or download** this directory to your server.
2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

Run the script manually to generate a report:
```bash
python3 resource_spy.py --alert
```

## Automation (Crontab)

To monitor your server every 15 minutes, add a entry to your crontab:

1. Open crontab editor:
   ```bash
   crontab -e
   ```
2. Add the following line (adjust path to your script):
   ```cron
   */15 * * * * cd /path/to/resource_spy && /usr/bin/python3 resource_spy.py --alert >> monitor.log 2>&1
   ```
## Example
report.html
<img width="1295" height="731" alt="image" src="https://github.com/user-attachments/assets/08a25451-5ca8-4845-9d5c-f3a7d251dd86" />

metrics.json
<img width="692" height="367" alt="image" src="https://github.com/user-attachments/assets/69d778ff-8f8a-40b3-bdcb-2d988e72b83a" />

## Requirements
- Python 3.6+
- `psutil`
- Internet connection (for Chart.js CDN in the dashboard)
