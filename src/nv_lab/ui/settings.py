"""Explicit connection and channel settings; opening this dialog never contacts hardware."""
from dataclasses import replace
from pathlib import Path

from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox,
    QDoubleSpinBox, QFormLayout, QLabel, QLineEdit, QMessageBox, QSpinBox,
    QTabWidget, QVBoxLayout, QWidget, QAbstractSpinBox)


class SettingsDialog(QDialog):
    def __init__(self, config, output_dir, parent=None):
        super().__init__(parent)
        self.config = config
        self.output_dir = output_dir
        self.setWindowTitle("Ustawienia stanowiska NV Lab")
        self.resize(640, 580)
        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs)
        connections = QWidget()
        form = QFormLayout(connections)
        self.backend = QComboBox()
        self.backend.addItem("Python VISA (@py) — TCP/IP", "@py")
        self.backend.addItem("NI / Keysight VISA — systemowy", "")
        self.backend.setCurrentIndex(0 if config.backend else 1)
        form.addRow("Biblioteka VISA", self.backend)
        self.sg = QLineEdit(config.sg_address)
        self.scope = QLineEdit(config.scope_address)
        self.scope.setPlaceholderText("USB0::…::INSTR lub TCPIP0::…::INSTR")
        self.pulse = QLineEdit(config.pulse_address)
        form.addRow("SRS SG386", self.sg)
        form.addRow("Oscyloskop DSO-X 2014A", self.scope)
        form.addRow("Pulse Streamer — IP", self.pulse)
        self.timeout = QDoubleSpinBox()
        self.timeout.setRange(0.5, 30)
        self.timeout.setValue(config.timeout_s)
        self.timeout.setSuffix(" s")
        form.addRow("Timeout VISA", self.timeout)
        self.directory = QLineEdit(str(output_dir))
        form.addRow("Katalog automatycznego zapisu", self.directory)
        note = QLabel("USB wymaga NI/Keysight VISA lub skonfigurowanego PyUSB/libusb. "
                      "Klient Pulse Streamera ma własny timeout HTTP 10 s. "
                      "HMP4040 nie jest wymagany do CW ODMR i nie jest włączany automatycznie.")
        note.setWordWrap(True)
        form.addRow(note)
        tabs.addTab(connections, "Połączenia i dane")

        mapping = QWidget()
        form = QFormLayout(mapping)
        self.channel = QSpinBox()
        self.channel.setRange(1, 4)
        self.channel.setValue(config.scope_channel)
        form.addRow("Fotodetektor — CH", self.channel)
        self.trigger_channel=QSpinBox();self.trigger_channel.setRange(1,4)
        self.trigger_channel.setValue(config.scope_trigger_channel)
        form.addRow("Trigger oscyloskopu — CH",self.trigger_channel)
        self.trigger_digital=QSpinBox();self.trigger_digital.setRange(0,7)
        self.trigger_digital.setValue(config.trigger_channel)
        form.addRow("Trigger z Pulse Streamera — D",self.trigger_digital)
        self.laser = QSpinBox()
        self.laser.setRange(0, 7)
        self.laser.setValue(config.laser_channel)
        self.mw = QSpinBox()
        self.mw.setRange(0, 7)
        self.mw.setValue(config.mw_channel)
        form.addRow("Laser — kanał D", self.laser)
        form.addRow("Bramka MW — kanał D", self.mw)
        self.laser_high = QCheckBox("Laser ON = HIGH (domyślnie ON = LOW)")
        self.laser_high.setChecked(config.laser_active_high)
        self.mw_high = QCheckBox("Bramka MW ON = HIGH")
        self.mw_high.setChecked(config.mw_active_high)
        self.iq = QCheckBox("Zewnętrzne I/Q: A0 = 0,5 V przy MW ON, A1 = 0 V")
        self.iq.setChecked(config.sg_iq)
        form.addRow(self.laser_high)
        form.addRow(self.mw_high)
        form.addRow(self.iq)
        self.verified = QCheckBox("Mapowanie TTL, polaryzacja i skale oscyloskopu sprawdzone na stanowisku")
        self.verified.setChecked(config.wiring_verified)
        form.addRow(self.verified)
        note = QLabel("Dane ze starego kodu: laser D3 (ON=0), MW D1 (ON=1), "
                      "sygnał CH2, trigger CH1. CW korzysta z AUTO trigger, bez impulsu D0. "
                      "Nieużywane wyjścia cyfrowe i Q są zerowane. "
                      "Przy STOP laser dostaje poziom OFF, RF jest wyłączane. "
                      "Nie zmieniamy prądu nieustalonego kontrolera lasera.")
        note.setWordWrap(True)
        form.addRow(note)
        tabs.addTab(mapping, "Kanały / I/Q")

        simulation = QWidget()
        form = QFormLayout(simulation)
        self.seed = QSpinBox()
        self.seed.setRange(0, 2_000_000_000)
        self.seed.setValue(config.simulation_seed)
        self.noise = QDoubleSpinBox()
        self.noise.setDecimals(4)
        self.noise.setRange(0, 100)
        self.noise.setSuffix(" mV")
        self.noise.setValue(config.simulation_noise_v * 1000)
        self.failure = QSpinBox()
        self.failure.setRange(0, 1000000)
        self.failure.setSpecialValueText("Bez awarii")
        self.failure.setValue(config.simulation_fail_after)
        form.addRow("Ziarno losowania", self.seed)
        form.addRow("Szum pojedynczej próbki", self.noise)
        form.addRow("Awaria od odczytu nr", self.failure)
        note = QLabel("Symulatory zachowują stan RF, bramki lasera, wyjść Pulse Streamera "
                      "i oscyloskopu. Awaria sprawdza STOP, zapis częściowy oraz cleanup. "
                      "Krzywa jest syntetyczna, nie stanowi modelu skalibrowanego stanowiska.")
        note.setWordWrap(True)
        form.addRow(note)
        tabs.addTab(simulation, "Symulator / awarie")
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        for spin in self.findChildren(QAbstractSpinBox):
            spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)

    def accept(self):
        config = replace(self.config, backend=self.backend.currentData(), sg_address=self.sg.text().strip(),
            scope_address=self.scope.text().strip(), pulse_address=self.pulse.text().strip(),
            timeout_s=self.timeout.value(), scope_channel=self.channel.value(),
            scope_trigger_channel=self.trigger_channel.value(),trigger_channel=self.trigger_digital.value(),
            laser_channel=self.laser.value(), mw_channel=self.mw.value(),
            laser_active_high=self.laser_high.isChecked(), mw_active_high=self.mw_high.isChecked(),
            sg_iq=self.iq.isChecked(), wiring_verified=self.verified.isChecked(),
            simulation_seed=self.seed.value(), simulation_noise_v=self.noise.value() / 1000,
            simulation_fail_after=self.failure.value())
        try:
            config.validate()
            if not self.directory.text().strip():
                raise ValueError("Podaj katalog zapisu danych.")
        except ValueError as exc:
            QMessageBox.warning(self, "Niepoprawne ustawienia", str(exc))
            return
        self.config = config
        self.output_dir = Path(self.directory.text()).expanduser().resolve()
        super().accept()
