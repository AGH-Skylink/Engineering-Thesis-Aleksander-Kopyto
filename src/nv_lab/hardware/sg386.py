import pyvisa
from qcodes.instrument import VisaInstrument
from qcodes.validators import Numbers, Ints, Enum

class SG386(VisaInstrument):
    """ Sterownik do generatora SG386, po sieci lokalnej"""

    def __init__(self, name: str, address: str, **kwargs):
        super().__init__(name=name, address=address, terminator="\n", **kwargs)

        #czestotliwosc
        self.add_parameter(
            "freq",
            label="Frequency",
            unit="Hz",
            get_cmd="FREQ?",
            set_cmd="FREQ {:.3f}",
            get_parser=float,
            vals=Numbers(2e9, 3e9) #ograniczamy zakres do mozliwosci toru pomiarowego
        )

        self.add_parameter(
            "power",
            label="Power",
            unit="dBm",
            get_cmd="AMPR?",
            set_cmd="AMPR {:.1f}",
            get_parser=float,
            vals=Numbers(-50, -10) #ograniczamy zakres do mozliwosci toru pomiarowego
        )