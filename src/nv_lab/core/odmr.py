"""CW ODMR configuration, calibrated waveforms and acquisition records.

AI-assisted implementation; provenance and verification: docs/ETYKA_AI.md.
"""
from dataclasses import asdict, dataclass, field
import math


@dataclass(frozen=True)
class CWConfig:
    start_hz: float = 2.82e9
    stop_hz: float = 2.92e9
    points: int = 101
    power_dbm: float = -30.0
    averages: int = 3
    settling_s: float = 0.02
    waveform_points: int = 1000
    reference: bool = True

    def validate(self):
        for name in ("start_hz", "stop_hz", "power_dbm", "settling_s"):
            value = getattr(self, name)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
                raise ValueError(f"{name}: wymagana skończona liczba.")
        if type(self.reference) is not bool:
            raise ValueError("reference musi być wartością logiczną.")
        if not 2e9 <= self.start_hz < self.stop_hz <= 3e9:
            raise ValueError("Zakres częstotliwości musi rosnąć i mieścić się w 2000–3000 MHz.")
        if not -50 <= self.power_dbm <= -10:
            raise ValueError("Moc toru musi mieścić się w -50…-10 dBm.")
        for name, low, high in (("points", 2, 10001), ("averages", 1, 1000),
                                ("waveform_points", 100, 1000)):
            value = getattr(self, name)
            if type(value) is not int or not low <= value <= high:
                raise ValueError(f"{name}: wymagana liczba całkowita {low}…{high}.")
        if not 0 <= self.settling_s <= 10:
            raise ValueError("Czas ustalania musi mieścić się w 0…10 s.")
        if self.points * self.averages * self.waveform_points * (2 if self.reference else 1) > 10_000_000:
            raise ValueError("Za dużo surowych próbek (>10 mln). Zmniejsz punkty/uśrednienia/długość przebiegu.")

    def frequencies(self):
        self.validate()
        return [self.start_hz + i * (self.stop_hz - self.start_hz) / (self.points - 1)
                for i in range(self.points)]


@dataclass(frozen=True)
class StationConfig:
    backend: str = "@py"
    sg_address: str = "TCPIP0::192.168.0.6::inst0::INSTR"
    scope_address: str = "USB0::0x0957::0x17A4::MY53160630::INSTR"  # historical v6 station
    pulse_address: str = "192.168.0.5"
    scope_channel: int = 2
    scope_trigger_channel: int = 1
    trigger_channel: int = 0
    laser_channel: int = 3
    mw_channel: int = 1
    laser_active_high: bool = False
    mw_active_high: bool = True
    sg_iq: bool = True
    timeout_s: float = 5.0
    wiring_verified: bool = False
    simulation_seed: int = 386
    simulation_noise_v: float = 0.0003
    simulation_fail_after: int = 0

    def validate(self, simulated=True):
        for name in ("backend", "sg_address", "scope_address", "pulse_address"):
            if not isinstance(getattr(self, name), str):
                raise ValueError(f"{name}: wymagana wartość tekstowa.")
        for name in ("laser_active_high", "mw_active_high", "sg_iq", "wiring_verified"):
            if type(getattr(self, name)) is not bool:
                raise ValueError(f"{name}: wymagana wartość logiczna.")
        if type(self.scope_channel) is not int or self.scope_channel not in (1, 2, 3, 4):
            raise ValueError("Kanał oscyloskopu: 1…4.")
        if self.scope_trigger_channel not in (1,2,3,4) or self.scope_trigger_channel==self.scope_channel:
            raise ValueError("Trigger oscyloskopu musi używać innego kanału niż fotodetektor.")
        if self.trigger_channel not in range(8) or self.trigger_channel in (self.laser_channel,self.mw_channel):
            raise ValueError("Trigger Pulse Streamera musi używać osobnego kanału D0…D7.")
        if any(type(c) is not int or not 0 <= c <= 7 for c in (self.laser_channel, self.mw_channel)):
            raise ValueError("Kanały Pulse Streamera: D0…D7.")
        if self.laser_channel == self.mw_channel:
            raise ValueError("Laser i bramka MW muszą używać różnych kanałów.")
        if not math.isfinite(self.timeout_s) or not 0.5 <= self.timeout_s <= 30:
            raise ValueError("Timeout połączenia: 0.5…30 s.")
        if not math.isfinite(self.simulation_noise_v) or not 0 <= self.simulation_noise_v <= 0.1:
            raise ValueError("Szum symulatora musi mieścić się w 0…0.1 V.")
        if type(self.simulation_fail_after) is not int or self.simulation_fail_after < 0:
            raise ValueError("Numer odczytu awarii musi być nieujemną liczbą całkowitą.")
        if type(self.simulation_seed) is not int or not 0 <= self.simulation_seed <= 2_000_000_000:
            raise ValueError("Niepoprawne ziarno generatora symulacji.")
        if not simulated:
            if not all(s.strip() for s in (self.sg_address, self.scope_address, self.pulse_address)):
                raise ValueError("Uzupełnij adresy generatora, oscyloskopu i Pulse Streamera.")
            if not self.wiring_verified:
                raise ValueError("W ustawieniach potwierdź sprawdzenie mapowania TTL i skal oscyloskopu.")


@dataclass
class Waveform:
    samples_v: list[float]
    dt_s: float
    t0_s: float = 0.0
    metadata: dict = field(default_factory=dict)

    def validate(self):
        if not self.samples_v or not all(math.isfinite(v) for v in self.samples_v):
            raise ValueError("Pusty lub niepoprawny przebieg z oscyloskopu.")
        if not math.isfinite(self.dt_s) or self.dt_s <= 0 or not math.isfinite(self.t0_s):
            raise ValueError("Niepoprawna podstawa czasu przebiegu.")


@dataclass
class ODMRPoint:
    index: int
    frequency_hz: float
    signal_v: float
    reference_v: float | None
    contrast: float | None
    signal_sem_v: float
    reference_sem_v: float | None
    rf_on: list[Waveform]
    rf_off: list[Waveform]


@dataclass
class ODMRRun:
    run_id: str
    simulated: bool
    config: dict
    station: dict
    started_utc: str
    state: str = "RUNNING"
    ended_utc: str | None = None
    error: str | None = None
    identities: dict = field(default_factory=dict)
    cleanup_errors: list[str] = field(default_factory=list)
    storage_errors: list[str] = field(default_factory=list)
    points: list[ODMRPoint] = field(default_factory=list)

    def document(self):
        return {"schema": "nv-lab.cw-odmr.v1", "units": {
            "frequency": "Hz", "voltage": "V", "time": "s", "contrast": "fraction"
        }, "provenance": "SYNTHETIC SIMULATION — NOT AN EXPERIMENT" if self.simulated
           else "HARDWARE ACQUISITION — REQUIRES LAB VALIDATION", **asdict(self)}
