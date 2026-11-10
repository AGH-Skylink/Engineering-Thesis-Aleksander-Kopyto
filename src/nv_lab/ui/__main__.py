"""Run the offline operator interface: python -m nv_lab.ui."""

import sys


def main() -> int:
    try:
        from PySide6.QtWidgets import QApplication
        from nv_lab.ui.main_window import MainWindow
    except ImportError as exc:
        print(f"Brak zależności GUI: {exc}", file=sys.stderr)
        print('Zainstaluj: python -m pip install -e ".[gui]"', file=sys.stderr)
        return 1

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
