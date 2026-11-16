# Build on Windows with .venv312\Scripts\python.exe -m PyInstaller NVLab.spec
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, copy_metadata

hidden = collect_submodules('nv_lab') + collect_submodules('pyvisa_py') + collect_submodules('pyvisa')
data = collect_data_files('qcodes') + copy_metadata('qcodes')
for distribution in ('PyVISA','PyVISA-py','pulsestreamer','pyqtgraph'):
    data += copy_metadata(distribution)
a = Analysis(['scripts/frozen_entry.py'], pathex=['src'],
    binaries=[], datas=data, hiddenimports=hidden,
    hookspath=[], hooksconfig={}, runtime_hooks=[],
    excludes=['PyQt5','PyQt6','PySide2','IPython','jupyter','notebook'], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz,a.scripts,a.binaries,a.datas,[],name='NVLab',
    debug=False,bootloader_ignore_signals=False,strip=False,upx=False,
    console=False,disable_windowed_traceback=False)
