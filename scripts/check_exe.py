"""Check the actual EXE against simulation and localhost SCPI, never lab hardware."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from datetime import datetime,timezone

root=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(root/'tests'))
from test_hardware_integration import scpi_station


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--exe',type=Path,default=root/'dist'/'NVLab.exe')
    parser.add_argument('--output',type=Path,default=None)
    args=parser.parse_args()
    executable=args.exe.resolve()
    if not executable.is_file():parser.error(f'EXE missing: {executable}')
    output=(args.output or root/'build'/('exe-check-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'))).resolve()
    output.mkdir(parents=True,exist_ok=False)
    env=os.environ.copy()
    for key in ('PYTHONPATH','PYTHONHOME','QT_PLUGIN_PATH'):env.pop(key,None)
    system_root=os.environ.get('SystemRoot',r'C:\Windows')
    env['PATH']=str(Path(system_root)/'System32')+';'+system_root
    env['QT_QPA_PLATFORM']='offscreen'
    with scpi_station() as (config,state,_):
        env['NV_LAB_SMOKE_SCOPE']=config.scope_address
        result=subprocess.run([str(executable),'--smoke-test',str(output/'gui')],env=env,timeout=120)
        report=json.loads((output/'gui'/'report.json').read_text(encoding='utf-8'))
        if result.returncode or not report.get('ok') or not report.get('gui_subprocess_diagnostic'):
            raise RuntimeError(json.dumps(report,ensure_ascii=False,indent=2))
        worker_report=output/'sg386.txt'
        result=subprocess.run([str(executable),'--diagnostic','sg386','--report',str(worker_report),
            config.sg_address,'--visalib','@py','--timeout','5'],env=env,timeout=60)
        text=worker_report.read_text(encoding='utf-8')
        if result.returncode or 'OK: SG386 communication verified' not in text:
            raise RuntimeError(text)
    report['sg386_worker']='OK: localhost server only'
    report['exe']=str(executable)
    report['size_bytes']=executable.stat().st_size
    report['sha256']=hashlib.sha256(executable.read_bytes()).hexdigest()
    report['python_removed_from_child_path']=True
    (output/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=True,indent=2))
    print(f'Report: {output}')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
