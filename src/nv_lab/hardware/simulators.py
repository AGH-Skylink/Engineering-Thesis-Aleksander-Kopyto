"""Stateful stand-ins for the station's instruments; no VISA/network access."""
import logging
import math
import random
from nv_lab.core.odmr import StationConfig, Waveform

logger = logging.getLogger(__name__)


class SimSG386:
    def __init__(self):
        self.frequency_hz = 2.87e9
        self.power_dbm = -30.0
        self.enabled = False
        self.connected = False

    def identify(self):
        self.connected = True
        return "SIMULATED SRS,SG386,SIM386,1.0"

    def configure(self, frequency_hz, power_dbm):
        if not 2e9 <= frequency_hz <= 3e9 or not -50 <= power_dbm <= -10:
            raise ValueError("SG386 SIM: przekroczono limity toru.")
        self.frequency_hz, self.power_dbm = frequency_hz, power_dbm

    def set_output(self, enabled):
        self.enabled = bool(enabled)

    def disable_output(self):
        self.set_output(False)

    def close(self):
        self.disable_output()
        self.connected = False


class SimPulseStreamer:
    def __init__(self, config):
        self.config = config
        self.levels = [0] * 8
        self.analog = [0.0, 0.0]
        self.connected = False
        self.constant(False, False)

    def identify(self):
        self.connected = True
        return "SIMULATED Swabian Pulse Streamer 8/2"

    def constant(self, laser_on, mw_on):
        self.levels = [0] * 8
        self.levels[self.config.laser_channel] = int(self.config.laser_active_high if laser_on
                                                   else not self.config.laser_active_high)
        self.levels[self.config.mw_channel] = int(self.config.mw_active_high if mw_on
                                                else not self.config.mw_active_high)
        self.analog = [0.5 if self.config.sg_iq and mw_on else 0.0, 0.0]

    @property
    def laser_on(self):
        return self.levels[self.config.laser_channel] == int(self.config.laser_active_high)

    @property
    def mw_on(self):
        return self.levels[self.config.mw_channel] == int(self.config.mw_active_high)

    def close(self):
        self.constant(False, False)
        self.connected = False

    def stream_pulsed(self,sequence,repeats):
        self.last_sequence=sequence
        self.repeats=repeats
        self.constant(False,False)

    def has_finished(self):
        return True


class SimLaserGate:
    """Thorlabs external gating path only; model/current control not fabricated."""
    def __init__(self, pulse):
        self.pulse = pulse

    @property
    def enabled(self):
        return self.pulse.laser_on


class SimHMP4040:
    """Four-channel resistive-load simulator; not used to power the actual station."""
    def __init__(self):
        self.voltage = [0.0] * 4
        self.current_limit = [0.1] * 4
        self.enabled = [False] * 4

    def identify(self):
        return "SIMULATED Rohde & Schwarz,HMP4040,SIM4040,1.0"

    def configure(self, channel, voltage, current_limit):
        if type(channel) is not int or not 1 <= channel <= 4:
            raise ValueError("HMP4040: kanał 1…4.")
        if not (math.isfinite(voltage) and math.isfinite(current_limit)
                and 0 <= voltage <= 32 and 0 <= current_limit <= 10):
            raise ValueError("HMP4040: niepoprawne napięcie/prąd.")
        self.voltage[channel - 1] = voltage
        self.current_limit[channel - 1] = current_limit

    def measure(self, channel, resistance_ohm=100.0):
        if not 1 <= channel <= 4 or not math.isfinite(resistance_ohm) or resistance_ohm <= 0:
            raise ValueError("HMP4040: niepoprawny kanał/obciążenie.")
        index = channel - 1
        if not self.enabled[index]:
            return (0.0, 0.0)
        current = min(self.voltage[index] / resistance_ohm, self.current_limit[index])
        return current * resistance_ohm, current

    def close(self):
        self.enabled = [False] * 4


