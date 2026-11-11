"""Read-only PCM WAV preflight for LIVYNTH Studio narration.

Blocks absent, malformed, too-short and effectively silent audio before video
rendering. Signal presence is NOT speech intelligibility or lip-sync quality.
No third-party packages are required, including Python 3.13+ (no audioop).
"""
from __future__ import annotations

import math
from pathlib import Path
import wave


class InvalidNarration(ValueError):
    """The WAV cannot be used as an audible narration candidate."""


def inspect_narration_wav(path: Path, *, min_active_s: float = 0.12,
                          threshold_dbfs: float = -55.0) -> dict:
    """Stream 50-ms PCM blocks and measure DC-removed signal activity.

    The acceptance threshold is deliberately permissive; a successful result
    does not prove a recognizable voice or the presence of meaningful words.
    """
    path = Path(path)
    try:
        with wave.open(str(path), "rb") as wav:
            channels = wav.getnchannels()
            width = wav.getsampwidth()
            rate = wav.getframerate()
            frame_count = wav.getnframes()
            if wav.getcomptype() != "NONE" or width not in (1, 2, 3, 4):
                raise InvalidNarration("E_WAV_UNSUPPORTED_PCM")
            if not (1 <= channels <= 8 and 8000 <= rate <= 192000 and frame_count > 0):
                raise InvalidNarration("E_WAV_INVALID_FORMAT")
            duration = frame_count / rate
            if not 0.25 <= duration <= 120.0:
                raise InvalidNarration("E_WAV_DURATION_OUT_OF_RANGE")
            block_frames = max(1, round(rate * 0.05))
            threshold = 10.0 ** (threshold_dbfs / 20.0)
            active_s = 0.0
            max_block_rms = 0.0
            peak = 0.0
            scale = float(1 << (width * 8 - 1))
            for start in range(0, frame_count, block_frames):
                frames_to_read = min(block_frames, frame_count - start)
                data = wav.readframes(frames_to_read)
                if len(data) != frames_to_read * channels * width:
                    raise InvalidNarration("E_WAV_TRUNCATED_PCM")
                sums = [0.0] * channels
                squares = [0.0] * channels
                for i in range(frames_to_read):
                    base = i * channels * width
                    for channel in range(channels):
                        pos = base + channel * width
                        raw = data[pos:pos + width]
                        sample = ((raw[0] - 128) / 128.0 if width == 1 else
                                  int.from_bytes(raw, "little", signed=True) / scale)
                        sums[channel] += sample
                        squares[channel] += sample * sample
                        peak = max(peak, abs(sample))
                # Ignore pure DC offsets; compute per-channel variance before
                # aggregating to avoid cancellation in out-of-phase stereo.
                count = float(frames_to_read)
                variance = sum(max(0.0, squares[ch] / count -
                                   (sums[ch] / count) ** 2)
                               for ch in range(channels)) / channels
                rms = math.sqrt(variance)
                max_block_rms = max(max_block_rms, rms)
                if rms >= threshold:
                    active_s += frames_to_read / rate
    except (wave.Error, EOFError, OSError) as exc:
        raise InvalidNarration("E_WAV_UNREADABLE") from exc

    if active_s + 1e-6 < min_active_s:
        raise InvalidNarration(
            f"E_WAV_NO_MEANINGFUL_SIGNAL: only {active_s:.3f}s above "
            f"{threshold_dbfs:g} dBFS (at least {min_active_s:g}s required)"
        )
    return {
        "status": "PASS_SIGNAL_NOT_SPEECH_QUALITY",
        "sample_rate_hz": rate,
        "channels": channels,
        "sample_width_bits": width * 8,
        "duration_s": round(duration, 4),
        "active_signal_s": round(active_s, 4),
        "loudest_block_dbfs": round(20 * math.log10(max(max_block_rms, 1e-12)), 2),
        "peak_normalized": round(peak, 5),
        "threshold_dbfs": threshold_dbfs,
    }
