"""Windows executable entry point and bounded, simulation-only build check."""
from contextlib import redirect_stderr, redirect_stdout
import json
import os
from pathlib import Path
import sys
import time
import traceback


DIAGNOSTICS = {"sg386", "scope"}


def main():
    args=sys.argv[1:]
    if args and args[0]=="--diagnostic":
        if len(args)<4 or args[1] not in DIAGNOSTICS or args[2]!="--report":
            return 2
        # A windowed EXE has no stdout. The parent reads this private result file.
        with Path(args[3]).open("w",encoding="utf-8") as stream, redirect_stdout(stream), redirect_stderr(stream):
            sys.argv=[args[1],*args[4:]]
            try:
                if args[1]=="sg386":
                    from nv_lab.hardware.check_sg386 import main as check
                else:
                    from nv_lab.hardware.diagnostics import main as check
                return check()
            except Exception:
                traceback.print_exc()
                return 1
    if args and args[0]=="--smoke-test":
        if len(args)!=2:
            return 2
        return smoke_test(Path(args[1]))
    # Double-clicked executables should save settings/data next to the executable.
    if getattr(sys,"frozen",False):
        os.chdir(Path(sys.executable).resolve().parent)
    # Some dependencies expect file-like streams even in a windowed application.
    for name in ("stdout","stderr"):
        if getattr(sys,name) is None:
            setattr(sys,name,open(os.devnull,"w",encoding="utf-8"))
    from nv_lab.ui.__main__ import main as launch
    return launch()


def smoke_test(directory):
    """Exercise the bundled GUI/engines and imports without touching lab equipment."""
    directory.mkdir(parents=True,exist_ok=True)
    report={"frozen":bool(getattr(sys,"frozen",False)),"simulated":True,"modes":[]}
    window=None
    try:
        # Import dynamic hardware backends as well as simulation code in the EXE.
        import qcodes
        import pyvisa_py
        import pulsestreamer
        import usb
        import libusb_package
        if libusb_package.get_libusb1_backend() is None:
            raise RuntimeError('Bundled libusb backend could not load')
        report['pyusb_version']=usb.__version__
        report['libusb_backend_available']=True
        from nv_lab.hardware.sg386 import SG386
        from PySide6.QtWidgets import QApplication,QAbstractSpinBox
        from PySide6.QtGui import QFontDatabase
        from nv_lab.ui.main_window import MainWindow
        app=QApplication([]);app.setStyle("Fusion")
        if not QFontDatabase.families() and os.name=="nt":
            QFontDatabase.addApplicationFont(str(Path(os.environ['WINDIR'])/'Fonts'/'segoeui.ttf'))
        window=MainWindow();window.show()
        window.acquisition.output_dir=directory/'runs'
        window.cw_points.setValue(3);window.cw_averages.setValue(1);window.cw_settling.setValue(0)
        window.points.setValue(3);window.pulsed_points.setValue(3);window.echo_points.setValue(3)
        for mode in range(4):
            window.set_mode(mode);app.processEvents()
            for spin in window.findChildren(QAbstractSpinBox):
                if spin.isVisible() and spin.lineEdit().width()<50:
                    raise RuntimeError('Numeric edit area is not visible')
            if mode:
                window.show_preview()
                if len(window.last_sequences)!=2:raise RuntimeError('Sequence preview failed')
            window.start_button.click()
            deadline=time.monotonic()+30
            while window.acquisition.worker is not None and time.monotonic()<deadline:
                app.processEvents();time.sleep(.01)
            run=window.acquisition.last_run
            if window.acquisition.worker is not None or run is None or run.state!='COMPLETED' or len(run.points)!=3:
                raise RuntimeError(f'Mode {mode} failed: {getattr(run,"error",None)}')
            if run.storage_errors:raise RuntimeError(str(run.storage_errors))
            report['modes'].append({"mode":window.MODES[mode],"state":run.state,"points":len(run.points)})
        window.tabs.setCurrentIndex(0);app.processEvents()
        window.grab().save(str(directory/'window.png'))
        if len(list((directory/'runs').glob('*.json')))!=4:
            raise RuntimeError('Raw exports missing')
        local_scope=os.environ.get('NV_LAB_SMOKE_SCOPE','')
        if local_scope:
            if not local_scope.startswith('TCPIP0::127.0.0.1::') or not local_scope.endswith('::SOCKET'):
                raise ValueError('Build diagnostics accept a localhost test server only')
            window.environment.setCurrentIndex(1)
            window.console.scope_address.setText(local_scope)
            window.console.scope_button.click()
            deadline=time.monotonic()+40
            while window.console.busy and time.monotonic()<deadline:
                app.processEvents();time.sleep(.01)
            if window.console.busy or 'test OK (sesja zamknięta)' not in window.status.text():
                raise RuntimeError('Bundled GUI diagnostic failed: '+window.console.output.toPlainText())
            report['gui_subprocess_diagnostic']='OK: localhost scope only'
        report['ok']=True
    except Exception:
        report['ok']=False;report['error']=traceback.format_exc()
    finally:
        if window is not None:
            if window.acquisition.worker is not None:
                window.acquisition.stop()
                while window.acquisition.worker is not None:
                    app.processEvents();time.sleep(.01)
            window.close();app.processEvents()
        (directory/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    return 0 if report['ok'] else 1
