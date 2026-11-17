param(
    [switch]$Install,
    [switch]$Demo
)

$ErrorActionPreference = 'Stop'
$projectDirectory = Split-Path -Parent $PSScriptRoot
Push-Location -LiteralPath $projectDirectory
try {
    $interpreterPath = Join-Path $projectDirectory '.venv312\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $interpreterPath)) {
        if (-not $Install) {
            throw 'Brak .venv312. Uruchom ponownie z -Install (wymagany Python 3.12: py -3.12).'
        }
        & py -3.12 -m venv .venv312
        if ($LASTEXITCODE -ne 0) { throw 'Nie utworzono srodowiska Python 3.12.' }
    }
    & $interpreterPath -c 'import sys; print(sys.version); raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'
    if ($LASTEXITCODE -ne 0) { throw 'Niepoprawna wersja Pythona w .venv312.' }
    if ($Install) {
        & $interpreterPath -m pip install --upgrade pip
        if ($LASTEXITCODE -ne 0) { throw 'Aktualizacja pip nie powiodla sie.' }
        # h5py wheels include HDF5; a source build requires a separate HDF5 SDK.
        & $interpreterPath -m pip install --only-binary=h5py -e '.[gui,hardware]'
        if ($LASTEXITCODE -ne 0) { throw 'Instalacja zaleznosci nie powiodla sie.' }
    }
    if ($Demo) {
        & $interpreterPath -m nv_lab.ui --demo
    } else {
        & $interpreterPath -m nv_lab.ui
    }
    if ($LASTEXITCODE -ne 0) { throw 'Program zakonczyl sie bledem.' }
} finally {
    Pop-Location
}
