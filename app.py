"""
app.py - Flask backend for the Engine Health Dashboard.

Serves:
  GET  /                     -> dashboard page
  GET  /api/live?n=120       -> last n readings as JSON (for Chart.js polling)
  GET  /api/summary          -> pandas-derived rolling stats + current status
  GET  /api/export.csv       -> full in-memory history as CSV (pandas)
  POST /api/fault/<name>     -> manually inject a fault scenario (demo control)
  POST /api/fault/clear      -> clear any active fault
"""

from __future__ import annotations

import io

from flask import Flask, jsonify, render_template, request, Response

from sensor_sim import simulator, NORMAL_MAX, WARNING_MAX, CRITICAL_MAX

app = Flask(__name__)
simulator.start()


@app.route("/")
def index():
    return render_template(
        "index.html",
        normal_max=NORMAL_MAX,
        warning_max=WARNING_MAX,
        critical_max=CRITICAL_MAX,
    )


@app.route("/api/live")
def live():
    n = request.args.get("n", default=120, type=int)
    data = simulator.snapshot(n)
    return jsonify(
        {
            "readings": data,
            "thresholds": {
                "normal_max": NORMAL_MAX,
                "warning_max": WARNING_MAX,
                "critical_max": CRITICAL_MAX,
            },
        }
    )


@app.route("/api/summary")
def summary():
    df = simulator.summary_frame()
    if df.empty:
        return jsonify({"count": 0})

    latest = df.iloc[-1]
    return jsonify(
        {
            "count": int(len(df)),
            "current_temp_c": float(latest["coolant_temp_c"]),
            "current_status": latest["status"],
            "rolling_avg_temp_c": round(float(latest["temp_rolling_avg"]), 1),
            "max_temp_c": round(float(df["coolant_temp_c"].max()), 1),
            "min_temp_c": round(float(df["coolant_temp_c"].min()), 1),
            "mean_temp_c": round(float(df["coolant_temp_c"].mean()), 1),
            "overheat_seconds": int((df["status"].isin(["warning", "critical"])).sum() / 2),
            "active_fault": latest["fault"] if isinstance(latest["fault"], str) else None,
        }
    )


@app.route("/api/export.csv")
def export_csv():
    df = simulator.summary_frame()
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return Response(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=engine_sensor_log.csv"},
    )


@app.route("/api/fault/<name>", methods=["POST"])
def set_fault(name: str):
    valid = {"stuck_thermostat", "coolant_loss", "high_load"}
    if name not in valid:
        return jsonify({"error": f"unknown fault '{name}'", "valid": sorted(valid)}), 400
    simulator.trigger_fault(name)
    return jsonify({"ok": True, "fault": name})


@app.route("/api/fault/clear", methods=["POST"])
def clear_fault():
    simulator.clear_fault()
    return jsonify({"ok": True})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
