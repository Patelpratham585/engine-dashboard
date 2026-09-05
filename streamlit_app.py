from __future__ import annotations

import streamlit as st
from streamlit_autorefresh import st_autorefresh

from sensor_sim import CRITICAL_MAX, NORMAL_MAX, WARNING_MAX, simulator


st.set_page_config(page_title="Coolant Watch", page_icon="◍", layout="wide")
simulator.start()
st_autorefresh(interval=1000, key="sensor-refresh")

st.title("Coolant Watch")
st.caption("Engine bay telemetry - Unit 07")

readings = simulator.snapshot(90)
summary = simulator.summary_frame()

if not readings or summary.empty:
    st.info("Starting sensor stream...")
    st.stop()

latest = readings[-1]
status = latest["status"]
status_labels = {
    "normal": "Normal",
    "elevated": "Elevated",
    "warning": "Warning",
    "critical": "Critical",
}

if status in {"warning", "critical"}:
    st.error(f"{status_labels[status]}: coolant temperature is {latest['coolant_temp_c']:.1f} C")
elif status == "elevated":
    st.warning(f"Elevated coolant temperature: {latest['coolant_temp_c']:.1f} C")

metric_columns = st.columns(4)
metric_columns[0].metric("Coolant temperature", f"{latest['coolant_temp_c']:.1f} C", status_labels[status])
metric_columns[1].metric("Engine speed", f"{latest['rpm']:,} rpm")
metric_columns[2].metric("Oil pressure", f"{latest['oil_pressure_psi']:.1f} psi")
metric_columns[3].metric("Load", f"{latest['load_pct']:.0f}%")

chart_data = summary.set_index("time")[["coolant_temp_c", "temp_rolling_avg"]].rename(
    columns={"coolant_temp_c": "Coolant temperature", "temp_rolling_avg": "Rolling average"}
)
st.subheader("Coolant temperature")
st.line_chart(chart_data, y_label="C", height=320)
st.caption(
    f"Normal < {NORMAL_MAX} C | Elevated {NORMAL_MAX}-{WARNING_MAX} C | "
    f"Warning >= {WARNING_MAX} C | Critical >= {CRITICAL_MAX} C"
)

stats_columns = st.columns(4)
stats_columns[0].metric("Session maximum", f"{summary['coolant_temp_c'].max():.1f} C")
stats_columns[1].metric("Session minimum", f"{summary['coolant_temp_c'].min():.1f} C")
stats_columns[2].metric("Mean", f"{summary['coolant_temp_c'].mean():.1f} C")
stats_columns[3].metric("Readings logged", f"{len(summary):,}")

st.subheader("Simulate a fault")
fault_columns = st.columns(4)
faults = [
    ("Stuck thermostat", "stuck_thermostat"),
    ("Coolant loss", "coolant_loss"),
    ("Sustained high load", "high_load"),
]
for column, (label, fault) in zip(fault_columns, faults):
    if column.button(label, use_container_width=True):
        simulator.trigger_fault(fault)
if fault_columns[3].button("Clear fault", use_container_width=True):
    simulator.clear_fault()

st.caption(f"Active fault: {latest['fault'] or 'none'}")