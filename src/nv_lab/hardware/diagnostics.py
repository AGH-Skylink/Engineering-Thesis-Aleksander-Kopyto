"""Read-only VISA discovery and DSO-X 2014A identification check."""

import argparse
from contextlib import closing
import sys


def check_scope(manager, address: str, timeout_ms: int = 5000) -> str:
    with closing(manager.open_resource(address, open_timeout=timeout_ms)) as scope:
        scope.timeout = timeout_ms
        scope.read_termination = "\n"
        scope.write_termination = "\n"
        identity = scope.query("*IDN?").strip()
        print(f"IDN: {identity}", flush=True)
        fields = identity.split(",")
        model = fields[1].replace("-", "").replace(" ", "").upper() if len(fields) > 1 else ""
        if model != "DSOX2014A":
            raise ValueError("Urządzenie nie identyfikuje się jako DSO-X 2014A.")
        return identity


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("list", "scope"))
    parser.add_argument("--address", default="")
    parser.add_argument("--visalib", default="@py")
    args = parser.parse_args()
    if args.action == "scope" and not args.address.strip():
        parser.error("Podaj adres VISA oscyloskopu przez --address.")
    try:
        import pyvisa
        # Empty backend selects the installed native VISA library.
        with closing(pyvisa.ResourceManager(args.visalib)) as manager:
            if args.action == "list":
                resources = manager.list_resources()
                print("Wykryte zasoby VISA (lista nie musi obejmować wszystkich urządzeń):")
                for address in resources:
                    print(address)
                if not resources:
                    print("Brak wykrytych zasobów. Adres TCPIP można wpisać ręcznie.")
                if args.visalib == "@py":
                    print("USB z @py wymaga PyUSB, libusb i zgodnego sterownika USB. "
                          "Alternatywnie wybierz systemowy NI/Keysight VISA.")
            else:
                check_scope(manager, args.address.strip())
                print("OK: DSO-X 2014A odpowiedział na *IDN?. Sesja zamknięta.")
        return 0
    except Exception as exc:
        print(f"Błąd diagnostyki VISA: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
