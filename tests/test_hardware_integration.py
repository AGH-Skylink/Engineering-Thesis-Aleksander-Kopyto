"""Exercise actual PyVISA/QCoDeS adapters against local SCPI servers, never lab devices."""
from contextlib import contextmanager
import importlib.util
import socketserver
import threading
import struct
import unittest
from unittest.mock import patch

from nv_lab.core.odmr import CWConfig, StationConfig
from nv_lab.experiments.cw_odmr import run_cw
from nv_lab.hardware.station import RealStation

AVAILABLE = all(importlib.util.find_spec(name) for name in ("pyvisa_py", "qcodes", "pulsestreamer"))


@contextmanager
def scpi_station(bad_scope=False,pulsed=False,scope_model='DSO-X3034A'):
    state = {"frequency": 2.87e9, "power": -30.0, "rf": 0, "modulation": 0,
             "type": 0, "qfnc": 0, "sg_commands": [], "scope_commands": [], "pulse_states": []}
    state['stream_records']=[]

    class RFHandler(socketserver.StreamRequestHandler):
        def handle(self):
            for line in self.rfile:
                command = line.decode().strip()
                state["sg_commands"].append(command)
                upper = command.upper()
                key = {"FREQ": "frequency", "AMPR": "power", "ENBR": "rf",
                       "MODL": "modulation", "TYPE": "type", "QFNC": "qfnc"}.get(upper.split()[0].rstrip("?"))
                if upper == "*IDN?":
                    reply = "Stanford Research Systems,SG386,LOCALTEST,1.0"
                elif upper.endswith("?"):
                    reply = str(state[key]) if key else "0"
                else:
                    if key:
                        value = float(command.split()[1])
                        state[key] = value if key in ("frequency", "power") else int(value)
                    continue
                self.wfile.write(reply.encode() + b"\n")

    class ScopeHandler(socketserver.StreamRequestHandler):
        def handle(self):
            for line in self.rfile:
                command = line.decode().strip().upper()
                state["scope_commands"].append(command)
                if command == "*IDN?":
                    reply = "UNKNOWN,WRONGMODEL,SN,1" if bad_scope else f"AGILENT TECHNOLOGIES,{scope_model},LOCALTEST,1"
                elif command == ":WAV:PRE?":
                    reply = "1,2,1000,16,2e-8,0,0,0.00001,0,32768" if pulsed else "0,0,100,1,1e-6,0,0,0.001,0,128"
                elif command == ":WAV:COUN?":
                    reply = "16" if pulsed else "1"
                elif command == ":WAV:DATA?":
                    # 70 mV OFF, 68 mV ON. IEEE block header and newline are real bytes.
                    data = bytes([196 if state["rf"] else 198]) * 100
                    if pulsed:
                        has_pi=any(level for _,level in state['sequence'].getDigital()[1][0])
                        values=[200 if i<25 else (6500 if has_pi and i<85 else 7200) for i in range(1000)]
                        data=struct.pack('<1000H',*[32768+v for v in values])
                    length = str(len(data)).encode()
                    self.wfile.write(b"#" + str(len(length)).encode() + length + data + b"\n")
                    continue
                elif command == ":SYST:ERR?":
                    reply = '0,"No error"'
                elif command.endswith("?"):
                    reply = "1"
                else:
                    continue
                self.wfile.write(reply.encode() + b"\n")

    class Server(socketserver.ThreadingTCPServer):
        daemon_threads = True

    class FakePulse:
        def __init__(self, address):
            pass
        def constant(self, outputs):
            state["pulse_states"].append(outputs)
        def getSerial(self):
            return "LOCALTEST"
        def getFirmwareVersion(self):
            return "2.1"
        def setSquareWave125MHz(self, channels):
            assert channels == []
        def createSequence(self):
            from pulsestreamer import Sequence
            return Sequence()
        def setTrigger(self,start,rearm):
            state['trigger']=(start,rearm)
        def stream(self,sequence,repeats,final):
            state['stream_records'].append(sequence)
            state['sequence']=sequence
            state['repeats']=repeats
            state['final']=final
        def hasFinished(self):
            return True

    with Server(("127.0.0.1", 0), RFHandler) as rf, Server(("127.0.0.1", 0), ScopeHandler) as scope:
        threads = [threading.Thread(target=lambda s=s: s.serve_forever(poll_interval=0.01), daemon=True)
                   for s in (rf, scope)]
        for thread in threads:
            thread.start()
        config = StationConfig(sg_address=f"TCPIP0::127.0.0.1::{rf.server_address[1]}::SOCKET",
                               scope_address=f"TCPIP0::127.0.0.1::{scope.server_address[1]}::SOCKET",
                               pulse_address="local-test-no-network", wiring_verified=True)
        try:
            yield config, state, FakePulse
        finally:
            rf.shutdown(); scope.shutdown()
            for thread in threads:
                thread.join(2)


