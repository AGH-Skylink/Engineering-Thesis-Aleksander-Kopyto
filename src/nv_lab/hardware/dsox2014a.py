"""InfiniiVision DSO-X 2014A/3034A captures and preamble calibration.

Keysight 2000 X-Series Programmer's Guide: pp. 177, 737, 744–745, 755.
"""
import math
import time
from nv_lab.core.odmr import Waveform

SUPPORTED_MODELS={'DSOX2014A':'DSO-X 2014A','DSOX3034A':'DSO-X 3034A'}


def scope_model(identity):
    fields=identity.strip().split(',')
    model=fields[1].replace(' ','').replace('-','').upper() if len(fields)>1 else ''
    if model not in SUPPORTED_MODELS:
        raise ValueError('Urządzenie nie identyfikuje się jako obsługiwany oscyloskop. '
            f'Oczekiwano DSO-X 2014A lub DSO-X 3034A, otrzymano: {identity}')
    return model


def decode_waveform(preamble: str, codes, channel=1, word=False, averaged=False):
    fields = [float(v) for v in preamble.strip().split(",")]
    if len(fields) != 10 or not all(math.isfinite(v) for v in fields):
        raise ValueError("Oscyloskop: niepoprawna preambuła (oczekiwano 10 liczb).")
    form, kind, count, avg, dx, x0, xr, dy, y0, yr = fields
    if form != int(word) or kind not in ((0,2,3) if averaged else (0,)):
        raise ValueError("Oscyloskop: format/typ preambuły nie odpowiada żądanej akwizycji.")
    if len(codes) != int(count) or not codes or not 0 < dx or not 0 < dy:
        raise ValueError("Oscyloskop: niezgodna liczba próbek lub skala.")
    if any(type(v) is not int or not 0 <= v <= (65535 if word else 255) for v in codes):
        raise ValueError("Niepoprawne próbki unsigned BYTE/WORD.")
    # Per manual, 0 is a hole, 1 clipped low, 255 clipped high. Never average holes.
    if 0 in codes:
        raise ValueError("Oscyloskop zwrócił dziury (kod 0). Sprawdź akwizycję i konfigurację czasu.")
    trace = Waveform([(v - yr) * dy + y0 for v in codes], dx, x0 - xr * dx,
                     {"preamble": fields, "channel": channel,
                      "clipped": any(v in ((256,65280) if word else (1,255)) for v in codes),
                      "simulated": False})
    trace.validate()
    return trace


