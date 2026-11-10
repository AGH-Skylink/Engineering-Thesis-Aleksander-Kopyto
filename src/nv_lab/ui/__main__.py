"""Run the offline operator interface: python -m nv_lab.ui."""

import sys
import argparse


def main() -> int:
    parser = argparse.ArgumentParser(description="NV Lab operator interface")
    parser.add_argument("--demo", action="store_true", help="Symulowany pomiar bez aparatury")
    args = parser.parse_args()
    try:
        from PySide6.QtWidgets import QApplication
        from nv_lab.ui.main_window import MainWindow
    except ImportError as exc:
        print(f"Brak zależności GUI: {exc}", file=sys.stderr)
        print('Zainstaluj: python -m pip install -e ".[gui]"', file=sys.stderr)
        return 1

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow(demo_mode=args.demo)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
