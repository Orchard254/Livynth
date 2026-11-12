#Requires -Version 5.1
<#
Local Windows test narration using the built-in System.Speech voice.
No external AI providers, API keys, network calls or uploads.
#>
param(
    [Parameter(Mandatory=$true)][string]$VoiceText,
    [Parameter(Mandatory=$true)][string]$OutputWav,
    [ValidateRange(-10,10)][int]$Rate = -1
)
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech -ErrorAction Stop
$destination = [System.IO.Path]::GetFullPath($OutputWav)
New-Item -ItemType Directory -Force -Path ([System.IO.Path]::GetDirectoryName($destination)) | Out-Null
if ([string]::IsNullOrWhiteSpace($VoiceText)) { throw 'Cannot synthesize empty speech' }
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $synth.Rate = $Rate
    $synth.SetOutputToWaveFile($destination)
    $synth.Speak($VoiceText)
    $synth.SetOutputToNull()
} finally {
    $synth.Dispose()
}
if (-not (Test-Path -LiteralPath $destination)) { throw 'Speech WAV was not created' }
Write-Host "[LIVYNTH] Local narration saved: $destination"