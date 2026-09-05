"""
analyze_log.py

Offline analysis companion for the dashboard. Load a CSV exported from
/api/export.csv (or produced by running the simulator directly) and
render a static Matplotlib summary: the full temperature trace with
threshold bands shaded in, plus a rolling-average overlay.

Usage:
    python app.py                       # run the dashboard, let it log data
    curl -o session.csv localhost:5000/api/export.csv
    python analyze_log.py session.csv
"""

import sys

import matplotlib.pyplot as plt
import pandas as pd

from sensor_sim import NORMAL_MAX, WARNING_MAX, CRITICAL_MAX


def plot_session(csv_path: str, out_path: str = "session_summary.png"):
    df = pd.read_csv(csv_path, parse_dates=["time"])
    if df.empty:
        print("No data in log — run the dashboard for a bit first.")
        return

    fig, ax = plt.subplots(figsize=(11, 5))

    ax.axhspan(0, NORMAL_MAX, color="#3ecf8e", alpha=0.08, label="normal")
    ax.axhspan(NORMAL_MAX, WARNING_MAX, color="#e8c04a", alpha=0.10, label="elevated")
    ax.axhspan(WARNING_MAX, CRITICAL_MAX, color="#ff9a3d", alpha=0.10, label="warning")
    ax.axhspan(CRITICAL_MAX, df["coolant_temp_c"].max() + 10, color="#ff4f4f", alpha=0.10, label="critical")

    ax.plot(df["time"], df["coolant_temp_c"], color="#1f2933", linewidth=1.2, label="coolant temp")
    ax.plot(df["time"], df["temp_rolling_avg"], color="#0b6efc", linewidth=1.6,
            linestyle="--", label="rolling avg (10 samples)")

    ax.set_title("Engine coolant temperature — session summary")
    ax.set_xlabel("time")
    ax.set_ylabel("temperature (°C)")
    ax.legend(loc="upper left", fontsize=8, ncol=3)
    fig.autofmt_xdate()
    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    print(f"Saved {out_path}")

    overheat = df[df["status"].isin(["warning", "critical"])]
    print(f"Samples logged:        {len(df)}")
    print(f"Max temp:               {df['coolant_temp_c'].max():.1f} C")
    print(f"Mean temp:              {df['coolant_temp_c'].mean():.1f} C")
    print(f"Time spent overheating: {len(overheat) / 2:.0f} s (at 2 Hz sampling)")


if __name__ == "__main__":
    csv_path = sys.argv[1] if len(sys.argv) > 1 else "session.csv"
    plot_session(csv_path)
