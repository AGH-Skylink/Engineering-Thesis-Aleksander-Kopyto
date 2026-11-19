"""Connection advice without switching backends or changing Windows USB drivers."""
import sys


def connection_error(error,address,backend):
    detail=str(error)
    usb_python=address.upper().startswith('USB') and backend=='@py'
    if not usb_python:
        return detail
    lowered=detail.lower()
    missing_pyusb='install pyusb' in lowered or "no module named 'usb'" in lowered
    missing_backend=any(value in lowered for value in ('no backend available','suitable backend',
                                                      'pyusb does not seem to be properly installed'))
    if not (missing_pyusb or missing_backend):
        return detail
    what='Brakuje PyUSB (modułu usb)' if missing_pyusb else 'Brakuje działającej biblioteki libusb dla PyUSB'
    advice=(f'{what} dla USB w backendzie @py. '
        'W programie wybierz VISA: systemowy NI / Keysight, jeśli masz zainstalowaną tę bibliotekę. ')
    if getattr(sys,'frozen',False):
        advice+='Dla @py użyj aktualnego NVLab.exe z dołączonym PyUSB i libusb. Instalacja pip nie zmienia istniejącego EXE. '
    else:
        advice+='Dla @py zainstaluj w interpreterze programu: python -m pip install pyusb libusb-package; potem uruchom program ponownie. '
    return advice+'Biblioteka libusb nie zastępuje zgodnego sterownika urządzenia w Windows. Szczegóły: '+detail
