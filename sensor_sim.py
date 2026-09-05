"""
sensor_sim.py

Simulates a mechanical system's sensor stream (an internal-combustion
engine) using numpy/pandas. This stands in for a real telemetry feed
(e.g. an OBD-II reader or an industrial PLC) so the dashboard has
something realistic to plot without needing real hardware.

Signals modeled:
- coolant_temp_c   : the headline metric, what the dashboard flags
- rpm              : engine speed, drives load and heat generation
- oil_pressure_psi : drops as temp rises, a secondary health signal
- load_pct         : throttle/load, the main driver of heat

The model is a simple thermal RC-circuit style simulation: temperature
drifts toward a "target" set by engine load, with lag (thermal mass)
and noise, plus occasional injected fault scenarios (stuck thermostat,
coolant loss, high sustained load) so the overheat alert has something
real to catch.
"""

from __future__ import annotations

import time
import random
import threading
from collections import deque
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

# ---- thresholds (°C) -------------------------------------------------
NORMAL_MAX = 105       # top of normal operating band
WARNING_MAX = 115       # above this: overheating warning
CRITICAL_MAX = 125       # above this: critical / shut down

AMBIENT_TEMP = 22.0
IDLE_TARGET = 90.0


@dataclass
class EngineState:
    coolant_temp_c: float = AMBIENT_TEMP
    rpm: float = 800.0
    oil_pressure_psi: float = 45.0
    load_pct: float = 10.0
    fault: str | None = None          # active fault scenario, if any
    fault_ticks_left: int = 0
    t: float = 0.0                    # seconds since start


class EngineSimulator:
    """Thread-safe rolling simulation of engine sensor data."""

    def __init__(self, history_len: int = 600, hz: float = 2.0):
        self.hz = hz
        self.dt = 1.0 / hz
        self.state = EngineState()
        self.history: deque[dict] = deque(maxlen=history_len)
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._running = False
        self._rng = np.random.default_rng()

    # -- public API ------------------------------------------------
    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def snapshot(self, n: int | None = None) -> list[dict]:
        with self._lock:
            data = list(self.history)
        if n:
            return data[-n:]
        return data

    def trigger_fault(self, name: str, duration_s: float = 45):
        """Manually inject a fault scenario (for the demo 'Simulate Fault' button)."""
        with self._lock:
            self.state.fault = name
            self.state.fault_ticks_left = int(duration_s * self.hz)

    def clear_fault(self):
        with self._lock:
            self.state.fault = None
            self.state.fault_ticks_left = 0

    # -- internal simulation loop -----------------------------------
    def _loop(self):
        while self._running:
            self._step()
            time.sleep(self.dt)

    def _step(self):
        s = self.state
        s.t += self.dt

        # Randomly wander the driving load (throttle) using an
        # Ornstein-Uhlenbeck-ish process so it feels organic.
        load_drift = self._rng.normal(0, 3.0)
        s.load_pct = float(np.clip(s.load_pct + load_drift - 0.05 * (s.load_pct - 35), 0, 100))

        # RPM follows load with noise
        target_rpm = 800 + s.load_pct * 38
        s.rpm = float(s.rpm + (target_rpm - s.rpm) * 0.15 + self._rng.normal(0, 40))
        s.rpm = float(np.clip(s.rpm, 700, 7000))

        # Occasionally auto-trigger a random fault so the "live" demo
        # produces overheat events on its own without user input.
        if s.fault is None and self._rng.random() < 0.0025:
            s.fault = self._rng.choice(
                ["stuck_thermostat", "coolant_loss", "high_load"], p=[0.4, 0.3, 0.3]
            )
            s.fault_ticks_left = int(self._rng.uniform(30, 70) * self.hz)

        cooling_efficiency = 1.0
        heat_bonus = 0.0
        oil_penalty = 0.0

        if s.fault == "stuck_thermostat":
            cooling_efficiency = 0.35   # radiator loop barely engages
        elif s.fault == "coolant_loss":
            cooling_efficiency = 0.15
            oil_penalty = 6.0
        elif s.fault == "high_load":
            heat_bonus = 25.0

        if s.fault:
            s.fault_ticks_left -= 1
            if s.fault_ticks_left <= 0:
                s.fault = None

        # Thermal model: temp relaxes toward a load-driven target,
        # with cooling system efficiency reducing how fast heat escapes.
        target_temp = IDLE_TARGET + (s.load_pct / 100) * 35 + heat_bonus
        cooling_rate = 0.06 * cooling_efficiency
        heating_rate = 0.05 + (s.load_pct / 100) * 0.05

        if s.coolant_temp_c < target_temp:
            s.coolant_temp_c += heating_rate * (target_temp - s.coolant_temp_c)
        else:
            s.coolant_temp_c -= cooling_rate * (s.coolant_temp_c - target_temp)

        s.coolant_temp_c += self._rng.normal(0, 0.25)
        s.coolant_temp_c = float(np.clip(s.coolant_temp_c, AMBIENT_TEMP, 140))

        # Oil pressure: nominal band, drops as temp climbs past normal,
        # plus any active fault penalty.
        base_pressure = 45 - max(0, s.coolant_temp_c - NORMAL_MAX) * 0.4
        s.oil_pressure_psi = float(
            np.clip(base_pressure - oil_penalty + self._rng.normal(0, 0.8), 5, 60)
        )

        status = self._status_for(s.coolant_temp_c)

        with self._lock:
            self.history.append(
                {
                    "timestamp": time.time(),
                    "coolant_temp_c": round(s.coolant_temp_c, 1),
                    "rpm": round(s.rpm),
                    "oil_pressure_psi": round(s.oil_pressure_psi, 1),
                    "load_pct": round(s.load_pct, 1),
                    "status": status,
                    "fault": s.fault,
                }
            )

    @staticmethod
    def _status_for(temp: float) -> str:
        if temp >= CRITICAL_MAX:
            return "critical"
        if temp >= WARNING_MAX:
            return "warning"
        if temp >= NORMAL_MAX:
            return "elevated"
        return "normal"

    # -- data science bits: pandas summary stats ---------------------
    def summary_frame(self) -> pd.DataFrame:
        """Return the current history as a pandas DataFrame, and attach
        rolling-average / anomaly columns. This is the 'Pandas' layer:
        the Flask route below serializes this to JSON for the frontend,
        and a standalone analysis script can load the CSV export the
        same way for offline Matplotlib plotting."""
        data = self.snapshot()
        if not data:
            return pd.DataFrame()
        df = pd.DataFrame(data)
        df["time"] = pd.to_datetime(df["timestamp"], unit="s")
        df["temp_rolling_avg"] = df["coolant_temp_c"].rolling(10, min_periods=1).mean()
        df["temp_delta"] = df["coolant_temp_c"].diff().fillna(0)
        return df


# a module-level singleton used by the Flask app
simulator = EngineSimulator()
