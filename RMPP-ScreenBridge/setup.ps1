param([switch]$VerifyOnly, [switch]$Uninstall)
$ErrorActionPreference = 'Stop'
$project = Split-Path -Parent $MyInvocation.MyCommand.Path
$venv = Join-Path $project '.venv'
$python = Join-Path $venv 'Scripts\python.exe'
$pythonw = Join-Path $venv 'Scripts\pythonw.exe'

if (-not (Test-Path -LiteralPath $python)) {
    $systemPython = Get-Command py.exe -ErrorAction SilentlyContinue
    $pyUsable = $false
    if ($systemPython) {
        try {
            & $systemPython.Source -3 -c 'import sys; print(sys.version_info[:2])' 2>$null
            $pyUsable = ($LASTEXITCODE -eq 0)
        } catch { $pyUsable = $false }
    }
    if ($pyUsable) {
        & $systemPython.Source -3 -m venv $venv
    } else {
        $systemPython = Get-Command python.exe -ErrorAction SilentlyContinue
        if (-not $systemPython) { throw 'Python 3.10+ is required. No system Python will be installed.' }
        & $systemPython.Source -m venv $venv
    }
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path -LiteralPath $python)) { throw 'Could not create the project virtual environment.' }
}

& $python -c 'import sys; assert sys.version_info >= (3, 10), "Python 3.10+ required"'
if ($LASTEXITCODE -ne 0) { throw 'Python 3.10+ is required.' }
& $python -c 'import paramiko, win32cred, cryptography'
if ($LASTEXITCODE -ne 0) {
    & $python -m pip install --disable-pip-version-check --index-url 'https://pypi.org/simple' -r (Join-Path $project 'requirements.txt')
    if ($LASTEXITCODE -ne 0) { throw 'Could not install the project Python dependencies.' }
}
$guiName = if ($Uninstall) { 'uninstaller_gui.py' } else { 'portable_gui.py' }
$gui = Join-Path $project (Join-Path 'apps\VNSee-Launcher' $guiName)
if (-not (Test-Path -LiteralPath $gui)) { throw "GUI source file is missing: $guiName" }
if ($VerifyOnly) { Write-Output 'Project Python environment is ready.'; exit 0 }
Start-Process -FilePath $pythonw -ArgumentList ('"{0}"' -f $gui) -WorkingDirectory $project -WindowStyle Normal
