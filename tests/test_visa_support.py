"""Keep missing USB dependencies distinct from device/network failures."""
import sys
import unittest
from unittest.mock import patch
from nv_lab.hardware.visa_support import connection_error


class VisaAdviceTests(unittest.TestCase):
    def test_missing_pyusb_explains_installation_in_python_interpreter(self):
        error=ValueError("Please install PyUSB to use this resource type. No module named 'usb'")
        text=connection_error(error,'USB0::TEST::INSTR','@py')
        self.assertIn('python -m pip install pyusb libusb-package',text)
        self.assertIn('systemowy NI / Keysight',text)

    def test_frozen_program_does_not_suggest_pip_to_repair_exe(self):
        with patch.object(sys,'frozen',True,create=True):
            text=connection_error(ValueError('No backend available'),'USB0::TEST::INSTR','@py')
        self.assertIn('aktualnego NVLab.exe',text)
        self.assertNotIn('python -m pip install',text)

    def test_non_usb_native_and_other_errors_keep_original_diagnosis(self):
        error=ValueError('No backend available')
        self.assertEqual(connection_error(error,'TCPIP0::localhost::INSTR','@py'),str(error))
        self.assertEqual(connection_error(error,'USB0::TEST::INSTR',''),str(error))
        self.assertEqual(connection_error(ValueError('timeout'),'USB0::TEST::INSTR','@py'),'timeout')
