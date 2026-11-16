"""Real CW station; lazy dependencies, no hardware access at module import."""
from uuid import uuid4
from nv_lab.hardware.dsox2014a import DSOX2014A


class PulseStreamerGate:
    def __init__(self, device, config):
        self.device, self.config = device, config

    def constant(self, laser_on, mw_on):
        levels = {
            self.config.laser_channel: self.config.laser_active_high if laser_on else not self.config.laser_active_high,
            self.config.mw_channel: self.config.mw_active_high if mw_on else not self.config.mw_active_high,
        }
        # Legacy path: external I/Q, I=A0=0.5 V when MW is ON, Q=A1=0 V.
        i_voltage = 0.5 if self.config.sg_iq and mw_on else 0.0
        self.device.constant(([channel for channel, high in levels.items() if high], i_voltage, 0.0))

    def close(self):
        self.constant(False, False)

    def stream_pulsed(self, sequence, repeats):
        from pulsestreamer import TriggerStart, TriggerRearm
        seq=self.device.createSequence()
        mapping={"laser":self.config.laser_channel,"mw_gate":self.config.mw_channel,
                 "scope_trigger":self.config.trigger_channel}
        for name,channel in mapping.items():
            pattern=sequence.channels[name]
            if name=="mw_gate" and not self.config.mw_active_high:
                pattern=[(dt,1-level) for dt,level in pattern]
            seq.setDigital(channel,pattern)
        for channel,name in ((0,"iq_i"),(1,"iq_q")):
            seq.setAnalog(channel,sequence.channels[name] if self.config.sg_iq else [(sequence.duration_ns,0)])
        self.device.setTrigger(TriggerStart.IMMEDIATE,TriggerRearm.MANUAL)
        final_high=[]
        if not self.config.laser_active_high:final_high.append(self.config.laser_channel)
        if not self.config.mw_active_high:final_high.append(self.config.mw_channel)
        self.device.stream(seq,repeats,final=(final_high,0,0))

    def has_finished(self):
        return self.device.hasFinished()


class RealStation:
    simulated = False

    def __init__(self, config):
        self.config = config
        self.manager = self.rf = self.scope = self.pulse = None
        self.identities = {}
        self.open_attempted = False

    def open(self):
        self.config.validate(simulated=False)
        self.open_attempted = True
        import pyvisa
        from pulsestreamer import PulseStreamer
        from nv_lab.hardware.sg386 import SG386
        timeout_ms = round(self.config.timeout_s * 1000)
        self.manager = pyvisa.ResourceManager(self.config.backend)
        address = self.config.sg_address.strip()
        if "::" not in address:
            address = f"TCPIP0::{address}::5025::SOCKET"
        resource = self.manager.open_resource(address, open_timeout=timeout_ms)
        try:
            resource.read_termination = resource.write_termination = "\n"
            resource.timeout = timeout_ms
            identity = resource.query("*IDN?").strip()
            if len(identity.split(",")) < 2 or identity.split(",")[1].strip().upper() != "SG386":
                raise ValueError(f"To nie jest SG386: {identity}")
            self.rf = SG386(f"sg386_{uuid4().hex}", resource=resource,
                            timeout=self.config.timeout_s, device_clear=False)
        except Exception:
            resource.close()
            raise
        self.identities["sg386"] = identity
        self.rf.cw_iq_mode = self.config.sg_iq
        self.rf.disable_output()
        # Bind the gate before identification so shutdown can blank a partially opened PS.
        # Vendor 2.1 client has a fixed 10 s HTTP timeout; no timeout constructor argument.
        device = PulseStreamer(self.config.pulse_address.strip())
        self.pulse = PulseStreamerGate(device, self.config)
        device.setSquareWave125MHz([])
        self.pulse.constant(False, False)
        self.identities["pulse_streamer"] = {
            "serial": device.getSerial(), "firmware": device.getFirmwareVersion()}
        resource = self.manager.open_resource(self.config.scope_address.strip(), open_timeout=timeout_ms)
        resource.timeout = timeout_ms
        self.scope = DSOX2014A(resource, self.config.scope_channel)
        self.identities["scope"] = self.scope.identify()
        self.identities["laser"] = "External TTL gate; model not identified, no laser-current API"

    def shutdown(self):
        errors = []
        if self.open_attempted:
            if self.rf is None:
                errors.append("Brak połączenia SG386 — nie potwierdzono RF OFF.")
            if self.pulse is None:
                errors.append("Brak połączenia Pulse Streamera — nie potwierdzono laser/MW OFF.")
        actions = []
        if self.rf is not None:
            actions.append(("SG386 RF OFF", self.rf.disable_output))
        if self.pulse is not None:
            actions.append(("Laser OFF / MW gate OFF", lambda: self.pulse.constant(False, False)))
        for name, device in (("scope", self.scope), ("SG386", self.rf), ("VISA", self.manager)):
            if device is not None:
                actions.append((f"close {name}", device.close))
        for name, action in actions:
            try:
                action()
            except Exception as exc:
                errors.append(f"{name}: {exc}")
        return errors
