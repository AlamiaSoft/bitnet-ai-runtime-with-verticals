<#
.SYNOPSIS
Portable BitNet Server Launcher for Windows (Zero Docker Required).
Selects the best native binary tier for this CPU automatically.

Binary tiers (highest to lowest performance):
  AVX-512  -> llama-server-avx512.exe  (modern Intel/AMD)
  AVX2     -> llama-server-avx2.exe    (CPUs from 2013+)
  Generic  -> llama-server.exe         (any x64, slow - no SIMD)

If no compatible binary is found, the script exits cleanly so Alamia
can fallback to Docker or remote inference automatically.
#>
$ErrorActionPreference = "Stop"

Write-Host "============================================================"
Write-Host " Alamia BitNet Runtime  -  Windows Native (Zero Docker)"
Write-Host "============================================================"

# Thread calculation (low-end friendly)
$port = 8080
$cores = [Environment]::ProcessorCount
if ($cores -le 4) { $threads = $cores } else { $threads = $cores - 2 }
if ($threads -gt 8) { $threads = 8 }
Write-Host "[Hardware] CPU cores: $cores  ->  Inference threads: $threads"

# Architecture-aware binary tier selection
$binDir = Join-Path $PSScriptRoot "bin"
$tiers = @(
    @{ Name = "AVX-512"; File = "llama-server-avx512.exe"; FeatureId = 41; Suitability = "excellent" },
    @{ Name = "AVX2";    File = "llama-server-avx2.exe";   FeatureId = 40; Suitability = "excellent" },
    @{ Name = "Generic"; File = "llama-server.exe";         FeatureId = -1; Suitability = "poor" }
)

$selectedTier = $null
$selectedExe  = $null

# Load WinAPI for instruction-set detection
Add-Type -TypeDefinition @"
using System;
using System.Runtime.InteropServices;
public class WinApi {
    [DllImport("kernel32.dll")] public static extern bool IsProcessorFeaturePresent(int ProcessorFeature);
}
"@

foreach ($tier in $tiers) {
    $exePath = Join-Path $binDir $tier.File
    if (-not (Test-Path $exePath)) {
        Write-Host "[Binary] $($tier.Name): binary not found, skipping."
        continue
    }
    # FeatureId -1 = no requirement (generic, runs on any x64)
    $featureOk = ($tier.FeatureId -eq -1) -or ([WinApi]::IsProcessorFeaturePresent($tier.FeatureId))
    if (-not $featureOk) {
        Write-Host "[Binary] $($tier.Name): CPU does not support required instruction set, skipping."
        continue
    }
    $selectedTier = $tier
    $selectedExe  = $exePath
    break
}

if ($null -eq $selectedTier) {
    Write-Host ""
    Write-Host "[ERROR] No compatible native binary found in: $binDir"
    Write-Host "        Alamia will fallback to Docker or remote inference."
    exit 1
}

Write-Host "[Binary] Selected: $($selectedTier.Name)  Suitability: $($selectedTier.Suitability)"

# Performance warning for generic build
if ($selectedTier.Name -eq "Generic") {
    Write-Host ""
    Write-Host "[WARNING] Generic x64 binary selected. No SIMD acceleration available."
    Write-Host "          Performance will be significantly degraded on this hardware."
    Write-Host "          Consider using Docker or the Alamia remote inference fallback."
    Write-Host ""
}

# Dry-run: detect illegal instruction crash before model load
try {
    $testProc = Start-Process -FilePath $selectedExe -ArgumentList "--help" -NoNewWindow -PassThru -Wait
    # STATUS_ILLEGAL_INSTRUCTION = 0xC000001D = -1073741795 (signed) = 3221225501 (unsigned)
    if ($testProc.ExitCode -eq -1073741795 -or $testProc.ExitCode -eq 3221225501) {
        Write-Host "[ERROR] Binary crashed with illegal instruction on this CPU."
        Write-Host "        Alamia will fallback to Docker or remote inference."
        exit 1
    }
} catch {
    Write-Host "[WARNING] CPU instruction verification could not complete: $_"
}

# Model discovery (after binary check to avoid unnecessary downloads)
$modelCandidates = @(
    (Join-Path $PSScriptRoot "..\..\models\BitNet-b1.58-2B-4T\ggml-model-i2_s.gguf"),
    (Join-Path $PSScriptRoot "..\..\models\ggml-model-i2_s.gguf"),
    (Join-Path $PSScriptRoot "models\ggml-model-i2_s.gguf")
)

$modelPath = $null
foreach ($cand in $modelCandidates) {
    if (Test-Path $cand) {
        $modelPath = (Resolve-Path $cand).Path
        break
    }
}

if (-not $modelPath) {
    $targetDir = Join-Path $PSScriptRoot "..\..\models\BitNet-b1.58-2B-4T"
    if (-not (Test-Path $targetDir)) { New-Item -ItemType Directory -Path $targetDir -Force | Out-Null }
    $modelPath = Join-Path $targetDir "ggml-model-i2_s.gguf"
    $url = "https://huggingface.co/microsoft/BitNet-b1.58-2B-4T-gguf/resolve/main/ggml-model-i2_s.gguf"
    Write-Host "[INFO] Downloading BitNet weights (~1.2 GB)..."
    Write-Host "       Destination: $modelPath"
    Start-BitsTransfer -Source $url -Destination $modelPath -DisplayName "BitNet Model Download"
    Write-Host "[OK] Download completed."
}

# Launch
Write-Host ""
Write-Host "[Start] http://127.0.0.1:$port/v1   (Threads: $threads)"
Write-Host "[Model] $modelPath"
Write-Host "        Press Ctrl+C to stop."
Write-Host "============================================================"

& $selectedExe `
    -m $modelPath `
    --host 127.0.0.1 `
    --port $port `
    -t $threads `
    --repeat-penalty 1.15 `
    --repeat-last-n 64 `
    --top-p 0.9 `
    --min-p 0.05 `
    --temp 0.7 `
    -c 4096
