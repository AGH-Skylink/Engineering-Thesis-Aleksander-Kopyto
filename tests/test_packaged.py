"""Frozen entry dispatch must run diagnostics without opening another GUI."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from nv_lab.packaged import main


class PackagedEntryTests(unittest.TestCase):
    def test_diagnostic_arguments_and_output_are_preserved(self):
        with tempfile.TemporaryDirectory() as folder:
            report=Path(folder)/'result.txt'
            args=['NVLab.exe','--diagnostic','sg386','--report',str(report),
                  'TCPIP0::127.0.0.1::1234::SOCKET','--visalib','@py']
            def check():
                self.assertEqual(sys.argv[1:],args[5:])
                print('IDN: LOCAL TEST')
                return 0
            with patch.object(sys,'argv',args),patch('nv_lab.hardware.check_sg386.main',side_effect=check):
                self.assertEqual(main(),0)
            self.assertIn('IDN: LOCAL TEST',report.read_text(encoding='utf-8'))

    def test_worker_exception_is_reported_and_returns_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            report=Path(folder)/'result.txt'
            args=['NVLab.exe','--diagnostic','scope','--report',str(report),'list']
            with patch.object(sys,'argv',args),patch('nv_lab.hardware.diagnostics.main',side_effect=RuntimeError('test failure')):
                self.assertEqual(main(),1)
            self.assertIn('test failure',report.read_text(encoding='utf-8'))

    def test_unknown_worker_is_rejected(self):
        with patch.object(sys,'argv',['NVLab.exe','--diagnostic','unknown','--report','unused']):
            self.assertEqual(main(),2)
