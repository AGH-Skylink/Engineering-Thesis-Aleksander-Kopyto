param([switch]$Install)
$ErrorActionPreference='Stop'
$projectDirectory=Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectDirectory
try {
    $interpreterPath=Join-Path $projectDirectory '.venv312\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $interpreterPath)) {
        throw 'Najpierw uruchom scripts\Start-NVLab.ps1 -Install (Python 3.12).'
    }
    if ($Install) {
        & $interpreterPath -m pip install --only-binary=h5py -e '.[gui,hardware]' 'pyinstaller>=6,<7'
        if ($LASTEXITCODE -ne 0) { throw 'Instalacja zaleznosci nie powiodla sie.' }
    }
    & $interpreterPath -m PyInstaller --noconfirm NVLab.spec
    if ($LASTEXITCODE -ne 0) { throw 'Budowanie EXE nie powiodlo sie.' }
    Write-Host "Gotowe: $projectDirectory\dist\NVLab.exe"
} finally { Pop-Location }
