"""Read-only connection check using the SG386 QCoDeS driver."""

import argparse
import math
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("address", help="Instrument IP/hostname or full VISA address")
    parser.add_argument("--visalib", default=None, help="VISA backend, e.g. @py")
    parser.add_argument("--timeout", type=float, default=5.0, help="Timeout in seconds")
    args = parser.parse_args()
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error("--timeout must be a finite positive number")

    try:
        from nv_lab.hardware.sg386 import SG386
    except ImportError as exc:
        print(f"Missing hardware dependency: {exc}", file=sys.stderr)
        print('Install with: python -m pip install -e ".[hardware]"', file=sys.stderr)
        return 1

    address = args.address
    if "::" not in address:
        address = f"TCPIP0::{address}::5025::SOCKET"
    print(f"Connecting to {address}")
    instrument = None
    try:
        instrument = SG386(
            "sg386_connection_check",
            address,
            visalib=args.visalib,
            timeout=args.timeout,
            device_clear=False,
        )
        identity = instrument.ask("*IDN?").strip()
        print(f"IDN: {identity}")
        fields = identity.split(",")
        if len(fields) < 2 or fields[1].strip().upper() != "SG386":
            raise ValueError("The instrument did not identify itself as an SG386")
        print(f"Frequency: {instrument.freq.get()} Hz")
        print(f"Power: {instrument.power.get()} dBm")
        print("OK: SG386 communication verified (queries only).")
        return 0
    except Exception as exc:
        print(f"SG386 connection check failed: {exc}", file=sys.stderr)
        return 1
    finally:
        if instrument is not None:
            instrument.close()


if __name__ == "__main__":
    raise SystemExit(main())