class SimDSOX2014A:
    def __init__(self, config, rf, pulse):
        self.config, self.rf, self.pulse = config, rf, pulse
        self.random = random.Random(config.simulation_seed)
        self.captures = 0
        self.connected = False
        self.points = 1000

    def identify(self):
        self.connected = True
        return "SIMULATED Keysight,DSO-X 2014A,SIM2014,1.0"

    def configure(self, points):
        self.points = points

    def capture(self):
        self.captures += 1
        if self.config.simulation_fail_after and self.captures >= self.config.simulation_fail_after:
            raise TimeoutError("SIM: zadana awaria odczytu oscyloskopu.")
        baseline = 0.070 * (1 + 0.00002 * self.captures)
        if not self.pulse.laser_on:
            baseline = 0.0001
        elif (self.rf.enabled and self.pulse.mw_on and
              (not self.config.sg_iq or math.hypot(*self.pulse.analog) > 0.01)):
            depth = min(0.12, 0.025 * 10 ** ((self.rf.power_dbm + 30) / 40))
            dips = sum(depth / (1 + ((self.rf.frequency_hz - center) / 2.5e6) ** 2)
                       for center in (2.864e9, 2.876e9))
            baseline *= 1 - dips
        samples = [baseline + 0.00005 * math.sin(2 * math.pi * i / 73)
                   + self.random.gauss(0, self.config.simulation_noise_v) for i in range(self.points)]
        return Waveform(samples, 1e-6, metadata={"simulated": True,
                        "channel": self.config.scope_channel, "clipped": False})

    def close(self):
        self.connected = False

    def configure_pulsed(self,config,station_config):
        self.pulsed=config
        self.points=config.waveform_points

    def arm_pulsed(self,stop,timeout_s):
        if stop.is_set():
            from nv_lab.experiments.cw_odmr import Cancelled
            raise Cancelled()

    def read_pulsed(self):
        self.captures+=1
        if self.config.simulation_fail_after and self.captures>=self.config.simulation_fail_after:
            raise TimeoutError("SIM: zadana awaria przebiegu impulsowego.")
        cfg=self.pulsed
        sequence=self.pulse.last_sequence
        dt=cfg.capture_ns*1e-9/self.points
        dip=0
        if cfg.mode=="T2" and self.rf.enabled:
            coherence=.08*math.exp(-(sequence.metadata['tau_ns']/80000)**1.4)
            coherence*=math.sin(math.pi*cfg.pi2_ns/100)**2*math.sin(math.pi*cfg.pi_ns/200)**2
            dip=coherence if sequence.metadata['final_phase_deg']==0 else -coherence
        elif sequence.metadata.get("with_pi") and self.rf.enabled:
            if cfg.mode=="T1":dip=0.12*math.exp(-sequence.metadata["tau_ns"]/350_000)
            else:
                dip=sum(0.1/(1+((self.rf.frequency_hz-center)/2e6)**2) for center in (2.864e9,2.876e9))
            dip*=math.sin(math.pi*cfg.pi_ns/(2*100))**2
        values=[]
        for i in range(self.points):
            after=i*dt-cfg.trigger_lead_ns*1e-9
            level=0.002 if after<0 else 0.002+0.07*(1-dip*math.exp(-after/1e-6))
            values.append(level+self.random.gauss(0,self.config.simulation_noise_v/math.sqrt(cfg.average_count)))
        return Waveform(values,dt,metadata={"simulated":True,"trigger_verified":True,
            "waveform_count":cfg.average_count,"profile":"simulated-legacy-trigger-WORD",
            "model_t1_ns":350000,"model_pi_ns":100,"model_t2_ns":80000})


class SimStation:
    simulated = True

    def __init__(self, config: StationConfig):
        self.config = config
        self.rf = SimSG386()
        self.pulse = SimPulseStreamer(config)
        self.laser = SimLaserGate(self.pulse)
        self.scope = SimDSOX2014A(config, self.rf, self.pulse)
        self.supply = SimHMP4040()
        self.identities = {}

    def open(self):
        self.config.validate()
        self.identities = {"sg386": self.rf.identify(), "pulse_streamer": self.pulse.identify(),
                           "scope": self.scope.identify(), "hmp4040": self.supply.identify(),
                           "laser": "SIMULATED active-low external laser gate; controller model unknown"}
        logger.info("SIM | Połączono symulatory SG386, Pulse Streamer, oscyloskopu i bramki lasera.")

    def shutdown(self):
        errors = []
        for name, action in (("RF OFF", self.rf.disable_output),
                             ("laser/MW OFF", lambda: self.pulse.constant(False, False)),
                             ("scope", self.scope.close), ("RF close", self.rf.close),
                             ("pulse close", self.pulse.close), ("supply close", self.supply.close)):
            try:
                action()
            except Exception as exc:
                errors.append(f"{name}: {exc}")
        return errors
