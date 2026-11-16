"""Pulse semantics, acquisition failures and scope decoding; no laboratory hardware."""
from dataclasses import replace
from threading import Event
import unittest
from unittest.mock import Mock

from nv_lab.core.odmr import StationConfig
from nv_lab.core.pulsed import PulsedConfig, compile_pulsed, window_means
from nv_lab.experiments.pulsed import run_pulsed
from nv_lab.hardware.simulators import SimStation
from nv_lab.hardware.dsox2014a import DSOX2014A, decode_waveform


class PulseTests(unittest.TestCase):
    def test_echo_has_equal_free_intervals_and_reference_changes_only_final_i_phase(self):
        cfg=replace(PulsedConfig(),mode='T2',start=5000,stop=200000)
        signal=compile_pulsed(cfg,12346,True)
        reference=compile_pulsed(cfg,12346,False)
        intervals=signal.metadata['mw_intervals_ns']
        self.assertEqual(intervals[1][0]-intervals[0][1],6173)
        self.assertEqual(intervals[2][0]-intervals[1][1],6173)
        self.assertEqual([b-a for a,b in intervals],[50,100,50])
        for key in ('laser','mw_gate','scope_trigger','iq_q'):
            self.assertEqual(signal.channels[key],reference.channels[key])
        self.assertNotEqual(signal.channels['iq_i'],reference.channels['iq_i'])
        self.assertIn(-.5,[level for _,level in reference.channels['iq_i']])
        for seq in (signal,reference):
            self.assertEqual(seq.duration_ns%8,0)
            for pattern in seq.channels.values():
                self.assertEqual(sum(dt for dt,_ in pattern),seq.duration_ns)
            for dt,_ in seq.channels['iq_i']:
                self.assertEqual(dt%8,0)

    def test_echo_phase_cycle_simulation_and_iq_requirement(self):
        cfg=replace(PulsedConfig(),mode='T2',start=5000,stop=200000,points=5,settling_s=0)
        result=run_pulsed(SimStation(StationConfig(simulation_noise_v=0)),cfg)
        self.assertEqual(result.state,'COMPLETED',result.error)
        self.assertGreater(result.points[0].difference,10*result.points[-1].difference)
        self.assertEqual(result.document()['units']['x'],'ns')
        self.assertEqual(result.points[0].sequences['phase_180']['metadata']['final_phase_deg'],180)
        with self.assertRaisesRegex(ValueError,'I/Q'):
            run_pulsed(SimStation(StationConfig(sg_iq=False)),cfg)

    def test_reference_reserves_pi_and_all_channels_have_same_duration(self):
        cfg=PulsedConfig()
        signal=compile_pulsed(cfg,123456,True)
        reference=compile_pulsed(cfg,123456,False)
        self.assertEqual(signal.duration_ns,reference.duration_ns)
        self.assertEqual(signal.duration_ns%8,0)
        self.assertEqual(signal.channels['laser'],reference.channels['laser'])
        self.assertEqual(signal.channels['scope_trigger'],reference.channels['scope_trigger'])
        self.assertEqual(signal.metadata['readout_start_ns']-signal.metadata['pi_end_ns'],123456)
        self.assertEqual(signal.channels['laser'][0][1],0)  # active low
        for pattern in signal.channels.values():
            self.assertEqual(sum(dt for dt,_ in pattern),signal.duration_ns)
        for dt,_ in signal.channels['iq_i']:
            self.assertEqual(dt%8,0)

    def test_t1_simulation_decays_and_retains_raw_and_sequences(self):
        station=SimStation(StationConfig(simulation_noise_v=0))
        result=run_pulsed(station,replace(PulsedConfig(),points=5,settling_s=0))
        self.assertEqual(result.state,'COMPLETED',result.error)
        self.assertGreater(result.points[0].difference,5*result.points[-1].difference)
        self.assertEqual(len(result.points[0].signal_trace.samples_v),1000)
        self.assertFalse(result.points[0].sequences['reference']['metadata']['with_pi'])
        self.assertIn('SYNTHETIC',result.document()['provenance'])
        self.assertFalse(station.rf.enabled)
        self.assertFalse(station.pulse.laser_on)

    def test_pulsed_odmr_resonance_and_fault_partial_save(self):
        cfg=replace(PulsedConfig(),mode='PULSED_ODMR',start=2.85e9,stop=2.878e9,points=15,settling_s=0)
        result=run_pulsed(SimStation(StationConfig(simulation_noise_v=0)),cfg)
        self.assertEqual(result.state,'COMPLETED',result.error)
        self.assertGreater(result.points[7].difference,5*result.points[0].difference)
        station=SimStation(StationConfig(simulation_fail_after=4))
        result=run_pulsed(station,cfg)
        self.assertEqual(result.state,'ERROR')
        self.assertEqual(len(result.points),1)
        self.assertFalse(station.rf.enabled)
        self.assertFalse(station.pulse.laser_on)

    def test_stop_and_unverified_hardware_never_opens(self):
        stop=Event()
        station=SimStation(StationConfig())
        result=run_pulsed(station,replace(PulsedConfig(),points=5,settling_s=0),stop,
                          on_point=lambda p: stop.set())
        self.assertEqual(result.state,'STOPPED')
        self.assertEqual(len(result.points),1)
        station.simulated=False
        station.config=replace(station.config,scope_address='unused',wiring_verified=True)
        station.open=Mock()
        with self.assertRaisesRegex(ValueError,'kalibrację'):
            run_pulsed(station,PulsedConfig())
        station.open.assert_not_called()

    def test_windows_reject_missing_baseline_and_zero_reference(self):
        from nv_lab.core.odmr import Waveform
        with self.assertRaisesRegex(ValueError,'próbek'):
            window_means(Waveform([.07]*1000,1e-6),PulsedConfig())
        with self.assertRaisesRegex(ValueError,'zeru'):
            window_means(Waveform([.07]*1000,20e-9),PulsedConfig())


