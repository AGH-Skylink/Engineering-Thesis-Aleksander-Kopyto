"""Editable, explicitly uncalibrated pulse and integration timing."""
from dataclasses import replace
from PySide6.QtWidgets import (QCheckBox,QDialog,QDialogButtonBox,QDoubleSpinBox,
                              QFormLayout,QLabel,QMessageBox,QVBoxLayout,QAbstractSpinBox)


class PulseSettingsDialog(QDialog):
    def __init__(self,config,parent=None):
        super().__init__(parent)
        self.config=config
        self.setWindowTitle("Czasy i okna — wartości robocze, nie kalibracja")
        self.resize(620,650)
        layout=QVBoxLayout(self)
        note=QLabel("Ze starego kodu: laser 2 ms, trigger 300 ns, guard 500 ns. "
                    "π i zakres τ pochodziły z brakującego PARAMETERS.txt. "
                    "Okna poniżej są jawne i wymagają kontroli na przebiegu. "
                    "τ liczymy od końca π do włączenia lasera odczytu.")
        note.setWordWrap(True);layout.addWidget(note)
        form=QFormLayout();layout.addLayout(form)
        self.fields={}
        for name,label in (("initialization_ns","Inicjalizacja lasera"),("readout_ns","Laser odczytu"),
            ("guard_ns","Guard I/Q przed/po π"),("trigger_lead_ns","Trigger przed laserem ON"),
            ("trigger_ns","Szerokość triggera"),("capture_ns","Zakres czasu oscyloskopu"),
            ("baseline_start_ns","Tło: początek od triggera"),("baseline_stop_ns","Tło: koniec od triggera"),
            ("signal_start_ns","Sygnał: początek od laser ON"),("signal_stop_ns","Sygnał: koniec od laser ON"),
            ("reference_start_ns","Referencja: początek od laser ON"),("reference_stop_ns","Referencja: koniec od laser ON")):
            box=QDoubleSpinBox();box.setDecimals(3);box.setRange(0,1000000)
            box.setSuffix(" µs");box.setValue(getattr(config,name)/1000)
            box.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.NoButtons)
            self.fields[name]=box;form.addRow(label,box)
        self.verified=QCheckBox("Sprawdzono impulsy π/π/2, fazy I/Q, opóźnienia, trigger i okna na stanowisku")
        self.verified.setToolTip("Potwierdzenie operatora dla bieżącego trybu i mocy. Testy symulatora nie zastępują kalibracji.")
        self.verified.setChecked(config.timings_verified)
        for box in self.fields.values():
            box.valueChanged.connect(lambda *_:self.verified.setChecked(False))
        layout.addWidget(self.verified)
        buttons=QDialogButtonBox(QDialogButtonBox.StandardButton.Save|QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept);buttons.rejected.connect(self.reject);layout.addWidget(buttons)

    def accept(self):
        candidate=replace(self.config,**{key:round(box.value()*1000) for key,box in self.fields.items()},
                          timings_verified=self.verified.isChecked())
        try:candidate.validate()
        except ValueError as exc:
            QMessageBox.warning(self,"Niepoprawne okna",str(exc));return
        self.config=candidate
        super().accept()
