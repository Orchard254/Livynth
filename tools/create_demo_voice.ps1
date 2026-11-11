#Requires -Version 5.1
<#
Generate a spoken PCM WAV and matching transcript using Windows' built-in
System.Speech engine. No web service or GitHub Actions credit required.

Run from the Livynth repository:
  powershell -ExecutionPolicy Bypass -File .\tools\create_demo_voice.ps1
#>
param(
    [string]$VoiceText = 'Welcome to Livynth. We are creating digital humans that can speak, move, and bring stories to life. Today, we take our first step toward an intelligent video creation studio.',
    [ValidateRange(-10, 10)][int]$Rate = -1
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$assets = Join-Path $repo 'assets'
New-Item -ItemType Directory -Path $assets -Force | Out-Null
$wavPath = Join-Path $assets 'voice.wav'
$transcriptPath = Join-Path $assets 'voice_transcript.txt'

try {
    Add-Type -AssemblyName System.Speech -ErrorAction Stop
} catch {
    throw 'Windows System.Speech is unavailable. Use Windows PowerShell 5.1, or copy livynth_demo_voice.wav from the first smoke kit to assets/voice.wav.'
}

$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
try {
    $synth.Rate = $Rate
    $synth.SetOutputToWaveFile($wavPath)
    $synth.Speak($VoiceText)
    $synth.SetOutputToNull()
} finally {
    $synth.Dispose()
}
Set-Content -LiteralPath $transcriptPath -Value $VoiceText -NoNewline -Encoding UTF8
Write-Host "Created audio: $wavPath"
Write-Host "Created transcript: $transcriptPath"
& python -c 'import wave,sys; w=wave.open(sys.argv[1], "rb"); print("WAV duration: %.2f seconds; %d channels; %d Hz" % (w.getnframes()/w.getframerate(),w.getnchannels(),w.getframerate())); w.close()' $wavPath
if ($LASTEXITCODE -ne 0) { throw 'WAV validation failed. Check your Python installation.' }
