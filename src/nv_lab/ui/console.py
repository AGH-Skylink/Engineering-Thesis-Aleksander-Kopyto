"""Application log viewer and asynchronous, read-only connection checks.

AI-assisted implementation; provenance recorded in docs/ETYKA_AI.md.
"""

import codecs
from datetime import datetime
import logging
import sys

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, QTimer, Signal, Slot
from PySide6.QtWidgets import (
    QComboBox, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
    QPushButton, QVBoxLayout, QWidget,
)


class LogBridge(QObject):
    message = Signal(str)


class ConsoleHandler(logging.Handler):
    def __init__(self, bridge: LogBridge):
        super().__init__(logging.INFO)
        self.bridge = bridge
        self.setFormatter(logging.Formatter("%(levelname)s | %(message)s"))

    def emit(self, record):
        self.bridge.message.emit(self.format(record))


class DiagnosticsConsole(QWidget):
    test_status = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(200)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 0, 28, 0)
        heading = QHBoxLayout()
        heading.addWidget(QLabel("Konsola programu / diagnostyka"))
        heading.addStretch()
        self.backend = QComboBox()
        self.backend.addItem("VISA: Python (@py)", "@py")
        self.backend.addItem("VISA: systemowy NI / Keysight", "")
        heading.addWidget(self.backend)
        self.discover_button = QPushButton("Wykryj VISA")
        heading.addWidget(self.discover_button)
        self.cancel_button = QPushButton("Przerwij test")
        self.cancel_button.setEnabled(False)
        heading.addWidget(self.cancel_button)
        clear = QPushButton("Wyczyść logi")
        heading.addWidget(clear)
        layout.addLayout(heading)

        addresses = QGridLayout()
        self.sg_address = QLineEdit("TCPIP0::192.168.0.6::inst0::INSTR")
        self.scope_address = QLineEdit()
        self.scope_address.setPlaceholderText("Pełny adres VISA, np. USB0::…::INSTR")
        self.sg_button = QPushButton("Test SG386")
        self.scope_button = QPushButton("Test oscyloskopu")
        for row, (name, edit, button) in enumerate((
            ("SG386", self.sg_address, self.sg_button),
            ("Oscyloskop", self.scope_address, self.scope_button),
        )):
            addresses.addWidget(QLabel(name), row, 0)
            addresses.addWidget(edit, row, 1)
            addresses.addWidget(button, row, 2)
        addresses.setColumnStretch(1, 1)
        layout.addLayout(addresses)
        self.output = QPlainTextEdit()
        self.output.setReadOnly(True)
        self.output.setMaximumBlockCount(1500)
        self.output.setStyleSheet(
            "QPlainTextEdit { background: #202126; color: #e2e4ec; "
            "font-family: Consolas; font-size: 12px; padding: 6px; }"
        )
        layout.addWidget(self.output, 1)
        clear.clicked.connect(self.output.clear)

        self.process = QProcess(self)
        self.process.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        environment = QProcessEnvironment.systemEnvironment()
        environment.insert("PYTHONIOENCODING", "utf-8")
        self.process.setProcessEnvironment(environment)
        self.process.readyReadStandardOutput.connect(self._read_output)
        self.process.finished.connect(self._finished)
        self.process.errorOccurred.connect(self._process_error)
        self.deadline = QTimer(self)
        self.deadline.setSingleShot(True)
        self.deadline.setInterval(30000)
        self.deadline.timeout.connect(self._timeout)
        self.busy = False
        self.demo_mode = False
        self.demo_timer = QTimer(self)
        self.demo_timer.setSingleShot(True)
        self.demo_timer.setInterval(350)
        self.demo_timer.timeout.connect(self._demo_finished)
        self.task = ""
        self.interrupted = False
        self._buffer = ""
        self._decoder = codecs.getincrementaldecoder("utf-8")("replace")
        self.discover_button.clicked.connect(lambda: self.start_check("list"))
        self.sg_button.clicked.connect(lambda: self.start_check("sg386"))
        self.scope_button.clicked.connect(lambda: self.start_check("scope"))
        self.cancel_button.clicked.connect(self.cancel)

        self.bridge = LogBridge(self)
        self.bridge.message.connect(self.append_message)
        self.handler = ConsoleHandler(self.bridge)
        self.logger = logging.getLogger("nv_lab")
        self.logger.setLevel(logging.INFO)
        self.logger.addHandler(self.handler)
        self.append_message("INFO | Program gotowy. Testy są uruchamiane tylko przyciskiem.")

    @Slot(str)
    def append_message(self, text: str):
        self.output.appendPlainText(f"{datetime.now():%H:%M:%S} | {text}")
        bar = self.output.verticalScrollBar()
        bar.setValue(bar.maximum())

    def start_check(self, task: str):
        if self.busy:
            return
        if self.demo_mode:
            self.task = task
            self._set_busy(True)
            self.append_message(f"DEMO | Symulowany test: {task}. Bez połączenia z aparaturą.")
            self.demo_timer.start()
            return
        address = self.sg_address.text().strip() if task == "sg386" else self.scope_address.text().strip()
        if task != "list" and not address:
            self.append_message("ERROR | Wpisz adres VISA urządzenia przed testem.")
            return
        backend = self.backend.currentData()
        if task == "sg386":
            arguments = ["-u", "-m", "nv_lab.hardware.check_sg386", address, "--timeout", "5"]
            if backend:
                arguments += ["--visalib", backend]
        else:
            arguments = ["-u", "-m", "nv_lab.hardware.diagnostics", task, "--visalib", backend]
            if task == "scope":
                arguments += ["--address", address]
        self.task = task
        self.interrupted = False
        self._buffer = ""
        self._decoder.reset()
        self._set_busy(True)
        self.append_message(
            f"INFO | Start: {task}; backend={backend or 'systemowy'}"
            + (f"; adres={address}." if task != "list" else ".")
        )
        if task != "list":
            self.test_status.emit(task, "test w toku")
        self.process.start(sys.executable, arguments)
        self.deadline.start()

    def _set_busy(self, busy: bool):
        self.busy = busy
        for widget in (self.sg_button, self.scope_button, self.discover_button,
                       self.sg_address, self.scope_address, self.backend):
            widget.setEnabled(not busy)
        if self.demo_mode:
            for widget in (self.sg_address, self.scope_address, self.backend):
                widget.setEnabled(False)
        self.cancel_button.setEnabled(busy)

    def _read_output(self):
        self._buffer += self._decoder.decode(bytes(self.process.readAllStandardOutput()))
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            self.append_message(line.rstrip("\r"))

    def _finished(self, exit_code, exit_status):
        if not self.busy:
            return
        self.deadline.stop()
        self._read_output()
        self._buffer += self._decoder.decode(b"", final=True)
        if self._buffer:
            self.append_message(self._buffer.rstrip("\r"))
        success = (not self.interrupted and exit_code == 0
                   and exit_status == QProcess.ExitStatus.NormalExit)
        if self.task != "list":
            self.test_status.emit(self.task, "test OK (sesja zamknięta)" if success else "test nieudany")
        self.append_message(
            f"{'INFO' if success else 'ERROR'} | Koniec: {self.task}; "
            f"{'OK' if success else 'przerwano' if self.interrupted else 'błąd'} (kod {exit_code})."
        )
        self._set_busy(False)

    def _process_error(self, error):
        if error == QProcess.ProcessError.FailedToStart:
            self.append_message(f"ERROR | Nie można uruchomić testu: {self.process.errorString()}")
            self._finished(-1, QProcess.ExitStatus.CrashExit)

    def cancel(self):
        if self.demo_mode and self.busy:
            self.demo_timer.stop()
            self.append_message("DEMO | Symulowany test przerwany.")
            self._set_busy(False)
            return
        if self.busy:
            self.interrupted = True
            self.append_message("WARNING | Przerywanie testu.")
            self.process.kill()

    def _timeout(self):
        self.append_message("ERROR | Przekroczono limit 30 s całego testu.")
        self.cancel()

    def shutdown(self):
        if self.demo_mode and self.busy:
            self.cancel()
        self.demo_timer.stop()
        self.logger.removeHandler(self.handler)
        self.handler.close()
        self.deadline.stop()
        if self.process.state() != QProcess.ProcessState.NotRunning:
            self.interrupted = True
            self.process.kill()
            self.process.waitForFinished(1500)

    def _demo_finished(self):
        replies = {
            "sg386": "SG386-DEMO: IDN symulowany; FREQ = 2870000000 Hz; AMPR = -30 dBm.",
            "scope": "DSO-X 2014A-DEMO: identyfikacja symulowana; generator próbek gotowy.",
            "list": "Zasoby symulowane: DEMO::SG386, DEMO::DSOX2014A, DEMO::PULSESTREAMER.",
        }
        self.append_message(f"DEMO | {replies[self.task]}")
        if self.task != "list":
            self.test_status.emit(self.task, "symulowany test OK")
        self._set_busy(False)
