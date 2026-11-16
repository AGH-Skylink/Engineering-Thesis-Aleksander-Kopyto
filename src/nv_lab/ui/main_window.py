"""Operator UI based on the author's Figma exports in ui/.

Implementation prepared with AI assistance; see docs/ETYKA_AI.md.
Simulation and hardware share engines; diagnostics run in a subprocess.
"""

import logging
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QFrame, QHBoxLayout,
    QLabel, QMainWindow, QPushButton, QScrollArea, QSpinBox, QStackedWidget,
    QTabWidget, QVBoxLayout, QWidget, QSizePolicy, QSplitter, QProgressBar, QAbstractSpinBox,
)

from nv_lab.core.sequences import T1Settings, compile_t1
from nv_lab.ui.console import DiagnosticsConsole
from nv_lab.ui.help_panel import HelpPanel

logger = logging.getLogger(__name__)


STYLE = """
QMainWindow, QWidget#root { background: #f4f7fc; color: #17253d; }
QWidget { background: #f4f7fc; color: #17253d; font-family: 'Segoe UI'; font-size: 13px; }
QLabel#status { background: #152743; color: #e4edf9; padding: 14px; }
QWidget#header { background: #152743; }
QPushButton#settings { background: #294162; color: white; padding: 10px 18px; }
QPushButton#settings:hover { background: #3c567a; }
QLabel#section { background: #e4ecf7; color: #294162; font-weight: bold; padding: 9px; }
QLabel#notice { color: #51515c; padding: 6px; }
QLabel#feedback { color: #454555; padding: 6px; }
QComboBox {
    background: #f2f2f7; color: #151515; border: 1px solid #c6c6cf;
    border-radius: 0px; padding: 6px; min-height: 22px;
}
/* Qt 6.12 + NoButtons: custom border/padding collapses the embedded edit to 1px.
   Keep native spinbox geometry; only colour and minimum height are styled. */
QDoubleSpinBox, QSpinBox { background:#f2f2f7; color:#151515; min-height:34px; }
QPushButton { background: #e2eaf5; color: #24395b; border: 0; border-radius: 5px; padding: 10px; }
QPushButton:hover { background: #d1dff2; }
QPushButton:checked { background: #2468d9; color: white; font-weight: bold; }
QPushButton:disabled { background: #e5e5e9; color: #85858e; }
QPushButton#preview { background: #d8e8ff; font-weight: bold; }
QPushButton#start:enabled { background: #148358; color: white; font-weight: bold; }
QPushButton#stop:enabled { background: #bd3c4a; color: white; font-weight: bold; }
QPushButton#save:enabled { background: #2468d9; color: white; font-weight: bold; }
QTabWidget::pane { border: 1px solid #d9d9df; }
QTabBar::tab { background: #ededf1; color: #151515; padding: 9px 16px; }
QTabBar::tab:selected { background: #d8e8ff; }
QCheckBox { color: #151515; padding: 5px; }
QProgressBar { border: 0; background: #e0e8f4; border-radius: 4px; text-align: center; min-height: 18px; }
QProgressBar::chunk { background: #58b99b; border-radius: 4px; }
QLineEdit { background: white; color: #17253d; padding: 5px; border: 1px solid #cbd7e8; border-radius: 4px; }
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
    """Operator configuration, sequence preview, raw records and acquisition."""

    MODES = ("CW ODMR", "Pulsed ODMR", "T1", "T2 echo")

    def __init__(self, demo_mode: bool = False) -> None:
        super().__init__()
        # Keep native spinbox arrows and dialogs readable even on a dark Windows desktop.
        palette = self.palette()
        for role in (QPalette.ColorRole.Text, QPalette.ColorRole.WindowText, QPalette.ColorRole.ButtonText):
            palette.setColor(role, QColor("#17253d"))
        palette.setColor(QPalette.ColorRole.Base, QColor("#ffffff"))
        palette.setColor(QPalette.ColorRole.Button, QColor("#e2eaf5"))
        self.setPalette(palette)
        self.demo = None
        self.acquisition = None
        self.setWindowTitle("NV Lab — stanowisko magnetometru | OFFLINE")
        self.resize(1360, 900)
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
        self.environment = QComboBox()
        self.environment.addItem("Symulator urządzeń", True)
        self.environment.addItem("Stanowisko — sprzęt", False)
        self.environment.setToolTip("Wybór sprzętu nie otwiera połączeń. Połączenie dopiero po START lub teście.")
        header_layout.addWidget(self.environment)
        self.settings_button = QPushButton("Ustawienia")
        self.settings_button.setObjectName("settings")
        self.settings_button.setToolTip("Ustawienia aplikacji — panel w przygotowaniu.")
        header_layout.addWidget(self.settings_button)
        layout.addWidget(header)
        splitter = QSplitter(Qt.Orientation.Vertical)
        body_widget = QWidget()
        body = QHBoxLayout(body_widget)
        body.setContentsMargins(20, 12, 20, 4)
        body.setSpacing(20)
        splitter.addWidget(body_widget)
        self.console = DiagnosticsConsole(self)
        self.console.demo_mode = demo_mode
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
        sequence_page=QWidget()
        sequence_layout=QVBoxLayout(sequence_page);sequence_layout.setContentsMargins(0,0,0,0)
        sequence_toolbar=QHBoxLayout();sequence_toolbar.addStretch()
        self.sequence_autoscale_button=QPushButton('Autoscale')
        self.sequence_autoscale_button.setToolTip('Pokaż cały harmonogram i wszystkie kanały po przybliżeniu wykresu.')
        self.sequence_autoscale_button.clicked.connect(self.autoscale_sequence)
        sequence_toolbar.addWidget(self.sequence_autoscale_button)
        sequence_layout.addLayout(sequence_toolbar);sequence_layout.addWidget(self.sequence_plot,1)
        self.tabs.addTab(sequence_page, "Sekwencja — harmonogram")
        self.waveform_plot = self._plot("Ostatnie surowe odczyty obu faz", "Czas", "s")
        self.waveform_plot.setLabel("left", "Fotodetektor", units="V")
        self.waveform_plot.getAxis("bottom").enableAutoSIPrefix(True)
        self.waveform_plot.addLegend()
        self.tabs.addTab(self.waveform_plot, "Oscyloskop — surowe dane")
        self.help_panel=HelpPanel(self)
        self.tabs.addTab(self.help_panel,'Help · sprzęt')
        left.addWidget(self.tabs, 1)
        self.notice = QLabel("Pomiar OFFLINE · Testy komunikacji dostępne w konsoli poniżej.")
        self.notice.setObjectName("notice")
        self.notice.setWordWrap(True)
        left.addWidget(self.notice)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        left.addWidget(self.progress)
        self.metrics = QLabel("NV LAB · CW ODMR · Wybierz zakres częstotliwości i uruchom pomiar.")
        self.metrics.setWordWrap(True)
        self.metrics.setStyleSheet("color:#405577; padding:6px; font-weight:600;")
        left.addWidget(self.metrics)
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
        self.signal_scale.setToolTip("Zakres wyświetlania surowego przebiegu. Skale sprzętowego oscyloskopu ustaw na panelu urządzenia.")
        self.power = number(-50, -10, -30, "dBm", 1)
        self.frequency = number(2000, 3000, 2870, "MHz", 6)
        common.addRow("Signal Scale", self.signal_scale)
        common.addRow("RF Power", self.power)
        common.addRow("Freq", self.frequency)
        right.addLayout(common)
        self.mode_fields = QStackedWidget()
        right.addWidget(self.mode_fields)
        self.odmr_ranges = []
        for index in range(2):
            page = QWidget()
            fields = QVBoxLayout(page)
            fields.setContentsMargins(0, 0, 0, 0)
            fields.addWidget(section("ODMR"))
            form = QFormLayout()
            low = number(2000, 3000, 2800, "MHz", 6)
            high = number(2000, 3000, 2940, "MHz", 6)
            self.odmr_ranges.append((low, high))
            form.addRow("Freq 1", low)
            form.addRow("Freq 2", high)
            if index == 0:
                low.setValue(2820)
                high.setValue(2920)
                self.cw_points = QSpinBox()
                self.cw_points.setRange(2, 10001)
                self.cw_points.setValue(101)
                self.cw_averages = QSpinBox()
                self.cw_averages.setRange(1, 1000)
                self.cw_averages.setValue(3)
                self.cw_settling = number(0, 10000, 20, "ms", 1)
                self.cw_samples = QSpinBox()
                self.cw_samples.setRange(100, 1000)
                self.cw_samples.setValue(1000)
                form.addRow("Punkty sweepu", self.cw_points)
                form.addRow("Odczyty na punkt", self.cw_averages)
                form.addRow("Czas ustalania", self.cw_settling)
                form.addRow("Próbki / przebieg", self.cw_samples)
                self.cw_reference = QCheckBox("Referencja RF OFF / ON")
                self.cw_reference.setChecked(True)
                form.addRow(self.cw_reference)
            fields.addLayout(form)
            if index == 1:
                pulse = QFormLayout()
                self.pulsed_pi=number(3,1e6,100,"ns",0)
                self.pulsed_points=QSpinBox();self.pulsed_points.setRange(2,1001);self.pulsed_points.setValue(61)
                self.pulsed_averages=QSpinBox();self.pulsed_averages.setRange(1,1024);self.pulsed_averages.setValue(16)
                pulse.addRow("π (do kalibracji)",self.pulsed_pi)
                pulse.addRow("Punkty",self.pulsed_points)
                pulse.addRow("AVER: 1,2,4,8…",self.pulsed_averages)
                fields.addLayout(pulse)
            note = QLabel("CW: laser ciągły, zmiana częstotliwości, świeży odczyt RF OFF/ON. "
                          "Kontrast = (OFF − ON) / OFF. STOP wyłącza RF i bramki." if index == 0 else
                          "Impulsowe ODMR: sweep częstotliwości, cykle bez/z π, trigger D0 → CH1. "
                          "Ustaw czasy i okna; π wymaga kalibracji.")
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
        self.points.setRange(2, 1001)
        self.points.setValue(50)
        self.averages = QSpinBox()
        self.averages.setRange(1, 1024)
        self.averages.setValue(16)
        for box in (self.points, self.averages):
            box.setToolTip("Parametr serii pomiarowej; AVER: potęga 2. Nie zmienia podglądu pojedynczego cyklu.")
        form.addRow("No. points", self.points)
        form.addRow("Averages", self.averages)
        t1.addLayout(form)
        self.reference = QCheckBox("Ref. subtraction")
        self.reference.setChecked(True)
        self.reference.setToolTip("Silnik impulsowy mierzy obie fazy i odejmuje znormalizowane odczyty.")
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
        form.addRow("Guard I/Q", self.delay)
        advanced_layout.addLayout(form)
        self.active_high = QCheckBox("Laser aktywny stanem wysokim")
        self.active_high.setToolTip("Robocza polaryzacja TTL do podglądu; wymaga sprawdzenia w laboratorium.")
        advanced_layout.addWidget(self.active_high)
        t1.addWidget(advanced)
        advanced.hide()
        self.advanced_button.toggled.connect(advanced.setVisible)
        self.mode_fields.addWidget(t1_page)
        echo_page=QWidget()
        echo_layout=QVBoxLayout(echo_page)
        echo_layout.addWidget(section("T2 · echo Hahna"))
        echo_form=QFormLayout();echo_layout.addLayout(echo_form)
        self.echo_pi=number(3,1e6,100,"ns",0)
        self.echo_pi2=number(3,1e6,50,"ns",0)
        self.echo_start=number(0,1e6,5,"µs")
        self.echo_stop=number(0,1e6,200,"µs")
        self.echo_points=QSpinBox();self.echo_points.setRange(2,1001);self.echo_points.setValue(41)
        self.echo_averages=QSpinBox();self.echo_averages.setRange(1,1024);self.echo_averages.setValue(16)
        for label,field in (("π (kalibracja)",self.echo_pi),("π/2 (kalibracja)",self.echo_pi2),
            ("Start t = 2τ",self.echo_start),("Stop t = 2τ",self.echo_stop),
            ("Punkty",self.echo_points),("AVER: 1,2,4,8…",self.echo_averages)):
            echo_form.addRow(label,field)
            field.valueChanged.connect(self.invalidate_preview)
        echo_note=QLabel("π/2 — τ — π — τ — ±π/2. Oś: łączny czas swobodnej ewolucji 2τ, bez impulsów. "
                        "Referencja zmienia fazę ostatniego π/2 o 180°. Wymaga zewnętrznego I/Q i kalibracji obu impulsów.")
        echo_note.setWordWrap(True);echo_layout.addWidget(echo_note);echo_layout.addStretch()
        self.mode_fields.addWidget(echo_page)

        self.preview_button = QPushButton("PODGLĄD SEKWENCJI")
        self.preview_button.setObjectName("preview")
        self.preview_button.clicked.connect(self.show_preview)
        self.feedback = QLabel("Ustaw parametry i wybierz PODGLĄD T1.")
        self.feedback.setObjectName("feedback")
        self.feedback.setWordWrap(True)
        actions = QHBoxLayout()
        self.start_button = QPushButton("START")
        self.stop_button = QPushButton("STOP")
        self.save_button = QPushButton("SAVE")
        self.start_button.setObjectName("start")
        self.stop_button.setObjectName("stop")
        self.save_button.setObjectName("save")
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
        self.pulse_settings_button=QPushButton("Czasy / okna / kalibracja π")
        sidebar.addWidget(self.pulse_settings_button)
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
        logger.info("Interfejs gotowy. Urządzenia łączone tylko na żądanie; bez automatycznego START.")
        if demo_mode:
            from nv_lab.ui.demo import DemoController
            self.demo = DemoController(self)
            self.environment.setEnabled(False)
            self.pulse_settings_button.hide()
            self.mode_buttons[3].hide()
        else:
            from nv_lab.ui.acquisition import CWController
            self.acquisition = CWController(self)
            self.set_mode(0)
        for spin in self.findChildren(QAbstractSpinBox):
            spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)

    def _update_test_status(self, device: str, state: str):
        self.help_panel.diagnostic(device,state,self.demo is not None or bool(self.environment.currentData()))
        if self.demo is not None:
            self.demo.update_status(f"{device}: {state}")
            return
        if self.acquisition is not None:
            self.acquisition._status(f"{'SG386' if device == 'sg386' else 'Oscyloskop'}: {state}")
            return
        self.device_test_status[device] = state
        self.status.setText(
            "○ SYSTEM: POMIAR OFFLINE  │  ○ Pulse Streamer: niepołączony  │  "
            f"SG386: {self.device_test_status['sg386']}  │  "
            f"Oscyloskop: {self.device_test_status['scope']}"
        )

    def closeEvent(self, event):
        if self.acquisition is not None and not self.acquisition.request_close():
            event.ignore()
            return
        if self.demo is not None:
            self.demo.stop()
        self.console.shutdown()
        super().closeEvent(event)

    @staticmethod
    def _plot(title: str, x_label: str, unit: str) -> pg.PlotWidget:
        plot = pg.PlotWidget(background="#ffffff")
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
        if self.acquisition is not None:
            self.waveform_plot.setYRange(-scale_v, scale_v, padding=0)
        else:
            self.measurement_plot.setYRange(-scale_v, scale_v, padding=0)

    def set_mode(self, index: int) -> None:
        self.mode_fields.setCurrentIndex(index)
        for i, button in enumerate(self.mode_buttons):
            button.setChecked(i == index)
        pulsed=index>=1 if self.demo is None else index==2
        self.preview_button.setEnabled(pulsed)
        self.preview_button.setVisible(pulsed)
        self.pulse_settings_button.setVisible(index>=1 and self.demo is None)
        if index != 2:
            self.tabs.setCurrentIndex(0)
        self.tabs.setTabEnabled(1, pulsed)
        self.measurement_plot.setLabel(
            "bottom", "Czas ewolucji" if index >= 2 else "Częstotliwość",
            units="s" if index >= 2 else "Hz",
        )
        self.measurement_plot.getAxis("bottom").enableAutoSIPrefix(True)
        self.invalidate_preview()
        logger.info("Wybrano tryb %s.", self.MODES[index])
        if self.demo is not None:
            self.demo.mode_changed()
        if self.acquisition is not None:
            self.acquisition.mode_changed()

    def invalidate_preview(self, *_args) -> None:
        self.last_sequences = ()
        self.sequence_autoscale_button.setEnabled(False)
        self.sequence_plot.clear()
        self.feedback.setText(
            "Parametry robocze. Wybierz PODGLĄD SEKWENCJI, aby przeliczyć harmonogram."
            if self.mode_fields.currentIndex() >= 1
            else "Wybierz START. Symulator generuje dane syntetyczne; sprzęt wymaga konfiguracji."
        )

    def show_preview(self) -> None:
        """Compile the selected endpoint; never synthesize measurement values."""
        if self.acquisition is not None and self.mode_fields.currentIndex()>=1:
            self.acquisition.preview_pulsed()
            return
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
        self.sequence_autoscale_button.setEnabled(True)
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

    def autoscale_sequence(self):
        if self.last_sequences:
            self.sequence_plot.enableAutoRange(x=True,y=True)
            self.sequence_plot.autoRange(padding=.04)
