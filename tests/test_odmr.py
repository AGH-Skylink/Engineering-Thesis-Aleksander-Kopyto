"""Acquisition, calibration and failure tests without laboratory equipment."""
from dataclasses import replace
import csv
import json
from pathlib import Path
from threading import Event
import tempfile
import unittest
from unittest.mock import Mock

from nv_lab.core.odmr import CWConfig, StationConfig, Waveform
from nv_lab.experiments.cw_odmr import run_cw
from nv_lab.experiments.storage import RunJournal, save_csv, save_run
from nv_lab.hardware.dsox2014a import decode_waveform, DSOX2014A
from nv_lab.hardware.simulators import SimStation, SimHMP4040
from nv_lab.hardware.station import PulseStreamerGate, RealStation
from nv_lab.hardware.hmp4040 import HMP4040Monitor


class CWTests(unittest.TestCase):
    def config(self, **kwargs):
        return replace(CWConfig(points=5, averages=2, settling_s=0, waveform_points=100), **kwargs)

    def assert_outputs_off(self, station):
        self.assertFalse(station.rf.enabled)
        self.assertFalse(station.laser.enabled)
        self.assertFalse(station.pulse.mw_on)
        self.assertEqual(station.pulse.levels[3], 1)
        self.assertEqual(station.pulse.analog, [0, 0])

    def test_paired_sweep_retains_raw_samples_and_reference_normalization(self):
        station = SimStation(StationConfig())
        result = run_cw(station, self.config())
        self.assertEqual(result.state, "COMPLETED")
        self.assertEqual(len(result.points), 5)
        self.assertEqual(station.scope.captures, 20)
        self.assertEqual(result.points[0].frequency_hz, 2.82e9)
        self.assertEqual(result.points[-1].frequency_hz, 2.92e9)
        for point in result.points:
            self.assertEqual(len(point.rf_on), 2)
            self.assertEqual(len(point.rf_off), 2)
            self.assertEqual(len(point.rf_on[0].samples_v), 100)
            self.assertAlmostEqual(point.contrast, (point.reference_v-point.signal_v)/point.reference_v)
        self.assert_outputs_off(station)

    def test_no_reference_mode_and_deterministic_simulator(self):
        results = [run_cw(SimStation(StationConfig()), self.config(reference=False)) for _ in range(2)]
        self.assertEqual(results[0].points, results[1].points)
        self.assertTrue(all(p.reference_v is None and p.contrast is None and p.rf_off == []
                            for p in results[0].points))

    def test_simulated_resonance_requires_laser_and_rf_and_reflects_power(self):
        station = SimStation(StationConfig(simulation_noise_v=0))
        station.scope.configure(100)
        station.rf.configure(2.864e9, -30)
        station.pulse.constant(False, True)
        self.assertLess(sum(station.scope.capture().samples_v)/100, 0.001)
        station.pulse.constant(True, True)
        off = sum(station.scope.capture().samples_v)/100
        station.rf.set_output(True)
        on = sum(station.scope.capture().samples_v)/100
        self.assertLess(on, off)
        station.rf.configure(2.864e9, -10)
        high_power = sum(station.scope.capture().samples_v)/100
        self.assertLess(high_power, on)
        station.pulse.analog = [0,0]
        blanked_iq = sum(station.scope.capture().samples_v)/100
        self.assertGreater(blanked_iq, high_power)

    def test_stop_keeps_completed_point_and_blanks_outputs(self):
        station, stop = SimStation(StationConfig()), Event()
        result = run_cw(station, self.config(), stop, on_point=lambda p: stop.set())
        self.assertEqual(result.state, "STOPPED")
        self.assertEqual(len(result.points), 1)
        self.assert_outputs_off(station)

    def test_stop_before_open_does_not_connect(self):
        station, stop = SimStation(StationConfig()), Event()
        stop.set()
        station.open = Mock(side_effect=AssertionError("must not open"))
        result = run_cw(station, self.config(), stop)
        self.assertEqual(result.state, "STOPPED")
        station.open.assert_not_called()

    def test_timeout_keeps_partial_run_and_blanks_outputs(self):
        station = SimStation(StationConfig(simulation_fail_after=6))
        result = run_cw(station, self.config())
        self.assertEqual(result.state, "ERROR")
        self.assertEqual(len(result.points), 1)
        self.assertIn("TimeoutError", result.error)
        self.assert_outputs_off(station)

    def test_cleanup_runs_after_partial_open_failure_and_each_action_is_attempted(self):
        station = SimStation(StationConfig())
        def bad_open():
            station.rf.enabled = True
            station.pulse.constant(True, True)
            raise ConnectionError("scope missing")
        station.open = bad_open
        result = run_cw(station, self.config())
        self.assertEqual(result.state, "ERROR")
        self.assert_outputs_off(station)
        station = SimStation(StationConfig())
        def bad_disable():
            raise OSError("RF cable disconnected")
        station.rf.disable_output = bad_disable
        result = run_cw(station, self.config())
        self.assertEqual(result.state, "ERROR")
        self.assertTrue(result.cleanup_errors)
        self.assertFalse(station.laser.enabled)
        self.assertFalse(station.scope.connected)

    def test_bad_scope_data_is_not_silently_averaged(self):
        for trace in (Waveform([], 1), Waveform([float('nan')], 1),
                      Waveform([1.0], 1, metadata={"clipped": True}), Waveform([0.0]*100, 1)):
            station = SimStation(StationConfig())
            station.scope.capture = lambda: trace
            result = run_cw(station, self.config())
            self.assertEqual(result.state, "ERROR")
            self.assert_outputs_off(station)

    def test_invalid_configuration_is_rejected_before_hardware_access(self):
        for config in (self.config(points=1), self.config(start_hz=float('nan')),
                       self.config(stop_hz=1e9), self.config(power_dbm=0),
                       self.config(averages=0), self.config(settling_s=-1)):
            station = SimStation(StationConfig())
            station.open = Mock()
            with self.assertRaises(ValueError):
                run_cw(station, config)
            station.open.assert_not_called()
        with self.assertRaises(ValueError):
            StationConfig(laser_channel=1).validate()
        with self.assertRaises(ValueError):
            StationConfig().validate(simulated=False)

    def test_json_csv_and_journal_preserve_provenance_and_partial_state(self):
        station = SimStation(StationConfig(simulation_fail_after=6))
        result = run_cw(station, self.config())
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            save_run(result, path / "run.json")
            doc = json.loads((path/"run.json").read_text(encoding="utf-8"))
            self.assertTrue(doc["simulated"])
            self.assertEqual(doc["state"], "ERROR")
            self.assertEqual(len(doc["points"][0]["rf_on"]), 2)
            save_csv(result, path / "summary.csv")
            with (path/"summary.csv").open(encoding="utf-8-sig") as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]["simulated"], "True")
            journal = RunJournal(path / "partial.jsonl")
            journal.write("point", {"test": 1})
            # A second reader can recover data before close.
            self.assertEqual(json.loads((path/"partial.jsonl").read_text())["data"], {"test": 1})
            journal.close()


