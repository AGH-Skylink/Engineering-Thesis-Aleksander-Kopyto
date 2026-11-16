"""Explicit pulsed ODMR/T1 timing, windows and raw records.

Defaults from legacy code are starting values, not a station calibration.
"""
from dataclasses import asdict, dataclass, field
import math
from statistics import fmean
from nv_lab.core.sequences import CompiledSequence, _pattern_from_intervals
from nv_lab.core.odmr import Waveform


@dataclass(frozen=True)
class PulsedConfig:
    mode: str = "T1"
    start: float = 100_000  # ns for T1, Hz for pulsed ODMR
    stop: float = 1_000_000
    points: int = 31
    frequency_hz: float = 2.87e9
    power_dbm: float = -30
    pi_ns: int = 100
    pi2_ns: int = 50
    initialization_ns: int = 2_000_000
    readout_ns: int = 2_000_000
    guard_ns: int = 500
    trigger_lead_ns: int = 500
    trigger_ns: int = 300
    average_count: int = 16
    waveform_points: int = 1000
    capture_ns: int = 20_000
    baseline_start_ns: int = 0
    baseline_stop_ns: int = 200
    signal_start_ns: int = 200  # relative to laser readout ON, not trigger
    signal_stop_ns: int = 1200
    reference_start_ns: int = 5000
    reference_stop_ns: int = 15000
    settling_s: float = 0.02
    timings_verified: bool = False

    def validate(self):
        if any(type(getattr(self,key)) is not int for key in ('points','average_count','waveform_points')):
            raise ValueError("Punkty, uśrednienia i liczba próbek muszą być całkowite.")
        if self.mode not in ("T1", "T2", "PULSED_ODMR"):
            raise ValueError("Nieznany tryb impulsowy.")
        if any(not math.isfinite(v) for v in (self.start, self.stop, self.frequency_hz, self.power_dbm,self.settling_s)):
            raise ValueError("Parametry muszą być skończonymi liczbami.")
        if not 2e9 <= self.frequency_hz <= 3e9 or not -50 <= self.power_dbm <= -10:
            raise ValueError("Przekroczono limity częstotliwości/mocy toru.")
        if not self.start < self.stop or self.points < 2 or self.points > 1001:
            raise ValueError("Start musi być mniejszy od Stop; wymagane 2…1001 punktów.")
        if self.mode == "PULSED_ODMR" and not 2e9 <= self.start < self.stop <= 3e9:
            raise ValueError("Zakres Pulsed ODMR: 2000…3000 MHz.")
        if self.mode in ("T1","T2") and self.start < max(self.guard_ns,self.trigger_lead_ns):
            raise ValueError("τ musi być co najmniej tak duże jak czas ochronny/wyprzedzenie triggera.")
        if self.mode=="T2" and (self.start<4*self.guard_ns+32 or self.guard_ns<self.trigger_lead_ns):
            raise ValueError("T2: czas ewolucji ≥4×guard+32 ns; guard przed laserem ≥wyprzedzenie triggera.")
        names = ("pi_ns","pi2_ns","initialization_ns","readout_ns","guard_ns","trigger_lead_ns","trigger_ns",
                 "capture_ns","baseline_stop_ns","signal_stop_ns","reference_stop_ns")
        if any(type(getattr(self,n)) is not int or getattr(self,n)<=0 for n in names):
            raise ValueError("Czasy muszą być dodatnimi całkowitymi ns.")
        if self.pi_ns < 3 or self.pi2_ns<3 or self.trigger_ns < 3 or self.guard_ns < 100:
            raise ValueError("π/trigger ≥3 ns, ochrona I/Q ≥100 ns; wymagana weryfikacja na sprzęcie.")
        if self.trigger_ns > self.trigger_lead_ns+self.readout_ns:
            raise ValueError("Trigger nie mieści się w cyklu odczytu.")
        if not 1 <= self.average_count <= 1024 or self.average_count & (self.average_count-1):
            raise ValueError("Uśrednienia muszą być potęgą 2, z zakresu 1…1024.")
        if not 100 <= self.waveform_points <= 1000 or not 0 <= self.settling_s <= 10:
            raise ValueError("Niepoprawna liczba próbek/czas ustalania.")
        if not 0 <= self.baseline_start_ns < self.baseline_stop_ns < self.trigger_lead_ns:
            raise ValueError("Okno tła musi kończyć się przed laserem ON.")
        if not 0 <= self.signal_start_ns < self.signal_stop_ns <= self.reference_start_ns < self.reference_stop_ns:
            raise ValueError("Okna sygnału i referencji muszą rosnąć i nie nakładać się.")
        if self.trigger_lead_ns+self.reference_stop_ns > self.capture_ns or self.reference_stop_ns > self.readout_ns:
            raise ValueError("Okna integracji nie mieszczą się w odczycie/przebiegu.")
        if self.points*self.waveform_points*2 > 10_000_000:
            raise ValueError("Za dużo surowych próbek.")
        if self.mode in ('T1','T2') and self.stop-self.start < (self.points-1)*(2 if self.mode=='T2' else 1):
            raise ValueError("Za gęsty sweep dla rozdzielczości ns — punkty powtarzałyby się.")

    def axis(self):
        self.validate()
        values=[self.start+(self.stop-self.start)*i/(self.points-1) for i in range(self.points)]
        if self.mode=="T2":
            return [round(v/2)*2 for v in values]
        return [round(v) for v in values] if self.mode=="T1" else values


