"""Accept the reported 3034A without accepting arbitrary SCPI instruments."""
import unittest
from unittest.mock import Mock
from nv_lab.hardware.dsox2014a import InfiniiVisionScope,scope_model


class ScopeIdentityTests(unittest.TestCase):
    def test_reported_agilent_3034a_identity_is_accepted_without_writes(self):
        identity='AGILENT TECHNOLOGIES,DSO-X3034A,MY53160630,02.66.2024012316'
        resource=Mock();resource.query.return_value=identity
        scope=InfiniiVisionScope(resource,2)
        self.assertEqual(scope.identify(),identity)
        self.assertEqual(scope.model,'DSOX3034A')
        resource.query.assert_called_once_with('*IDN?')
        resource.write.assert_not_called()

    def test_spacing_vendor_and_model_formats(self):
        for text,expected in (('KEYSIGHT,DSO-X 2014A,SN,1','DSOX2014A'),
            ('Agilent Technologies,DSOX3034A,SN,1','DSOX3034A')):
            with self.subTest(text=text):self.assertEqual(scope_model(text),expected)

    def test_unknown_instrument_is_rejected_without_configuration(self):
        for identity in ('SRS,SG386,SN,1','KEYSIGHT,DSOX9999,SN,1','incomplete'):
            with self.subTest(identity=identity):
                resource=Mock();resource.query.return_value=identity
                with self.assertRaisesRegex(ValueError,'Oczekiwano DSO-X'):
                    InfiniiVisionScope(resource).identify()
                resource.write.assert_not_called()
