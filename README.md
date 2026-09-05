# Coolant Watch — Live Engine Health Dashboard

A small full-stack demo: a simulated engine sensor feed, served over a
Flask API, visualized as a live-updating web dashboard that flags
overheating in real time.

![status](https://img.shields.io/badge/data-simulated-blue) ![stack](https://img.shields.io/badge/stack-Flask%20%2B%20Pandas%20%2B%20Chart.js-informational)

## What it does

- **Simulates** a car engine's cooling system (`sensor_sim.py`) — coolant
  temperature, RPM, oil pressure, and load — using a simple thermal
  model (numpy/pandas) with realistic lag, noise, and randomly
  injected fault scenarios (stuck thermostat, coolant loss, sustained
  high load).
- **Serves** that data from a Flask backend (`app.py`) as JSON, plus a
  pandas-derived rolling-average/summary endpoint and a CSV export.
- **Displays** it as a live dashboard (`templates/index.html` +
  `static/`) using Chart.js — a real-time line chart color-coded by
  status, gauges for RPM/oil pressure/load, and an alert banner that
  appears the moment coolant temperature crosses into warning or
  critical territory.
- **Analyzes offline**, too — `analyze_log.py` loads an exported CSV
  and renders a static Matplotlib summary plot with shaded threshold
  bands, for when you want the "data science report" version instead
  of the live view.

## Why these thresholds

| Status    | Coolant temp        | Meaning                              |
|-----------|----------------------|---------------------------------------|
| Normal    | < 105°C              | Typical operating range               |
| Elevated  | 105–115°C            | Worth watching                        |
| Warning   | 115–125°C            | Overheating — reduce load             |
| Critical  | ≥ 125°C              | Risk of engine damage — shut down     |

These are illustrative, not from a specific vehicle's spec sheet.

## Running it locally

```bash
git clone <this-repo-url>
cd engine-dashboard
pip install -r requirements.txt
python app.py
```

Then open **http://localhost:5000**. The simulator starts automatically
and streams a new reading twice a second; the page polls the API once
a second. Use the "Simulate a fault" buttons to force an overheat
event, or just wait — faults also trigger randomly on their own.

### Deploy publicly

This is a Flask app, so the GitHub repository itself cannot run the dashboard.
To deploy the same app publicly, create a new Web Service on Render from this
repository. Render will use `render.yaml`, install the requirements, and start
the app with Gunicorn.

To try the offline Matplotlib report:

```bash
curl -o session.csv http://localhost:5000/api/export.csv
python analyze_log.py session.csv
```

## Project structure

```
engine-dashboard/
├── app.py              # Flask routes / API
├── sensor_sim.py        # thermal simulation (numpy/pandas), runs on a background thread
├── analyze_log.py        # offline Matplotlib summary plot from an exported CSV
├── templates/
│   └── index.html
├── static/
│   ├── style.css
│   └── script.js         # Chart.js live chart + polling
├── requirements.txt
└── README.md
```

## API

| Route                    | Method | Returns                                         |
|---------------------------|--------|--------------------------------------------------|
| `/api/live?n=120`          | GET    | last `n` sensor readings                          |
| `/api/summary`             | GET    | pandas rolling stats + current status             |
| `/api/export.csv`          | GET    | full session history as CSV                       |
| `/api/fault/<name>`        | POST   | inject a fault (`stuck_thermostat`, `coolant_loss`, `high_load`) |
| `/api/fault/clear`         | POST   | clear the active fault                            |

## Notes

This is a simulation for demonstration purposes — there's no real
hardware or OBD-II reader behind it. Swapping in a real sensor feed
would mean replacing `EngineSimulator._step()` with a real data source
while keeping the same reading shape (`coolant_temp_c`, `rpm`,
`oil_pressure_psi`, `load_pct`, `status`, `fault`), so the API and
frontend need no changes.
