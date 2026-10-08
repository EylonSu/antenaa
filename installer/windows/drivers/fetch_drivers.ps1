# Downloads the official WCH CH341SER and FTDI CDM drivers into this folder.
param(
    [string]$Ch341Url = $(if ($env:CH341_URL) { $env:CH341_URL } else { "https://www.wch-ic.com/downloads/file/65.html" }),
    [string]$FtdiUrl  = $(if ($env:FTDI_URL)  { $env:FTDI_URL }  else { "https://ftdichip.com/wp-content/uploads/2023/09/CDM-v2.12.36.4-WHQL-Certified.zip" })
)
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
$here = $PSScriptRoot
$base = if ($env:RUNNER_TEMP) { $env:RUNNER_TEMP } else { [IO.Path]::GetTempPath() }
$tmp = Join-Path $base "antenna-drivers"
New-Item -ItemType Directory -Force -Path $tmp | Out-Null

function Get-Driver([string]$Url, [string]$Name) {
    $zip = Join-Path $tmp "$Name.zip"
    $raw = Join-Path $tmp $Name
    Write-Host "Downloading $Name from $Url"
    Invoke-WebRequest -Uri $Url -OutFile $zip -UserAgent "Mozilla/5.0"
    if (Test-Path $raw) { Remove-Item -Recurse -Force $raw }
    Expand-Archive -Path $zip -DestinationPath $raw -Force
    # Nested self-extracting exe (FTDI sometimes ships one): unpack with 7-Zip.
    Get-ChildItem $raw -Recurse -Filter *.exe | ForEach-Object { & 7z x $_.FullName "-o$raw\exe" -y | Out-Null }
    return $raw
}

function Copy-InfDir([string]$Raw, [string]$Pattern, [string]$Dest) {
    $inf = Get-ChildItem $Raw -Recurse -Filter $Pattern | Select-Object -First 1
    if (-not $inf) { throw "No $Pattern found under $Raw" }
    $target = Join-Path $here $Dest
    if (Test-Path $target) { Remove-Item -Recurse -Force $target }
    Copy-Item -Recurse $inf.Directory.FullName $target
    Write-Host "Placed $Dest from $($inf.Directory.FullName)"
}

# A failed vendor download must not break the build; setup.iss skips missing drivers.
foreach ($d in @(
    @{ Url = $Ch341Url; Name = "CH341SER"; Inf = "CH341SER.INF" },
    @{ Url = $FtdiUrl;  Name = "FTDI";     Inf = "ftdibus.inf" }
)) {
    try {
        Copy-InfDir (Get-Driver $d.Url $d.Name) $d.Inf $d.Name
    } catch {
        Write-Warning "Skipping $($d.Name) driver: $($_.Exception.Message)"
        if ($env:GITHUB_ACTIONS) { Write-Host "::warning::$($d.Name) driver not bundled: $($_.Exception.Message)" }
    }
}
