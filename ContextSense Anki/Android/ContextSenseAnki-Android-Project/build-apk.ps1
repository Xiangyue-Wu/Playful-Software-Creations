param(
    [ValidateSet(10, 11)]
    [int]$AndroidVersion = 10
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$assetsRoot = Join-Path $projectRoot "assets"
$sdkRoot = Join-Path $projectRoot "android-sdk"
$workRoot = Join-Path $projectRoot "build"
$downloadRoot = Join-Path $projectRoot "downloads"
$toolsZip = Join-Path $downloadRoot "commandlinetools-win-15859902_latest.zip"
$toolsUrl = "https://dl.google.com/android/repository/commandlinetools-win-15859902_latest.zip"
$toolsSha256 = "90ae805d20434428bffcb699c290860f19bb5f66a67e6b330067e3de801fb04a"
$cmdlineRoot = Join-Path $sdkRoot "cmdline-tools\latest"
$sdkManager = Join-Path $cmdlineRoot "bin\sdkmanager.bat"
$buildTools = Join-Path $sdkRoot "build-tools\35.0.0"
$androidJar = Join-Path $sdkRoot "platforms\android-35\android.jar"
$minSdkVersion = if ($AndroidVersion -eq 10) { 29 } else { 30 }
$outputApk = Join-Path $projectRoot "ContextSenseAnki-Android$AndroidVersion.apk"

foreach ($requiredFile in @(
    (Join-Path $assetsRoot "index.html"),
    (Join-Path $assetsRoot "styles.css"),
    (Join-Path $assetsRoot "app.js"),
    (Join-Path $assetsRoot "bundled-backup.js")
)) {
    if (-not (Test-Path -LiteralPath $requiredFile)) {
        throw "Missing required source file: $requiredFile"
    }
}

$obsoleteAssets = @("bundled-data.js") + (1..10 | ForEach-Object { "deck{0:D2}.txt" -f $_ })
foreach ($obsoleteAsset in $obsoleteAssets) {
    $obsoletePath = Join-Path $assetsRoot $obsoleteAsset
    if (Test-Path -LiteralPath $obsoletePath) {
        Remove-Item -LiteralPath $obsoletePath -Force
    }
}

New-Item -ItemType Directory -Force -Path $downloadRoot, $sdkRoot | Out-Null

if (-not (Test-Path -LiteralPath $sdkManager)) {
    if (-not (Test-Path -LiteralPath $toolsZip)) {
        Invoke-WebRequest -Uri $toolsUrl -OutFile $toolsZip
    }
    $actualHash = (Get-FileHash -LiteralPath $toolsZip -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualHash -ne $toolsSha256) {
        throw "Android command-line tools checksum mismatch."
    }
    $extractRoot = Join-Path $downloadRoot "cmdline-extracted"
    if (Test-Path -LiteralPath $extractRoot) { Remove-Item -LiteralPath $extractRoot -Recurse -Force }
    Expand-Archive -LiteralPath $toolsZip -DestinationPath $extractRoot -Force
    New-Item -ItemType Directory -Force -Path (Split-Path -Parent $cmdlineRoot) | Out-Null
    Move-Item -LiteralPath (Join-Path $extractRoot "cmdline-tools") -Destination $cmdlineRoot
}

$javaHome = $env:JAVA_HOME
if (-not $javaHome) {
    $javaCommand = Get-Command java.exe -ErrorAction SilentlyContinue
    if ($javaCommand) {
        $javaHome = Split-Path (Split-Path $javaCommand.Source -Parent) -Parent
    }
}
if (-not $javaHome -or -not (Test-Path -LiteralPath (Join-Path $javaHome "bin\javac.exe"))) {
    throw "JDK not found. Install a JDK and set JAVA_HOME before building."
}
$env:JAVA_HOME = $javaHome
$env:PATH = "$javaHome\bin;$env:PATH"
if (-not (Test-Path -LiteralPath $androidJar) -or -not (Test-Path -LiteralPath $buildTools)) {
    $yes = 1..30 | ForEach-Object { "y" }
    $yes | & $sdkManager --sdk_root=$sdkRoot --licenses | Out-Null
    & $sdkManager --sdk_root=$sdkRoot "platforms;android-35" "build-tools;35.0.0"
}
if (-not (Test-Path -LiteralPath $androidJar) -or -not (Test-Path -LiteralPath (Join-Path $buildTools "aapt2.exe"))) {
    throw "Required Android SDK platform or build tools are unavailable."
}

if (Test-Path -LiteralPath $workRoot) { Remove-Item -LiteralPath $workRoot -Recurse -Force }
$compiled = Join-Path $workRoot "compiled.zip"
$unsigned = Join-Path $workRoot "unsigned.apk"
$aligned = Join-Path $workRoot "aligned.apk"
$generated = Join-Path $workRoot "generated"
$classes = Join-Path $workRoot "classes"
$dex = Join-Path $workRoot "dex"
New-Item -ItemType Directory -Force -Path $workRoot, $generated, $classes, $dex | Out-Null

& (Join-Path $buildTools "aapt2.exe") compile --dir (Join-Path $projectRoot "res") -o $compiled
& (Join-Path $buildTools "aapt2.exe") link `
    -o $unsigned `
    -I $androidJar `
    --manifest (Join-Path $projectRoot "AndroidManifest.xml") `
    --min-sdk-version $minSdkVersion `
    --target-sdk-version 35 `
    --version-code 22 `
    --version-name "1.21" `
    -A $assetsRoot `
    $compiled `
    --java $generated `
    --auto-add-overlay

$javaSources = @(
    (Join-Path $projectRoot "src\com\memorize\anki\MainActivity.java"),
    (Join-Path $generated "com\memorize\anki\R.java")
)
& (Join-Path $javaHome "bin\javac.exe") -encoding UTF-8 -source 8 -target 8 -classpath $androidJar -d $classes $javaSources
$classesJar = Join-Path $workRoot "classes.jar"
Push-Location $classes
try { & (Join-Path $javaHome "bin\jar.exe") cf $classesJar . } finally { Pop-Location }
& (Join-Path $buildTools "d8.bat") --min-api $minSdkVersion --output $dex $classesJar
& (Join-Path $javaHome "bin\jar.exe") uf $unsigned -C $dex "classes.dex"
& (Join-Path $buildTools "zipalign.exe") -f 4 $unsigned $aligned

$signingRoot = Join-Path $projectRoot "signing"
$keystore = Join-Path $signingRoot "anki-release.jks"
$storePass = "MemorizeAnki2026!"
New-Item -ItemType Directory -Force -Path $signingRoot | Out-Null
if (-not (Test-Path -LiteralPath $keystore)) {
    & (Join-Path $javaHome "bin\keytool.exe") -genkeypair -v `
        -keystore $keystore -storepass $storePass -keypass $storePass `
        -alias anki -keyalg RSA -keysize 2048 -validity 10000 `
        -dname "CN=Memorize Anki, OU=Personal, O=Memorize, L=Shanghai, C=CN"
}

& (Join-Path $buildTools "apksigner.bat") sign `
    --ks $keystore --ks-key-alias anki `
    --ks-pass "pass:$storePass" --key-pass "pass:$storePass" `
    --out $outputApk $aligned
& (Join-Path $buildTools "apksigner.bat") verify --verbose --print-certs $outputApk
Write-Output "APK=$outputApk"
