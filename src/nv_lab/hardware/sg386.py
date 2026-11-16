import pyvisa
from qcodes.instrument import VisaInstrument
from qcodes.validators import Numbers, Ints, Enum

class SG386(VisaInstrument):
    """ Sterownik do generatora SG386, po sieci lokalnej"""

    def __init__(self, name: str, address: str | None = None, **kwargs):
        super().__init__(name=name, address=address, terminator="\n", **kwargs)

        #czestotliwosc
        self.add_parameter(
            "freq",
            label="Frequency",
            unit="Hz",
            get_cmd="FREQ?",
            set_cmd="FREQ {:.3f}",
            get_parser=float,
            vals=Numbers(2e9, 3e9) #ograniczamy zakres do mozliwosci toru pomiarowego
        )

        self.add_parameter(
            "power",
            label="Power",
            unit="dBm",
            get_cmd="AMPR?",
            set_cmd="AMPR {:.1f}",
            get_parser=float,
            vals=Numbers(-50, -10) #ograniczamy zakres do mozliwosci toru pomiarowego
        )

    def identify(self):
        identity = self.ask("*IDN?").strip()
        fields = identity.split(",")
        if len(fields) < 2 or fields[1].strip().upper() != "SG386":
            raise ValueError(f"Oczekiwano SG386, otrzymano: {identity}")
        return identity

    def configure(self, frequency_hz, power_dbm):
        self.freq.validate(frequency_hz)
        self.power.validate(power_dbm)
        iq = bool(getattr(self, "cw_iq_mode", False))
        if iq:
            self.write("TYPE 6")
            self.write("QFNC 5")
        self.write(f"MODL {int(iq)}")
        self.freq.set(frequency_hz)
        self.power.set(power_dbm)
        if abs(self.freq.get() - frequency_hz) > 1:
            raise RuntimeError("SG386: odczyt częstotliwości nie zgadza się z żądaniem.")
        if abs(self.power.get() - power_dbm) > 0.11:
            raise RuntimeError("SG386: odczyt mocy nie zgadza się z żądaniem.")
        if self.ask("MODL?").strip() != str(int(iq)):
            raise RuntimeError("SG386: nie potwierdzono ustawienia modulacji.")
        if iq and (self.ask("TYPE?").strip() != "6" or self.ask("QFNC?").strip() != "5"):
            raise RuntimeError("SG386: nie potwierdzono zewnętrznego I/Q.")

    def set_output(self, enabled):
        expected = int(bool(enabled))
        self.write(f"ENBR {expected}")
        if int(self.ask("ENBR?").strip()) != expected:
            raise RuntimeError("SG386: nie potwierdzono stanu wyjścia RF.")

    def disable_output(self):
        self.set_output(False)
