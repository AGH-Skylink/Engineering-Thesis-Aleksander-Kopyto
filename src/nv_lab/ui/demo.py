"""Illustrative synthetic signals for UI demonstrations, never lab measurements.

AI-assisted implementation; no hardware driver is imported by this module.
"""

from datetime import datetime, timezone
import json
import logging
import math
from pathlib import Path
import random

import pyqtgraph as pg
from PySide6.QtCore import QObject, QTimer
from PySide6.QtWidgets import QFileDialog

logger = logging.getLogger(__name__)


class DemoController(QObject):
    """Drive START/STOP/SAVE with a timer and explicitly labelled sample data."""

    def __init__(self, window):
        super().__init__(window)
        self.window = window
        self.timer = QTimer(self)
        self.timer.setInterval(100)
        self.timer.timeout.connect(self.tick)
        self.rows = []
        self.metadata = {}
        self.running = False
        self.random = random.Random(386)
        self.curve = None
        window.start_button.setEnabled(True)
        window.start_button.setToolTip("Rozpocznij demonstrację z danymi syntetycznymi.")
        window.stop_button.setToolTip("Zatrzymaj demonstrację.")
        window.save_button.setToolTip("Zapisz dane demonstracyjne do pliku JSON oznaczonego DEMO.")
        window.start_button.clicked.connect(self.start)
        window.stop_button.clicked.connect(self.stop)
        window.save_button.clicked.connect(self.save)
        window.setWindowTitle("NV Lab — DEMO | WYŁĄCZNIE DANE SYNTETYCZNE")
        window.notice.setText("DEMO · Dane syntetyczne. Urządzenia i czas pomiaru są symulowane.")
        window.notice.setStyleSheet("background: #fff0be; color: #654700; padding: 8px; font-weight: bold;")
        window.status.setStyleSheet("background: #654700; color: white; padding: 14px;")
        window.console.sg_address.setText("DEMO::SG386")
        window.console.scope_address.setText("DEMO::DSOX2014A")
        for widget in (window.console.sg_address, window.console.scope_address, window.console.backend):
            widget.setEnabled(False)
        self.mode_changed()
        logger.info("DEMO | Symulowane: SG386, Pulse Streamer, oscyloskop. Brak operacji VISA.")

    def update_status(self, state: str):
        self.window.status.setText(
            f"DEMO — {state}  │  SG386 / Pulse Streamer / oscyloskop: SYMULOWANE"
        )

    def mode_changed(self):
        self.stop()
        self.rows = []
        self.metadata = {}
        self.window.measurement_plot.clear()
        self.window.measurement_plot.setTitle("DEMO — brak próbek; naciśnij START", color="#876000")
        self.window.save_button.setEnabled(False)
        self.update_status("GOTOWY")

    def _lock_controls(self, running):
        w = self.window
        for widget in (w.mode_fields, w.power, w.frequency, *w.mode_buttons,
                       w.console.sg_button, w.console.scope_button, w.console.discover_button):
            widget.setEnabled(not running)
        # In demo mode these fields must never offer real VISA access.
        for widget in (w.console.sg_address, w.console.scope_address, w.console.backend):
            widget.setEnabled(False)
        w.preview_button.setEnabled(not running and w.mode_fields.currentIndex() == 2)
        w.start_button.setEnabled(not running)
        w.stop_button.setEnabled(running)
        w.save_button.setEnabled(not running and bool(self.rows))

    def start(self):
        if self.running:
            return
        w = self.window
        if w.console.busy:
            logger.warning("DEMO | Poczekaj na zakończenie symulowanego testu urządzenia.")
            return
        mode = w.mode_fields.currentIndex()
        count = w.points.value()
        if count > 1000:
            logger.warning("DEMO | Wybierz maksymalnie 1000 punktów demonstracji.")
            return
        if mode == 2:
            w.show_preview()
            if not w.last_sequences:
                return
            low, high = w.tau_start.value(), w.tau_stop.value()
            self.x_label, self.x_unit = "Czas relaksacji", "µs"
        else:
            low, high = (box.value() for box in w.odmr_ranges[mode])
            self.x_label, self.x_unit = "Częstotliwość", "MHz"
        if low >= high:
            logger.warning("DEMO | Początek zakresu musi być mniejszy od końca.")
            return
        self.mode = mode
        self.axis = [low + (high - low) * i / (count - 1) for i in range(count)]
        self.reference = mode == 2 and w.reference.isChecked()
        self.noise = 0.001 / math.sqrt(w.averages.value())
        self.center = w.frequency.value()
        self.rows = []
        self.random.seed(386)
        self.metadata = {
            "simulated": True,
            "label": "DEMO — SYNTHETIC DATA, NOT AN EXPERIMENT",
            "mode": w.MODES[mode],
            "created_utc": datetime.now(timezone.utc).isoformat(),
            "x_label": self.x_label, "x_unit": self.x_unit, "y_unit": "V",
            "requested_points": count, "averages": w.averages.value(),
            "sweep_start": low, "sweep_stop": high, "demo_interval_ms": 100,
            "frequency_mhz": self.center, "power_dbm": w.power.value(),
            "reference_subtraction": self.reference,
            "model": "illustrative exponential (T1) or Lorentzian dips (ODMR); not calibrated",
            "demo_t1_us": 350 if mode == 2 else None,
            "random_seed": 386, "completed": False,
        }
        if mode == 2:
            self.metadata["sequence"] = dict(w.last_sequences[0].metadata)
            self.metadata["sequence_duration_ns"] = w.last_sequences[0].duration_ns
        plot = w.measurement_plot
        plot.clear()
        plot.setTitle(f"DEMO — {w.MODES[mode]} · DANE SYNTETYCZNE", color="#876000")
        plot.setLabel("bottom", self.x_label, units=self.x_unit)
        plot.getAxis("bottom").enableAutoSIPrefix(False)
        plot.setLabel("left", "A − B (symulacja)" if self.reference else "Sygnał (symulacja)", units="V")
        plot.setXRange(low, high, padding=0.03)
        plot.enableAutoRange(axis="y", enable=True)
        self.curve = plot.plot([], [], pen=pg.mkPen("#267ac2", width=2),
                               symbol="o", symbolSize=5, symbolBrush="#267ac2")
        w.tabs.setCurrentIndex(0)
        self.running = True
        self._lock_controls(True)
        self.update_status("POMIAR SYMULOWANY 0%")
        logger.info("DEMO | SG386: symulowana konfiguracja %.6f MHz, %.1f dBm.",
                    self.center, w.power.value())
        logger.info("DEMO | Pulse Streamer: symulowane przesłanie sekwencji; oscyloskop: symulowane uzbrojenie.")
        logger.info("DEMO | START %s: %d punktów. Przyspieszony podgląd, 100 ms/punkt.", w.MODES[mode], count)
        self.timer.start()

    def tick(self):
        if not self.running:
            return
        x = self.axis[len(self.rows)]
        a = 0.070 + self.random.gauss(0, self.noise)
        if self.mode == 2:
            b = 0.070 - 0.015 * math.exp(-x / 350) + self.random.gauss(0, self.noise)
            y = a - b if self.reference else b
        else:
            width = 4.0 if self.mode == 0 else 1.8
            depth = 0.008 if self.mode == 0 else 0.012
            dip = sum(depth / (1 + ((x - center) / width) ** 2)
                      for center in (self.center - 6, self.center + 6))
            b = 0.070 - dip + self.random.gauss(0, self.noise)
            y = b
        self.rows.append({"x": x, "a_v": a, "b_v": b, "y_v": y})
        self.curve.setData([row["x"] for row in self.rows], [row["y_v"] for row in self.rows])
        progress = round(100 * len(self.rows) / len(self.axis))
        self.update_status(f"POMIAR SYMULOWANY {progress}%")
        self.window.feedback.setText(
            f"DEMO · {len(self.rows)}/{len(self.axis)} punktów ({progress}%). "
            "Dane syntetyczne, bez rzeczywistej akwizycji."
        )
        logger.info("DEMO | Punkt %d/%d: %.3f %s; sygnał %.6f V.",
                    len(self.rows), len(self.axis), x, self.x_unit, y)
        if len(self.rows) == len(self.axis):
            self.metadata["completed"] = True
            self.stop()

    def stop(self):
        if not self.running:
            return
        self.timer.stop()
        self.running = False
        complete = self.metadata.get("completed", False)
        state = "ZAKOŃCZONO" if complete else "ZATRZYMANO"
        self.update_status(f"{state} · {len(self.rows)}/{len(self.axis)} punktów")
        self.window.feedback.setText(f"DEMO · {state.lower()}; {len(self.rows)} próbek syntetycznych.")
        self._lock_controls(False)
        logger.info("DEMO | %s. Symulowane wyjścia RF i impulsy wyłączone.", state)

    def export(self, path):
        if not self.rows or self.running:
            raise ValueError("Brak zakończonych lub zatrzymanych danych DEMO do zapisu.")
        document = {"metadata": self.metadata, "samples": self.rows}
        Path(path).write_text(json.dumps(document, ensure_ascii=False, indent=2), encoding="utf-8")

    def save(self):
        if not self.rows or self.running:
            return
        path, _ = QFileDialog.getSaveFileName(self.window, "Zapis danych DEMO",
                                             "DEMO_synthetic.json", "Dane DEMO (*.json)")
        if path:
            try:
                self.export(path)
                logger.info("DEMO | Zapisano dane syntetyczne: %s", path)
            except OSError as exc:
                logger.error("DEMO | Błąd zapisu: %s", exc)
