"""Optional HMP4040 monitor. No output-enable or setpoint commands are exposed.

R&S HMP Series manual v05, sections 8.2 and 8.9. Not part of CW activation.
"""
import math


class HMP4040Monitor:
    def __init__(self, resource):
        self.resource = resource
        self.resource.read_termination = "\n"
        self.resource.write_termination = "\n"

    def identify(self):
        identity = self.resource.query("*IDN?").strip()
        fields = identity.split(",")
        if len(fields) < 2 or "HMP4040" not in fields[1].upper():
            raise ValueError(f"Oczekiwano HMP4040, otrzymano: {identity}")
        return identity

    def read_channel(self, channel):
        if type(channel) is not int or not 1 <= channel <= 4:
            raise ValueError("HMP4040: kanał 1…4.")
        selected = self.resource.query("INST?").strip().strip('"')
        if selected.upper() not in ("OUT1", "OUT2", "OUT3", "OUT4"):
            raise ValueError("HMP4040: nie rozpoznano aktualnie wybranego kanału.")
        try:
            self.resource.write(f"INST OUT{channel}")
            voltage = float(self.resource.query("MEAS:VOLT?"))
            current = float(self.resource.query("MEAS:CURR?"))
            if not math.isfinite(voltage) or not math.isfinite(current):
                raise ValueError("HMP4040: niepoprawny odczyt.")
            return {"channel": channel, "voltage_v": voltage, "current_a": current}
        finally:
            self.resource.write(f"INST {selected.upper()}")

    def close(self):
        self.resource.close()