@unittest.skipUnless(AVAILABLE, "Install [hardware] to test real adapters against local servers")
class AdapterIntegrationTests(unittest.TestCase):
    def test_2014a_remains_supported_with_shared_capture_profile(self):
        with scpi_station(scope_model='DSO-X 2014A') as (config,state,pulse):
            with patch('pulsestreamer.PulseStreamer',pulse):
                result=run_cw(RealStation(config),CWConfig(points=2,averages=1,waveform_points=100,settling_s=0))
            self.assertEqual(result.state,'COMPLETED',result.error)
            self.assertEqual(result.points[0].rf_on[0].metadata['scope_model'],'DSOX2014A')
    def test_echo_real_adapters_send_opposite_i_phases_with_identical_digital_timing(self):
        from nv_lab.core.pulsed import PulsedConfig
        from nv_lab.experiments.pulsed import run_pulsed
        from dataclasses import replace
        with scpi_station(pulsed=True) as (config,state,pulse):
            with patch('pulsestreamer.PulseStreamer',pulse):
                result=run_pulsed(RealStation(config),replace(PulsedConfig(),mode='T2',start=5000,
                    stop=200000,points=2,settling_s=0,timings_verified=True))
            self.assertEqual(result.state,'COMPLETED',(result.error,result.cleanup_errors))
            reference,signal=state['stream_records'][:2]
            self.assertTrue(any(level<0 for _,level in reference.getAnalog()[0][0]))
            self.assertFalse(any(level<0 for _,level in signal.getAnalog()[0][0]))
            self.assertEqual(reference.getDigital()[1][0],signal.getDigital()[1][0])
            self.assertEqual(state['rf'],0)

    def test_actual_word_visa_and_vendor_sequence_for_pulsed_engine(self):
        from nv_lab.core.pulsed import PulsedConfig
        from nv_lab.experiments.pulsed import run_pulsed
        from dataclasses import replace
        with scpi_station(pulsed=True) as (config,state,pulse):
            with patch('pulsestreamer.PulseStreamer',pulse):
                result=run_pulsed(RealStation(config),replace(PulsedConfig(),points=2,
                    settling_s=0,timings_verified=True))
            self.assertEqual(result.state,'COMPLETED',(result.error,result.cleanup_errors))
            self.assertEqual(len(result.points),2)
            self.assertGreater(result.points[0].difference,.05)
            self.assertEqual(state['repeats'],18)
            self.assertEqual(state['final'],([3],0,0))
            self.assertIn(':WAV:FORM WORD',state['scope_commands'])
            self.assertIn(':WAV:UNS 1',state['scope_commands'])
            self.assertEqual(state['scope_commands'].count(':RUN'),4)
            self.assertEqual(state['rf'],0)
            self.assertEqual(state['pulse_states'][-1],([3],0,0))

    def test_actual_visa_driver_sweep_and_iq_cleanup(self):
        with scpi_station() as (config, state, pulse):
            with patch("pulsestreamer.PulseStreamer", pulse):
                result = run_cw(RealStation(config), CWConfig(points=3, averages=1,
                                      waveform_points=100, settling_s=0))
            self.assertEqual(result.state, "COMPLETED", (result.error, result.cleanup_errors))
            self.assertEqual(len(result.points), 3)
            self.assertEqual(result.points[0].rf_on[0].metadata['scope_model'],'DSOX3034A')
            self.assertAlmostEqual(result.points[0].signal_v, 0.068)
            self.assertAlmostEqual(result.points[0].reference_v, 0.070)
            self.assertAlmostEqual(result.points[0].contrast, 2/70)
            self.assertIn("TYPE 6", state["sg_commands"])
            self.assertIn("QFNC 5", state["sg_commands"])
            self.assertIn("MODL 1", state["sg_commands"])
            self.assertEqual(state["rf"], 0)
            self.assertEqual(state["pulse_states"][-1], ([3], 0, 0))
            self.assertNotIn("*RST", state["sg_commands"] + state["scope_commands"])
            self.assertEqual(state["scope_commands"].count(":DIG CHAN2"), 6)

    def test_wrong_scope_model_stops_before_acquisition_and_blanks_outputs(self):
        with scpi_station(bad_scope=True) as (config, state, pulse):
            with patch("pulsestreamer.PulseStreamer", pulse):
                result = run_cw(RealStation(config), CWConfig(points=3, averages=1,
                                       waveform_points=100, settling_s=0))
            self.assertEqual(result.state, "ERROR")
            self.assertIn("Oczekiwano DSO-X", result.error)
            self.assertEqual(state["rf"], 0)
            self.assertEqual(state["pulse_states"][-1], ([3], 0, 0))
            self.assertEqual(state["scope_commands"], ["*IDN?"])