class ScopePulseTests(unittest.TestCase):
    def make_scope(self):
        resource=Mock()
        resource.query.side_effect=lambda cmd:{':TER?':'1',':AER?':'1',':WAV:COUN?':'16',
            ':WAV:PRE?':'1,2,4,16,2e-8,0,0,0.00001,0.001,32768',':SYST:ERR?':'0,"OK"'}[cmd]
        resource.query_binary_values.return_value=[32768,33768,39768,40768]
        scope=DSOX2014A(resource,2)
        scope.pulsed=PulsedConfig()
        return scope,resource

    def test_unsigned_word_uses_actual_preamble(self):
        scope,resource=self.make_scope()
        trace=scope.read_pulsed()
        self.assertAlmostEqual(trace.samples_v[2],.071)
        self.assertTrue(trace.metadata['trigger_verified'])
        self.assertEqual(resource.query_binary_values.call_args.kwargs['datatype'],'H')
        self.assertFalse(resource.query_binary_values.call_args.kwargs['is_big_endian'])

    def test_stale_trigger_and_incomplete_average_rejected(self):
        scope,resource=self.make_scope()
        resource.query.side_effect=lambda cmd:'0'
        with self.assertRaisesRegex(RuntimeError,'świeżego triggera'):
            scope.read_pulsed()
        resource.query.side_effect=lambda cmd:'1' if cmd==':TER?' else '8'
        with self.assertRaisesRegex(RuntimeError,'uśrednianie'):
            scope.read_pulsed()
        resource.query_binary_values.assert_not_called()

    def test_word_ascii_comparison_and_mismatch(self):
        scope,resource=self.make_scope()
        resource.query_ascii_values.return_value=[.001,.011,.071,.081]
        self.assertLess(scope.verify_word_ascii()['max_difference_v'],1e-12)
        resource.query_ascii_values.return_value=[.01]*4
        with self.assertRaisesRegex(ValueError,'skalowanie'):
            scope.verify_word_ascii()
        self.assertEqual(resource.write.call_args.args[0],':WAV:FORM WORD')

    def test_holes_and_clipping_are_detected(self):
        preamble='1,2,3,16,2e-8,0,0,0.00001,0,32768'
        with self.assertRaisesRegex(ValueError,'dziury'):
            decode_waveform(preamble,[32768,0,33768],word=True,averaged=True)
        trace=decode_waveform(preamble,[32768,65280,33768],word=True,averaged=True)
        self.assertTrue(trace.metadata['clipped'])

    def test_arm_waits_until_scope_reports_ready_and_can_stop(self):
        scope,resource=self.make_scope()
        scope.arm_pulsed(Event(),.1)
        writes=[c.args[0] for c in resource.write.call_args_list]
        self.assertLess(writes.index(':ACQ:TYPE NORM'),writes.index(':RUN'))
        stop=Event();stop.set()
        from nv_lab.experiments.cw_odmr import Cancelled
        with self.assertRaises(Cancelled):scope.arm_pulsed(stop,.1)
