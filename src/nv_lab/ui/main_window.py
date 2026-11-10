"""Operator UI based on the author's Figma exports in ui/.

Implementation prepared with AI assistance; see docs/ETYKA_AI.md.
Acquisition is offline; explicit read-only diagnostics run in a subprocess.
"""

import logging
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QFrame, QHBoxLayout,
    QLabel, QMainWindow, QPushButton, QScrollArea, QSpinBox, QStackedWidget,
    QTabWidget, QVBoxLayout, QWidget, QSizePolicy, QSplitter,
)

from nv_lab.core.sequences import T1Settings, compile_t1
from nv_lab.ui.console import DiagnosticsConsole

logger = logging.getLogger(__name__)


STYLE = """
QMainWindow, QWidget#root { background: white; color: #151515; }
QWidget { font-family: 'Segoe UI'; font-size: 13px; }
QLabel#status { background: #2b2b2b; color: white; padding: 14px; }
QWidget#header { background: #2b2b2b; }
QPushButton#settings { background: #414141; color: white; padding: 10px 18px; }
QPushButton#settings:hover { background: #555555; }
QLabel#section { background: #d9d9d9; font-weight: bold; padding: 10px; }
QLabel#notice { color: #51515c; padding: 6px; }
QLabel#feedback { color: #454555; padding: 6px; }
QDoubleSpinBox, QSpinBox, QComboBox {
    background: #f2f2f7; color: #151515; border: 1px solid #c6c6cf;
    border-radius: 0px; padding: 6px; min-height: 22px;
}
QPushButton { background: #d9d9d9; color: #151515; border: 0; padding: 12px; }
QPushButton:hover { background: #c9c9d0; }
QPushButton:checked { background: #bfc0c9; font-weight: bold; }
QPushButton:disabled { background: #e5e5e9; color: #85858e; }
QPushButton#preview { background: #d8e8ff; font-weight: bold; }
QTabWidget::pane { border: 1px solid #d9d9df; }
QTabBar::tab { background: #ededf1; color: #151515; padding: 9px 16px; }
QTabBar::tab:selected { background: #d8e8ff; }
QCheckBox { color: #151515; padding: 5px; }
"""


def number(minimum: float, maximum: float, value: float, unit: str,
           decimals: int = 3) -> QDoubleSpinBox:
    box = QDoubleSpinBox()
    box.setDecimals(decimals)
    box.setRange(minimum, maximum)
    box.setValue(value)
    box.setSuffix(f" {unit}")
    box.setKeyboardTracking(False)
    box.setMinimumWidth(100)
    box.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
    return box


def section(text: str) -> QLabel:
    label = QLabel(text)
    label.setObjectName("section")
    label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return label