def compile_pulsed(config, x, with_pi, laser_active_high=False):
    config.validate()
    if config.mode=="T2":
        return compile_echo(config,x,with_pi,laser_active_high)
    tau = int(x) if config.mode == "T1" else config.guard_ns
    if tau < max(config.guard_ns,config.trigger_lead_ns):
        raise ValueError("Za krótkie τ/przerwa przed odczytem.")
    pi_start=config.initialization_ns+config.guard_ns
    pi_end=pi_start+config.pi_ns
    readout_start=pi_end+tau
    trigger_start=readout_start-config.trigger_lead_ns
    # Explicitly pad with safe OFF levels to the hardware's 8 ns cycle boundary.
    unpadded=readout_start+config.readout_ns
    duration=((unpadded+7)//8)*8
    laser_on=int(laser_active_high)
    channels={
        "laser":_pattern_from_intervals(duration,[(0,config.initialization_ns),(readout_start,unpadded)],1-laser_on,laser_on),
        "mw_gate":_pattern_from_intervals(duration,[(pi_start,pi_end)] if with_pi else [],0,1),
        "scope_trigger":_pattern_from_intervals(duration,[(trigger_start,trigger_start+config.trigger_ns)],0,1),
    }
    # I/Q guard copied in intent from legacy: prepare analog I before the digital MW gate.
    i_start=(config.initialization_ns//8)*8
    i_end=min(((pi_end+config.guard_ns+7)//8)*8,(readout_start//8)*8)
    analog=_pattern_from_intervals(duration,[(i_start,i_end)] if with_pi else [],0,1)
    channels["iq_i"]=[(dt,0.5*level) for dt,level in analog]
    channels["iq_q"]=[(duration,0.0)]
    return CompiledSequence(duration,channels,{"mode":config.mode,"x":x,"with_pi":with_pi,
        "tau_ns":tau,"pi_start_ns":pi_start,"pi_end_ns":pi_end,"readout_start_ns":readout_start,
        "trigger_start_ns":trigger_start,"padding_ns":duration-unpadded,
        "laser_active_high":laser_active_high,"timing_origin":"explicit init → guard → π slot → τ → readout"})


def compile_echo(config,x,signal_phase,laser_active_high=False):
    """Hahn echo; x=total free evolution, final π/2 phase cycle 0°/180°."""
    half=round(x/2)
    first=config.initialization_ns+config.guard_ns
    middle=first+config.pi2_ns+half
    last=middle+config.pi_ns+half
    end=last+config.pi2_ns
    readout=end+config.guard_ns
    unpadded=readout+config.readout_ns
    duration=((unpadded+7)//8)*8
    on=int(laser_active_high)
    early_end=((middle+config.pi_ns+config.guard_ns+7)//8)*8
    final_start=((last-config.guard_ns)//8)*8
    if early_end>final_start:
        raise ValueError("T2: za mała przerwa na zmianę fazy I/Q.")
    final_end=min(((end+config.guard_ns+7)//8)*8,(readout//8)*8)
    analog=[];cursor=0
    for start,stop,level in ((config.initialization_ns//8*8,early_end,.5),
        (final_start,final_end,.5 if signal_phase else -.5)):
        if start>cursor:analog.append((start-cursor,0.0))
        if stop>start:analog.append((stop-start,level))
        cursor=stop
    if cursor<duration:analog.append((duration-cursor,0.0))
    channels={
        "laser":_pattern_from_intervals(duration,[(0,config.initialization_ns),(readout,unpadded)],1-on,on),
        "mw_gate":_pattern_from_intervals(duration,[(first,first+config.pi2_ns),
            (middle,middle+config.pi_ns),(last,end)],0,1),
        "scope_trigger":_pattern_from_intervals(duration,[(readout-config.trigger_lead_ns,
            readout-config.trigger_lead_ns+config.trigger_ns)],0,1),
        "iq_i":analog,"iq_q":[(duration,0.0)]}
    return CompiledSequence(duration,channels,{"mode":"T2","x":2*half,"tau_ns":2*half,
        "half_evolution_ns":half,"final_phase_deg":0 if signal_phase else 180,
        "readout_start_ns":readout,"trigger_start_ns":readout-config.trigger_lead_ns,
        "mw_intervals_ns":[[first,first+config.pi2_ns],[middle,middle+config.pi_ns],[last,end]],
        "padding_ns":duration-unpadded,"laser_active_high":laser_active_high,
        "timing_origin":"Hahn echo; x=total free evolution excluding pulses"})


def window_means(trace: Waveform, config):
    trace.validate()
    def mean_in(start_ns,stop_ns):
        values=[v for i,v in enumerate(trace.samples_v)
                if start_ns*1e-9 <= trace.t0_s+i*trace.dt_s < stop_ns*1e-9]
        if len(values)<3:
            raise ValueError("Za mało próbek w oknie integracji. Skróć zakres czasu lub zwiększ próbkowanie.")
        return fmean(values)
    baseline=mean_in(config.baseline_start_ns,config.baseline_stop_ns)
    signal=mean_in(config.trigger_lead_ns+config.signal_start_ns,config.trigger_lead_ns+config.signal_stop_ns)
    reference=mean_in(config.trigger_lead_ns+config.reference_start_ns,config.trigger_lead_ns+config.reference_stop_ns)
    if abs(reference-baseline)<1e-9:
        raise ValueError("Referencja po odjęciu tła jest bliska zeru.")
    return {"baseline_v":baseline,"signal_v":signal,"reference_v":reference,
            "ratio":(signal-baseline)/(reference-baseline)}


@dataclass
class PulsedPoint:
    index: int
    x: float
    frequency_hz: float
    reference_ratio: float
    signal_ratio: float
    difference: float
    reference_windows: dict
    signal_windows: dict
    reference_trace: Waveform
    signal_trace: Waveform
    sequences: dict


@dataclass
class PulsedRun:
    run_id: str
    simulated: bool
    config: dict
    station: dict
    started_utc: str
    state: str="RUNNING"
    ended_utc: str | None=None
    error: str | None=None
    identities: dict=field(default_factory=dict)
    cleanup_errors: list[str]=field(default_factory=list)
    storage_errors: list[str]=field(default_factory=list)
    points: list[PulsedPoint]=field(default_factory=list)

    def document(self):
        return {"schema":"nv-lab.pulsed.v1","provenance":"SYNTHETIC SIMULATION — NOT AN EXPERIMENT"
                if self.simulated else "HARDWARE ACQUISITION — REQUIRES LAB VALIDATION",
                "units":{"x":"Hz" if self.config["mode"]=="PULSED_ODMR" else "ns","voltage":"V","time":"s"},**asdict(self)}