class HardwareContractTests(unittest.TestCase):
    def test_byte_preamble_scaling_uses_both_references_and_origins(self):
        trace = decode_waveform("0,0,3,1,0.0001,-0.001,2,0.002,0.05,128", [126,128,130])
        self.assertEqual(trace.samples_v, [0.046,0.05,0.054000000000000006])
        self.assertAlmostEqual(trace.t0_s, -0.0012)
        self.assertEqual(trace.dt_s, 0.0001)

    def test_holes_clipping_bad_headers_and_wrong_lengths(self):
        for header,codes in (("1,0,2,1,1,0,0,1,0,128",[125,128]),
                             ("0,0,2,1,1,0,0,1,0,128",[0,128]),
                             ("0,0,3,1,1,0,0,1,0,128",[125,128])):
            with self.assertRaises(ValueError):
                decode_waveform(header,codes)
        trace=decode_waveform("0,0,2,1,1,0,0,1,0,128",[1,255])
        self.assertTrue(trace.metadata["clipped"])

    def test_scope_requires_new_capture_completion_and_never_resets(self):
        resource = Mock()
        resource.query.side_effect = lambda cmd: {
            "*IDN?":"KEYSIGHT TECHNOLOGIES,DSO-X 2014A,SN,1",":SYST:ERR?":'0,"No error"',
            "*OPC?":"1",":WAV:PRE?":"0,0,3,1,1e-6,0,0,0.001,0,128"}.get(cmd,"1")
        resource.query_binary_values.return_value=[130,131,132]
        scope=DSOX2014A(resource,2)
        scope.identify();scope.configure(100);trace=scope.capture();scope.close()
        commands=[call.args[0] for call in resource.write.call_args_list]
        self.assertIn(":DIG CHAN2",commands)
        self.assertNotIn("*RST",commands)
        self.assertAlmostEqual(trace.samples_v[0],0.002)
        resource.query_binary_values.assert_called_once_with(":WAV:DATA?",datatype="B",container=list,expect_termination=True)

    def test_active_low_gate_and_iq_safe_state(self):
        device=Mock()
        gate=PulseStreamerGate(device,StationConfig())
        gate.constant(True,True)
        device.constant.assert_called_with(([1],0.5,0.0))
        gate.constant(False,False)
        device.constant.assert_called_with(([3],0.0,0.0))
        station=SimStation(StationConfig())
        station.pulse.constant(True,True)
        self.assertEqual(station.pulse.analog,[0.5,0])

    def test_real_cleanup_attempts_rf_and_laser_after_one_failure(self):
        station=RealStation(StationConfig())
        station.rf,station.pulse,station.scope,station.manager=Mock(),Mock(),Mock(),Mock()
        station.rf.disable_output.side_effect=OSError("RF unavailable")
        errors=station.shutdown()
        self.assertEqual(len(errors),1)
        station.pulse.constant.assert_called_once_with(False,False)
        station.scope.close.assert_called_once()
        station.manager.close.assert_called_once()

    def test_hmp_simulated_load_and_laser_gate(self):
        supply=SimHMP4040()
        supply.configure(1,10,0.05)
        self.assertEqual(supply.measure(1),(0,0))
        supply.enabled[0]=True
        self.assertEqual(supply.measure(1,100),(5,0.05))
        supply.close()
        self.assertFalse(any(supply.enabled))

    def test_hmp_monitor_only_reads_values_and_restores_channel(self):
        resource=Mock()
        resource.query.side_effect=lambda cmd:{"*IDN?":"Rohde & Schwarz,HMP4040,SN,1",
            "INST?":"OUT2","MEAS:VOLT?":"5.0","MEAS:CURR?":"0.02"}[cmd]
        monitor=HMP4040Monitor(resource)
        monitor.identify()
        values=monitor.read_channel(1)
        self.assertEqual(values,{"channel":1,"voltage_v":5.0,"current_a":0.02})
        self.assertEqual([c.args[0] for c in resource.write.call_args_list],["INST OUT1","INST OUT2"])
