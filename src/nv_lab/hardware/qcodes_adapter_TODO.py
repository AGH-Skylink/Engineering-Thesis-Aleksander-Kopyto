"""QCoDeS integration plan, not an implemented QCoDeS driver.

1) Confirm installed QCoDeS version and existing upstream instrument drivers.
2) Wrap tested SG386 functions in Parameters (frequency/power/enable).
3) Wrap scope readout in a measurement backend (trace + scaling metadata).
4) Register parameters and write datasets with Measurement/DataSaver.
5) Test with dummy instruments and controlled lab limits.
"""