class MainWindow(QMainWindow):
    """Editable configuration and compiler preview; hardware actions disabled."""

    MODES = ("CW ODMR", "Pulsed ODMR", "T1")

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("NV Lab — stanowisko magnetometru | OFFLINE")
        self.resize(1280, 800)
        self.setMinimumSize(1000, 700)
        self.setStyleSheet(STYLE)
        self.last_sequences = ()

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 12)
        self.status = QLabel(
            "○ SYSTEM: OFFLINE  │  ○ Pulse Streamer: niepołączony  │  "
            "○ SG386: niepołączony  │  ○ Oscyloskop: niepołączony"
        )
        self.status.setObjectName("status")
        self.status.setWordWrap(True)
        header = QWidget()
        header.setObjectName("header")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(0, 0, 16, 0)
        header_layout.addWidget(self.status, 1)
        self.settings_button = QPushButton("Ustawienia")
        self.settings_button.setObjectName("settings")
        self.settings_button.setToolTip("Ustawienia aplikacji — panel w przygotowaniu.")
        header_layout.addWidget(self.settings_button)
        layout.addWidget(header)
        splitter = QSplitter(Qt.Orientation.Vertical)
        body_widget = QWidget()
        body = QHBoxLayout(body_widget)
        body.setContentsMargins(28, 8, 28, 0)
        body.setSpacing(32)
        splitter.addWidget(body_widget)
        self.console = DiagnosticsConsole(self)
        splitter.addWidget(self.console)
        splitter.setChildrenCollapsible(False)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([500, 250])
        layout.addWidget(splitter, 1)
        self.device_test_status = {"sg386": "nietestowany", "scope": "nietestowany"}
        self.console.test_status.connect(self._update_test_status)

        left = QVBoxLayout()
        body.addLayout(left, 3)
        self.tabs = QTabWidget()
        self.measurement_plot = self._plot("Brak danych pomiarowych", "Częstotliwość", "MHz")
        self.measurement_plot.setLabel("left", "Sygnał", units="V")
        self.tabs.addTab(self.measurement_plot, "Pomiar")
        self.sequence_plot = self._plot("Podgląd offline — brak walidacji na sprzęcie", "Czas", "µs")
        self.sequence_plot.setMouseEnabled(x=True, y=False)
        self.tabs.addTab(self.sequence_plot, "Sekwencja T1 (offline)")
        left.addWidget(self.tabs, 1)
        self.notice = QLabel("Pomiar OFFLINE · Testy komunikacji dostępne w konsoli poniżej.")
        self.notice.setObjectName("notice")
        left.addWidget(self.notice)
        modes = QHBoxLayout()
        self.mode_buttons = []
        for index, title in enumerate(self.MODES):
            button = QPushButton(title)
            button.setCheckable(True)
            button.clicked.connect(lambda checked=False, i=index: self.set_mode(i))
            self.mode_buttons.append(button)
            modes.addWidget(button)
        left.addLayout(modes)

        panel = QWidget()
        panel.setMinimumWidth(310)
        right = QVBoxLayout(panel)
        right.setContentsMargins(0, 0, 8, 0)
        common = QFormLayout()
        self.signal_scale = number(0.001, 10000, 100, "mV", 3)
        self.power = number(-50, -10, -30, "dBm", 1)
        self.frequency = number(2000, 3000, 2870, "MHz", 6)
        common.addRow("Signal Scale", self.signal_scale)
        common.addRow("RF Power", self.power)
        common.addRow("Freq", self.frequency)
        right.addLayout(common)
        self.mode_fields = QStackedWidget()
        right.addWidget(self.mode_fields)
        for index in range(2):
            page = QWidget()
            fields = QVBoxLayout(page)
            fields.setContentsMargins(0, 0, 0, 0)
            fields.addWidget(section("ODMR"))
            form = QFormLayout()
            form.addRow("Freq 1", number(2000, 3000, 2800, "MHz", 6))
            form.addRow("Freq 2", number(2000, 3000, 2940, "MHz", 6))
            fields.addLayout(form)
            if index == 1:
                fields.addWidget(section("RABI"))
                rabi = QFormLayout()
                rabi.addRow("Rabi 1", number(0, 1e6, 0, "ns", 0))
                rabi.addRow("Rabi 2", number(0, 1e6, 1000, "ns", 0))
                fields.addLayout(rabi)
            note = QLabel("Konfiguracja robocza. Obsługa pomiaru będzie dodana później.")
            note.setWordWrap(True)
            fields.addWidget(note)
            fields.addStretch()
            self.mode_fields.addWidget(page)

        t1_page = QWidget()
        t1 = QVBoxLayout(t1_page)
        t1.setContentsMargins(0, 0, 0, 0)
        t1.addWidget(section("T1"))
        form = QFormLayout()
        self.pi_duration = number(0, 1e6, 100, "ns", 0)
        self.tau_start = number(0, 1e6, 100, "µs")
        self.tau_stop = number(0, 1e6, 1000, "µs")
        form.addRow("π pulse duration", self.pi_duration)
        form.addRow("Start τ", self.tau_start)
        form.addRow("Stop τ", self.tau_stop)
        t1.addLayout(form)
        t1.addWidget(section("Meas"))
        form = QFormLayout()
        self.points = QSpinBox()
        self.points.setRange(2, 100000)
        self.points.setValue(50)
        self.averages = QSpinBox()
        self.averages.setRange(1, 1000000)
        self.averages.setValue(100)
        for box in (self.points, self.averages):
            box.setToolTip("Parametr przyszłego pomiaru; nie wpływa na podgląd pojedynczego cyklu.")
        form.addRow("No. points", self.points)
        form.addRow("Averages", self.averages)
        t1.addLayout(form)
        self.reference = QCheckBox("Ref. subtraction")
        self.reference.setChecked(True)
        self.reference.setToolTip("Podgląd pokazuje oba cykle. Nie wykonuje odejmowania danych.")
        t1.addWidget(self.reference)
        t1.addWidget(section("Podgląd pojedynczego punktu"))
        form = QFormLayout()
        self.preview_tau = QComboBox()
        self.preview_tau.addItems(("Start τ", "Stop τ"))
        form.addRow("Punkt", self.preview_tau)
        t1.addLayout(form)
        self.advanced_button = QPushButton("Pokaż czasy i polaryzację TTL ▾")
        self.advanced_button.setCheckable(True)
        t1.addWidget(self.advanced_button)
        advanced = QWidget()
        advanced_layout = QVBoxLayout(advanced)
        advanced_layout.setContentsMargins(0, 0, 0, 0)
        form = QFormLayout()
        self.initialization = number(0.001, 1e6, 2000, "µs")
        self.readout = number(0.001, 1e6, 2000, "µs")
        self.trigger = number(1, 1e9, 300, "ns", 0)
        self.delay = number(0, 1e9, 500, "ns", 0)
        form.addRow("Inicjalizacja", self.initialization)
        form.addRow("Odczyt", self.readout)
        form.addRow("Trigger", self.trigger)
        form.addRow("Opóźnienie odczytu", self.delay)
        advanced_layout.addLayout(form)
        self.active_high = QCheckBox("Laser aktywny stanem wysokim")
        self.active_high.setToolTip("Robocza polaryzacja TTL do podglądu; wymaga sprawdzenia w laboratorium.")
        advanced_layout.addWidget(self.active_high)
        t1.addWidget(advanced)
        advanced.hide()
        self.advanced_button.toggled.connect(advanced.setVisible)
        self.mode_fields.addWidget(t1_page)

        self.preview_button = QPushButton("PODGLĄD T1")
        self.preview_button.setObjectName("preview")
        self.preview_button.clicked.connect(self.show_preview)
        self.feedback = QLabel("Ustaw parametry i wybierz PODGLĄD T1.")
        self.feedback.setObjectName("feedback")
        self.feedback.setWordWrap(True)
        actions = QHBoxLayout()
        self.start_button = QPushButton("START")
        self.stop_button = QPushButton("STOP")
        self.save_button = QPushButton("SAVE")
        for button in (self.start_button, self.stop_button, self.save_button):
            button.setEnabled(False)
            button.setToolTip("Niedostępne w wersji offline: brak akwizycji i danych pomiarowych.")
            actions.addWidget(button)
        right.addStretch()
        scroll = QScrollArea()
        scroll.setMinimumWidth(340)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(panel)
        sidebar = QVBoxLayout()
        sidebar.addWidget(scroll, 1)
        sidebar.addWidget(self.preview_button)
        sidebar.addWidget(self.feedback)
        sidebar.addLayout(actions)
        body.addLayout(sidebar, 1)

        self.signal_scale.valueChanged.connect(self._set_signal_scale)
        for box in (self.pi_duration, self.tau_start, self.tau_stop, self.initialization,
                    self.readout, self.trigger, self.delay, self.points, self.averages):
            box.valueChanged.connect(self.invalidate_preview)
        self.preview_tau.currentIndexChanged.connect(self.invalidate_preview)
        self.active_high.toggled.connect(self.invalidate_preview)
        self.reference.toggled.connect(self.invalidate_preview)
        self._set_signal_scale()
        self.set_mode(2)
        logger.info("Uruchomiono interfejs. Akwizycja wyłączona; diagnostyka na żądanie.")

    def _update_test_status(self, device: str, state: str):
        self.device_test_status[device] = state
        self.status.setText(
            "○ SYSTEM: POMIAR OFFLINE  │  ○ Pulse Streamer: niepołączony  │  "
            f"SG386: {self.device_test_status['sg386']}  │  "
            f"Oscyloskop: {self.device_test_status['scope']}"
        )

    def closeEvent(self, event):
        self.console.shutdown()
        super().closeEvent(event)

    @staticmethod
    def _plot(title: str, x_label: str, unit: str) -> pg.PlotWidget:
        plot = pg.PlotWidget(background="#f1f1f3")
        plot.setTitle(title, color="#555563", size="12pt")
        plot.setLabel("bottom", x_label, units=unit)
        plot.getAxis("bottom").enableAutoSIPrefix(False)
        plot.showGrid(x=True, y=True, alpha=0.15)
        for name in ("left", "bottom"):
            plot.getAxis(name).setPen("#686874")
            plot.getAxis(name).setTextPen("#454550")
        return plot

    def _set_signal_scale(self) -> None:
        scale_v = self.signal_scale.value() / 1000
        self.measurement_plot.setYRange(-scale_v, scale_v, padding=0)

    def set_mode(self, index: int) -> None:
        self.mode_fields.setCurrentIndex(index)
        for i, button in enumerate(self.mode_buttons):
            button.setChecked(i == index)
        self.preview_button.setEnabled(index == 2)
        if index != 2:
            self.tabs.setCurrentIndex(0)
        self.tabs.setTabEnabled(1, index == 2)
        self.measurement_plot.setLabel(
            "bottom", "Czas relaksacji" if index == 2 else "Częstotliwość",
            units="s" if index == 2 else "Hz",
        )
        self.measurement_plot.getAxis("bottom").enableAutoSIPrefix(True)
        self.invalidate_preview()
        logger.info("Wybrano tryb %s.", self.MODES[index])

    def invalidate_preview(self, *_args) -> None:
        self.last_sequences = ()
        self.sequence_plot.clear()
        self.feedback.setText(
            "Parametry robocze. Wybierz PODGLĄD T1, aby przeliczyć sekwencję."
            if self.mode_fields.currentIndex() == 2
            else "Tryb offline. Obsługa tego pomiaru będzie dodana później."
        )

    def show_preview(self) -> None:
        """Compile the selected endpoint; never synthesize measurement values."""
        self.invalidate_preview()
        try:
            start_ns = round(self.tau_start.value() * 1000)
            stop_ns = round(self.tau_stop.value() * 1000)
            if start_ns > stop_ns:
                raise ValueError("Start τ nie może być większe niż Stop τ.")
            if round(self.pi_duration.value()) > start_ns:
                raise ValueError("W obecnym kompilatorze impuls π musi być ≤ Start τ.")
            settings = T1Settings(
                initialization_ns=round(self.initialization.value() * 1000),
                pi_pulse_ns=round(self.pi_duration.value()),
                tau_ns=start_ns if self.preview_tau.currentIndex() == 0 else stop_ns,
                readout_ns=round(self.readout.value() * 1000),
                trigger_ns=round(self.trigger.value()),
                readout_delay_ns=round(self.delay.value()),
                laser_active_high=self.active_high.isChecked(),
            )
            if settings.trigger_ns > settings.readout_ns:
                raise ValueError("Trigger nie może być dłuższy niż okno odczytu.")
            sequences = [compile_t1(settings, with_pi=True)]
            if self.reference.isChecked():
                sequences.append(compile_t1(settings, with_pi=False))
        except ValueError as exc:
            self.feedback.setText(f"Błąd parametrów: {exc}")
            logger.warning("Podgląd T1 odrzucony: %s", exc)
            return

        self.last_sequences = tuple(sequences)
        logger.info("Podgląd T1: tau=%d ns, cykl=%d ns, liczba cykli=%d.",
                    settings.tau_ns, sequences[0].duration_ns, len(sequences))
        tracks = [("Laser TTL", sequences[0].channels["laser"], "#27935a"),
                  ("MW π", sequences[0].channels["mw_gate"], "#297bc1"),
                  ("Trigger", sequences[0].channels["scope_trigger"], "#be7630")]
        if len(sequences) == 2:
            tracks.append(("MW referencja", sequences[1].channels["mw_gate"], "#8b66b1"))
        ticks = []
        for index, (name, pattern, color) in enumerate(tracks):
            offset = (len(tracks) - index - 1) * 2
            x, y, cursor = [], [], 0
            for duration, level in pattern:
                x.extend((cursor / 1000, (cursor + duration) / 1000))
                y.extend((offset + level, offset + level))
                cursor += duration
            self.sequence_plot.plot(x, y, pen=pg.mkPen(color, width=2))
            ticks.append((offset + 0.5, name))
        self.sequence_plot.getAxis("left").setTicks([ticks])
        self.sequence_plot.autoRange()
        self.tabs.setCurrentIndex(1)
        self.feedback.setText(
            f"Podgląd τ = {settings.tau_ns / 1000:g} µs; "
            f"cykl = {sequences[0].duration_ns / 1000:g} µs. "
            f"Laser ON = {int(settings.laser_active_high)}. "
            "To przebiegi logiczne, nie wyniki pomiaru. "
            "Dla referencji czasy lasera i triggera są identyczne."
        )
