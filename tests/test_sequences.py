import sys
from pathlib import Path
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from nv_lab.core.sequences import T1Settings, compile_t1

class SequenceTests(unittest.TestCase):
    def test_all_channels_have_equal_total_duration(self):
        for pi in [False, True]:
            seq = compile_t1(T1Settings(), with_pi=pi)
            for pattern in seq.channels.values():
                self.assertEqual(sum(dt for dt, _ in pattern), seq.duration_ns)

    def test_reference_has_no_microwave_pulse(self):
        seq = compile_t1(T1Settings(), with_pi=False)
        self.assertEqual(sum(dt for dt, lvl in seq.channels['mw_gate'] if lvl), 0)

    def test_pi_pulse_length(self):
        cfg = T1Settings(pi_pulse_ns=120)
        seq = compile_t1(cfg, with_pi=True)
        self.assertEqual(sum(dt for dt, lvl in seq.channels['mw_gate'] if lvl),120)

    def test_paired_cycles_same_duration(self):
        cfg = T1Settings(tau_ns=10_000)
        self.assertEqual(compile_t1(cfg,False).duration_ns,compile_t1(cfg,True).duration_ns)

    def test_invalid_settings_rejected(self):
        with self.assertRaises(ValueError):
            compile_t1(T1Settings(tau_ns=-1),True)
        with self.assertRaises(ValueError):
            compile_t1(T1Settings(pi_pulse_ns=100, tau_ns=50),True)

    def test_active_low_laser(self):
        seq=compile_t1(T1Settings(laser_active_high=False),True)
        self.assertEqual(seq.channels['laser'][0][1],0)
        self.assertEqual(seq.channels['laser'][1][1],1)

if __name__ == '__main__': unittest.main()
