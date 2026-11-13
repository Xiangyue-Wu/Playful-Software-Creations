param(
    [string]$Version = '0.1.4',
    [string]$OutputDirectory = (Join-Path (Split-Path -Parent $PSScriptRoot) 'release-output')
)
$ErrorActionPreference = 'Stop'

if (-not [Environment]::Is64BitOperatingSystem) { throw 'Build the release on Windows x64.' }
$python = Get-Command python.exe -ErrorAction SilentlyContinue
if (-not $python) { throw 'Python is required only on the build computer.' }
$project = $PSScriptRoot
$buildVenv = Join-Path $project '.release-build-venv'
$buildPython = Join-Path $buildVenv 'Scripts\python.exe'
if (-not (Test-Path -LiteralPath $buildPython)) {
    & $python.Source -m venv $buildVenv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create the isolated build environment.' }
}
& $buildPython -m pip install --disable-pip-version-check --index-url 'https://pypi.org/simple' -r (Join-Path $project 'requirements-release-build.txt')
if ($LASTEXITCODE -ne 0) { throw 'Could not install the pinned release-build dependencies.' }

$output = [IO.Path]::GetFullPath($OutputDirectory)
$buildRoot = Join-Path $output "build-$Version"
$package = Join-Path $output "RMPP-ScreenBridge-v$Version"
$zip = Join-Path $output "RMPP-ScreenBridge-v$Version-win-x64.zip"
foreach ($path in @($buildRoot, $package, $zip)) {
    if (Test-Path -LiteralPath $path) { throw "Output already exists; choose a new version or output directory: $path" }
}
New-Item -ItemType Directory -Path $output -Force | Out-Null
New-Item -ItemType Directory -Path $buildRoot -Force | Out-Null

$qmd = Join-Path $project 'deploy\qmd-vnsee-layout\vnsee-asivery-clip-v7-landscape.qmd'
$entry = Join-Path $project 'apps\VNSee-Launcher\release_entry.py'
$launcherPath = Join-Path $project 'apps\VNSee-Launcher'
$dist = Join-Path $buildRoot 'dist'
$work = Join-Path $buildRoot 'work'
$spec = Join-Path $buildRoot 'spec'
$pyinstaller = Join-Path $buildVenv 'Scripts\pyinstaller.exe'
& $pyinstaller --noconfirm --clean --onefile --windowed --name 'RMPP-ScreenBridge' `
    --paths $launcherPath `
    --add-data "$qmd;deploy\qmd-vnsee-layout" `
    --collect-all paramiko --collect-all cryptography `
    --hidden-import win32api --hidden-import win32cred --hidden-import win32timezone `
    --distpath $dist --workpath $work --specpath $spec $entry
if ($LASTEXITCODE -ne 0) { throw 'PyInstaller build failed.' }

New-Item -ItemType Directory -Path $package -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $dist 'RMPP-ScreenBridge.exe') -Destination $package
Copy-Item -LiteralPath (Join-Path $project '启动安装器.cmd') -Destination $package
Copy-Item -LiteralPath (Join-Path $project '卸载RMPP-ScreenBridge.cmd') -Destination $package
Copy-Item -LiteralPath (Join-Path $project 'README.md') -Destination $package
Copy-Item -LiteralPath (Join-Path $project 'README.zh-CN.md') -Destination $package
Copy-Item -LiteralPath (Join-Path $project 'LICENSE') -Destination $package
Copy-Item -LiteralPath (Join-Path $project 'THIRD_PARTY.md') -Destination $package
$packageDocs = Join-Path $package 'docs'
New-Item -ItemType Directory -Path $packageDocs -Force | Out-Null
Copy-Item -LiteralPath (Join-Path $project 'docs\RECOVERY.md') -Destination $packageDocs
$packageQmd = Join-Path $package 'deploy\qmd-vnsee-layout'
New-Item -ItemType Directory -Path $packageQmd -Force | Out-Null
Copy-Item -LiteralPath $qmd -Destination $packageQmd

$commit = (& git -C $project rev-parse HEAD 2>$null).Trim()
$buildVersion = (& $buildPython -m PyInstaller --version).Trim()
$exeHash = (Get-FileHash -LiteralPath (Join-Path $package 'RMPP-ScreenBridge.exe') -Algorithm SHA256).Hash.ToLowerInvariant()
$pythonVersion = (& $buildPython --version).Trim()
$freeze = @(& $buildPython -m pip freeze)
$buildInfo = @("Version: $Version", "Source commit: $commit", "Build Python: $pythonVersion", "PyInstaller: $buildVersion", "Executable SHA256: $exeHash", 'Target: Windows x64', '', 'Build environment packages:', $freeze) -join "`r`n"
[IO.File]::WriteAllText((Join-Path $package 'BUILD-INFO.txt'), $buildInfo + "`r`n", [Text.UTF8Encoding]::new($false))

& (Join-Path $package 'RMPP-ScreenBridge.exe') --smoke-test
if ($LASTEXITCODE -ne 0) { throw 'Frozen executable smoke check failed.' }
Compress-Archive -Path (Join-Path $package '*') -DestinationPath $zip -CompressionLevel Optimal
Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive = [IO.Compression.ZipFile]::OpenRead($zip)
try {
    $expected = @('BUILD-INFO.txt','LICENSE','README.md','README.zh-CN.md','RMPP-ScreenBridge.exe',
        'THIRD_PARTY.md','启动安装器.cmd','卸载RMPP-ScreenBridge.cmd',
        'deploy/qmd-vnsee-layout/vnsee-asivery-clip-v7-landscape.qmd','docs/RECOVERY.md') | Sort-Object
    $actual = @($archive.Entries | ForEach-Object { $_.FullName.Replace('\','/') } | Where-Object { -not $_.EndsWith('/') } | Sort-Object)
    if (Compare-Object $expected $actual) { throw 'Release ZIP contents do not match the allowlist.' }
    if ($archive.Entries | Where-Object { $_.FullName -match '临时备份|\.venv|known_hosts|\.log$|install-receipt|\.pem$' }) { throw 'Release ZIP contains excluded local state.' }
} finally { $archive.Dispose() }

"ZIP: $zip"
"ZIP SHA256: $((Get-FileHash -LiteralPath $zip -Algorithm SHA256).Hash.ToLowerInvariant())"
"EXE SHA256: $exeHash"
"Source commit: $commit"
