$ErrorActionPreference = 'Stop'
Set-Location (Split-Path -Parent $PSScriptRoot)
$python = Join-Path (Get-Location) '.venv-windows\Scripts\python.exe'
if (-not (Test-Path $python)) {
    py -3.12 -m venv .venv-windows
    if ($LASTEXITCODE -ne 0) { throw 'Python 3.12 environment creation failed.' }
}
& $python -m pip install -r packaging/requirements-windows.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
& $python -m PyInstaller --noconfirm --clean --onefile --windowed --name Malmoa --collect-all pykakasi --collect-all eng_to_ipa --collect-data pythainlp --collect-data laonlp --hidden-import pythainlp.tokenize.newmm --hidden-import pythainlp.transliterate.royin desktop.py
if ($LASTEXITCODE -ne 0) { throw 'Windows executable build failed.' }
$exe = Join-Path (Get-Location) 'dist\Malmoa.exe'
$report = Join-Path (Get-Location) 'dist\self-test.json'
if (Test-Path $report) { Remove-Item $report }
$process = Start-Process -FilePath $exe -ArgumentList @('--self-test', ('"' + $report + '"')) -Wait -PassThru
if ($process.ExitCode -ne 0) { throw 'Packaged application self-test failed.' }
if (-not (Test-Path $report)) { throw 'Self-test report was not produced.' }
$result = Get-Content -Raw -Encoding UTF8 $report | ConvertFrom-Json
if ($result.status -ne 'passed') { throw 'Packaged application self-test did not pass.' }
Get-FileHash $exe -Algorithm SHA256
Write-Host "Built: $exe"