class InfiniiVisionScope:
    def __init__(self, resource, channel=1):
        self.resource, self.channel = resource, channel
        self.identified = False
        self.model = None
        resource.read_termination = "\n"
        resource.write_termination = "\n"
        resource.chunk_size = 1024 * 1024

    def identify(self):
        identity = self.resource.query("*IDN?").strip()
        self.model=scope_model(identity)
        self.identified = True
        return identity

    def configure(self, points):
        if self.channel not in (1, 2, 3, 4):
            raise ValueError("Oscyloskop: kanał 1…4.")
        # Operator sets probe/vertical scale/time range before the scan. No autoscale/reset.
        for command in (f":CHAN{self.channel}:DISP 1", f":CHAN{self.channel}:COUP DC",
                        ":TIM:MODE MAIN", ":TRIG:SWE AUTO", ":ACQ:TYPE NORM",
                        f":WAV:SOUR CHAN{self.channel}", ":WAV:FORM BYTE", ":WAV:UNS 1",
                        ":WAV:POIN:MODE NORM", f":WAV:POIN {points}"):
            self.resource.write(command)
        error = self.resource.query(":SYST:ERR?").strip()
        if int(error.split(",")[0]) != 0:
            raise RuntimeError(f"Oscyloskop zgłasza błąd konfiguracji: {error}")
        self.setup = {key: self.resource.query(command).strip() for key, command in (
            ("probe", f":CHAN{self.channel}:PROB?"), ("range_v", f":CHAN{self.channel}:RANG?"),
            ("offset_v", f":CHAN{self.channel}:OFFS?"), ("time_range_s", ":TIM:RANG?"))}

    def capture(self):
        self.resource.write(f":DIG CHAN{self.channel}")
        if self.resource.query("*OPC?").strip() != "1":
            raise RuntimeError("Oscyloskop nie potwierdził zakończenia świeżej akwizycji.")
        preamble = self.resource.query(":WAV:PRE?")
        codes = self.resource.query_binary_values(":WAV:DATA?", datatype="B", container=list,
                                                  expect_termination=True)
        trace = decode_waveform(preamble, codes, self.channel)
        trace.metadata["setup"] = dict(self.setup)
        trace.metadata['scope_model']=self.model
        return trace

    def close(self):
        try:
            if self.identified:
                self.resource.write(":STOP")
        finally:
            self.resource.close()

    def configure_pulsed(self, config, station_config):
        self.pulsed=config
        # Proven legacy acquisition profile: external CH1 trigger, CH2 signal, AVER, WORD/LSBF.
        for command in (":STOP",f":CHAN{self.channel}:DISP 1",f":CHAN{self.channel}:COUP DC",
                        ":TIM:MODE MAIN",":TRIG:MODE EDGE", ":TRIG:SWE NORM",
                        f":TRIG:EDGE:SOUR CHAN{station_config.scope_trigger_channel}",
                        ":TRIG:EDGE:SLOP POS",":TRIG:EDGE:LEV 0.25",":TIM:REF LEFT",
                        ":TIM:DEL 0",f":TIM:RANG {config.capture_ns*1e-9:.12g}",
                        ":ACQ:TYPE NORM",f":WAV:SOUR CHAN{self.channel}",":WAV:FORM WORD",
                        ":WAV:BYT LSBF",":WAV:UNS 1",":WAV:POIN:MODE NORM",
                        f":WAV:POIN {config.waveform_points}"):
            self.resource.write(command)
        if config.average_count>1:
            self.resource.write(":ACQ:TYPE AVER")
            self.resource.write(f":ACQ:COUN {config.average_count}")
        error=self.resource.query(":SYST:ERR?").strip()
        if int(error.split(",")[0]):
            raise RuntimeError(f"Oscyloskop: błąd konfiguracji impulsowej: {error}")

    def arm_pulsed(self, stop, timeout_s):
        self.resource.write(":STOP")
        # Switching acquisition type discards the previous average before every phase.
        self.resource.write(":ACQ:TYPE NORM")
        if self.pulsed.average_count>1:
            self.resource.write(":ACQ:TYPE AVER")
            self.resource.write(f":ACQ:COUN {self.pulsed.average_count}")
        self.resource.query(":TER?")
        self.resource.query(":AER?")
        self.resource.write(":RUN")
        deadline=time.monotonic()+timeout_s
        while time.monotonic()<deadline:
            if stop.is_set():
                from nv_lab.experiments.cw_odmr import Cancelled
                raise Cancelled()
            if self.resource.query(":AER?").strip()=="1":
                return
            stop.wait(0.01)
        raise TimeoutError("Oscyloskop nie potwierdził uzbrojenia triggera CH1.")

    def read_pulsed(self):
        self.resource.write(":STOP")
        if self.resource.query(":TER?").strip()!="1":
            raise RuntimeError("Brak świeżego triggera — nie używam starego przebiegu.")
        count=int(self.resource.query(":WAV:COUN?").strip())
        if count<self.pulsed.average_count:
            raise RuntimeError(f"Niepełne uśrednianie: {count}/{self.pulsed.average_count}.")
        preamble=self.resource.query(":WAV:PRE?")
        codes=self.resource.query_binary_values(":WAV:DATA?",datatype="H",is_big_endian=False,container=list,
                                               expect_termination=True)
        trace=decode_waveform(preamble,codes,self.channel,word=True,averaged=self.pulsed.average_count>1)
        if trace.metadata["clipped"]:
            raise ValueError("Obcięty przebieg WORD — popraw skalę/offset oscyloskopu.")
        trace.metadata.update({"profile":"legacy-trigger-WORD-LSBF-preamble","trigger_verified":True,
                               "waveform_count":count,"scope_model":self.model})
        return trace

    def verify_word_ascii(self):
        """Compare two encodings of the same stopped record; no fabricated voltage scale."""
        self.resource.write(":STOP")
        for command in (f":WAV:SOUR CHAN{self.channel}",":WAV:FORM WORD",":WAV:BYT LSBF",":WAV:UNS 1",
                        ":WAV:POIN:MODE NORM",":WAV:POIN 1000"):
            self.resource.write(command)
        preamble=self.resource.query(":WAV:PRE?")
        codes=self.resource.query_binary_values(":WAV:DATA?",datatype="H",is_big_endian=False,
                                               container=list,expect_termination=True)
        trace=decode_waveform(preamble,codes,self.channel,word=True,averaged=True)
        if trace.metadata['clipped']:
            raise ValueError("WORD/ASCII: obcięty przebieg; popraw skalę oscyloskopu.")
        try:
            self.resource.write(":WAV:FORM ASC")
            ascii_values=self.resource.query_ascii_values(":WAV:DATA?",container=list)
        finally:
            self.resource.write(":WAV:FORM WORD")
        if len(ascii_values)!=len(trace.samples_v):
            raise ValueError("WORD/ASCII: różne liczby próbek.")
        if not all(math.isfinite(v) for v in ascii_values):
            raise ValueError("WORD/ASCII: niepoprawne wartości ASCII.")
        error=max(abs(a-b) for a,b in zip(ascii_values,trace.samples_v))
        tolerance=abs(trace.metadata["preamble"][7])*2+1e-7
        if not math.isfinite(error) or error>tolerance:
            raise ValueError(f"WORD/ASCII: niezgodne skalowanie ({error:g} V > {tolerance:g} V).")
        return {"max_difference_v":error,"tolerance_v":tolerance,"samples":len(ascii_values)}


# Preserve imports used by older scripts; both models use the verified shared profile.
DSOX2014A=InfiniiVisionScope
